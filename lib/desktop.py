#!/usr/bin/env python3
"""El escritorio: barra de tareas y Explorador por registro (HKCU), y los mods
de Windhawk.

Sigue el diseño «Tema Windows Claude CLI»: barra de ancho completo, centrada,
SIEMPRE VISIBLE (nada de autohide), búsqueda reducida a icono, sin widgets ni
vista de tareas, y nunca combinar botones. La forma — esquinas redondeadas
arriba y los colores — la pone Windhawk, porque eso Windows no lo expone.
"""
from __future__ import annotations
import pathlib, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import state, windhawk  # noqa: E402

ADVANCED = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
DESKTOP_ICONS = (r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer"
                 r"\HideDesktopIcons\NewStartPanel")
BAGS = r"HKCU\Software\Microsoft\Windows\Shell\Bags\AllFolders\Shell"
CLASSES = r"HKCU\Software\Classes"
GUID_THIS_PC = "{20D04FE0-3AEA-1069-A2D8-08002B30309D}"
SEARCH = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Search"
PERSONALIZE = (r"HKCU\Software\Microsoft\Windows\CurrentVersion\Themes"
               r"\Personalize")
POL_EXPLORER = r"HKCU\Software\Policies\Microsoft\Windows\Explorer"
STUCK = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\StuckRects3"

# valor → (clave, nombre, tipo, dato, explicación)
TASKBAR = [
    (ADVANCED, "TaskbarAl",            "REG_DWORD", "1", "iconos centrados"),
    (ADVANCED, "ShowTaskViewButton",   "REG_DWORD", "0", "sin vista de tareas"),
    (ADVANCED, "TaskbarDa",            "REG_DWORD", "0", "sin widgets"),
    (ADVANCED, "TaskbarMn",            "REG_DWORD", "0", "sin chat"),
    (SEARCH,   "SearchboxTaskbarMode", "REG_DWORD", "1", "búsqueda reducida a icono"),
    # v2, sección 11: «sin transparencia». Con cristal, el #0A0D0F de la barra
    # se mezcla con lo que haya debajo y deja de ser el color del tema.
    (PERSONALIZE, "EnableTransparency", "REG_DWORD", "0", "sin transparencia"),
    # v2, sección 04: el contenido web de Bing fuera de Win+S. Es directiva, pero
    # la de HKCU basta y no pide elevación.
    (POL_EXPLORER, "DisableSearchBoxSuggestions", "REG_DWORD", "1",
     "búsqueda sin resultados web"),
]

# Combinar botones. El diseño pide «nunca combinar», que en Windows implica
# etiqueta al lado de cada icono — y con diez ventanas abiertas eso son diez
# títulos truncados ocupando la barra entera. `always` deja solo el icono.
GLOM = {
    "always":   ("0", "un icono por app, sin etiqueta"),
    "whenFull": ("1", "combina solo cuando la barra se llena"),
    "never":    ("2", "nunca combinar: cada ventana con su etiqueta"),
}

# El Explorador: lo que el propio diseño reconoce como alcanzable de forma
# nativa — compacto, extensiones a la vista, ocultos visibles pero apagados.
EXPLORER = [
    (ADVANCED, "UseCompactMode", "REG_DWORD", "1", "espaciado compacto"),
    # Dos superficies menos que pintan un gris propio y no se pueden recolorear:
    # la barra de estado (#1C1C1C) y el panel de detalles (#141618). v2 tambien
    # pide quitar el panel en su seccion 06.
    (ADVANCED, "ShowStatusBar", "REG_DWORD", "0", "sin barra de estado"),
    (ADVANCED, "HideFileExt",    "REG_DWORD", "0", "extensiones siempre a la vista"),
    (ADVANCED, "Hidden",         "REG_DWORD", "1", "mostrar ficheros ocultos"),
    (ADVANCED, "ShowSuperHidden","REG_DWORD", "0", "pero no los del sistema"),
    # El diseño enseña «Este equipo» en el escritorio; 0 = visible.
    (DESKTOP_ICONS, GUID_THIS_PC, "REG_DWORD", "0", "«Este equipo» en el escritorio"),
    # Vista Detalles por defecto, que es lo que dibuja el diseño en el Explorador.
    (BAGS, "FolderType", "REG_SZ", "NotSpecified", "vista Detalles por defecto"),
]

# El menú Inicio del diseño tiene sección RECIENTES con ficheros y apps.
START = [
    (ADVANCED, "Start_TrackDocs",  "REG_DWORD", "1", "recientes: ficheros"),
    (ADVANCED, "Start_TrackProgs", "REG_DWORD", "1", "recientes: aplicaciones"),
    (ADVANCED, "Start_Layout",     "REG_DWORD", "1", "rejilla con más anclados"),
]


def _same(typ: str, a: str, b: str) -> bool:
    """reg.exe devuelve los DWORD en hex (0x1) y nosotros los pasamos en decimal."""
    if typ == "REG_DWORD":
        try:
            return int(a, 0) == int(b, 0)
        except ValueError:
            return False
    return a.strip().lower() == b.strip().lower()


def _autohide_blob(cur: str, on: bool) -> str:
    """StuckRects3\\Settings es binario; el bit 0 del byte 8 es el autohide."""
    b = bytearray.fromhex(cur)
    if len(b) < 9:
        raise ValueError("StuckRects3 con longitud inesperada")
    b[8] = (b[8] | 0x01) if on else (b[8] & ~0x01)
    return b.hex().upper()


def apply_taskbar(snap: state.Snapshot, ctx, pal: dict,
                  remove: bool = False) -> bool:
    """Devuelve True si algo cambió (y por tanto hay que reiniciar explorer)."""
    if remove:
        return False
    print("· barra de tareas y Explorador (HKCU)")
    mode = pal["windowsDesktop"]["taskbar"].get("combineButtons", "always")
    if mode not in GLOM:
        raise SystemExit(f"combineButtons: «{mode}» no vale; usa {sorted(GLOM)}")
    glom, glom_why = GLOM[mode]
    values = TASKBAR + [
        (ADVANCED, "TaskbarGlomLevel",   "REG_DWORD", glom, glom_why),
        (ADVANCED, "MMTaskbarGlomLevel", "REG_DWORD", glom, "ídem en pantallas secundarias"),
    ] + EXPLORER + START
    touched = False
    for key, name, typ, data, why in values:
        cur = state.read_reg(key, name)
        snap.capture_reg(key, name)
        if cur and _same(typ, cur[1], data):
            ctx.say(f"{name} ya está en {data} — {why}")
            continue
        ctx.say(f"{name} = {data} — {why}")
        touched = True
        if not ctx.dry:
            subprocess.run(["reg.exe", "add", key, "/v", name, "/t", typ,
                            "/d", data, "/f"], capture_output=True, cwd="/mnt/c")

    # El diseño pide la barra SIEMPRE VISIBLE, así que el autohide se apaga.
    cur = state.read_reg(STUCK, "Settings")
    if cur:
        snap.capture_reg(STUCK, "Settings")
        new = _autohide_blob(cur[1], on=False)
        if new == cur[1].upper():
            ctx.say("autohide ya estaba apagado")
        else:
            ctx.say("autohide apagado — barra siempre visible")
            touched = True
            if not ctx.dry:
                subprocess.run(["reg.exe", "add", STUCK, "/v", "Settings",
                                "/t", "REG_BINARY", "/d", new, "/f"],
                               capture_output=True, cwd="/mnt/c")
    return touched


def _vscode_exe() -> str | None:
    """Ruta de Code.exe en formato Windows, o None. Se busca en vez de cablearse
    para que esto funcione en cualquier máquina."""
    import glob
    cands = glob.glob("/mnt/c/Users/*/AppData/Local/Programs/Microsoft VS Code/Code.exe")
    cands += glob.glob("/mnt/c/Program Files/Microsoft VS Code/Code.exe")
    if not cands:
        return None
    return subprocess.run(["wslpath", "-w", cands[0]],
                          capture_output=True, text=True).stdout.strip()


def apply_context_menu(snap: state.Snapshot, ctx, remove: bool = False) -> bool:
    r"""«Abrir con Code» en carpetas y en el fondo de carpeta.

    Va a HKCU\Software\Classes, no a HKCR, para no necesitar elevación.
    «Abrir en Terminal» ya lo pone Windows 11 por su cuenta, así que no se toca.
    """
    if remove:
        return False
    print("· menú contextual")
    exe = _vscode_exe()
    if not exe:
        ctx.say("VS Code no está instalado, salto el verbo «Abrir con Code»")
        return False

    entries = [
        (rf"{CLASSES}\Directory\shell\VSCode", "%V", "sobre una carpeta"),
        (rf"{CLASSES}\Directory\Background\shell\VSCode", "%V", "en el fondo de carpeta"),
    ]
    for key, arg, where in entries:
        snap.capture_reg(key, "")
        snap.capture_reg(key, "Icon")
        snap.capture_reg(key + r"\command", "")
        ctx.say(f"«Abrir con Code» {where}")
        if ctx.dry:
            continue
        for k, name, val in ((key, None, "Abrir con Code"),
                             (key, "Icon", f"{exe},0"),
                             (key + r"\command", None, f'"{exe}" "{arg}"')):
            cmd = ["reg.exe", "add", k]
            cmd += ["/ve"] if name is None else ["/v", name]
            cmd += ["/t", "REG_SZ", "/d", val, "/f"]
            subprocess.run(cmd, capture_output=True, cwd="/mnt/c")
    return True


PINNED = ("Microsoft/Internet Explorer/Quick Launch/User Pinned/TaskBar")


def apply_pinned_icons(pal: dict, snap: state.Snapshot, ctx, win_home, remove: bool = False) -> bool:
    """Reviste los accesos directos anclados con los glifos de la paleta.

    Solo llega hasta aquí: el icono de un acceso directo es nuestro, pero el de
    una app en ejecución que no esté anclada lo pone la propia app y no hay por
    dónde cogerlo. El diseño dibuja cinco glifos; se aplican a los que estén
    anclados de verdad.
    """
    if remove or not win_home:
        return False
    print("· iconos de los anclados")
    try:
        import PIL  # noqa: F401
    except ImportError:
        ctx.say("falta python3-pil, no puedo generar los iconos")
        return False

    import icons
    pinned_dir = win_home / "AppData/Roaming" / PINNED
    if not pinned_dir.is_dir():
        ctx.say("no encuentro la carpeta de anclados")
        return False

    icon_dir = win_home / "AppData/Local/claude-terminal-theme/icons"
    if not ctx.dry:
        icons.build_all(pal, icon_dir)

    changed = False
    for lnk in sorted(pinned_dir.glob("*.lnk")):
        name = lnk.stem
        entry = icons.APPS.get(name)
        if not entry:
            ctx.say(f"{name}: sin glifo asignado en icons.APPS, lo dejo")
            continue
        glyph, role = entry
        ico = icon_dir / f"{role}-{name.replace(' ', '-')}.ico"
        snap.capture_file(lnk)              # el .lnk entero, para poder devolverlo
        ctx.say(f"{name} → {glyph} {role}")
        changed = True
        if ctx.dry:
            continue
        win_ico = subprocess.run(["wslpath", "-w", str(ico)],
                                 capture_output=True, text=True).stdout.strip()
        win_lnk = subprocess.run(["wslpath", "-w", str(lnk)],
                                 capture_output=True, text=True).stdout.strip()
        ps = (f"$s=New-Object -ComObject WScript.Shell;"
              f"$l=$s.CreateShortcut('{win_lnk}');"
              f"$l.IconLocation='{win_ico},0';$l.Save()")
        r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps],
                           capture_output=True, cwd="/mnt/c")
        if r.returncode != 0:
            ctx.say("  ! " + r.stderr.decode("cp850", "replace").strip()[:120])

    if changed and not ctx.dry:
        # sin esto Windows sigue enseñando el icono viejo desde su caché
        subprocess.run(["ie4uinit.exe", "-show"], capture_output=True, cwd="/mnt/c")
    return changed


def broadcast_colorchange(ctx) -> None:
    """Avisar de que el acento cambió, para que se relea sin reiniciar sesión.

    Escribir `AccentColor` y `AccentColorInactive` en el registro no basta: quien
    los usa ya los tiene en memoria. `win11-accent-border` los recarga en
    WM_DWMCOLORIZATIONCOLORCHANGED (0x0320) y en nada más — ni WM_SETTINGCHANGE
    con «ImmersiveColorSet» ni UpdatePerUserSystemParameters lo despiertan,
    ambos probados. Sin este aviso, el borde se queda con el color anterior
    hasta el siguiente inicio de sesión.
    """
    if ctx.dry:
        ctx.say("difundiendo WM_DWMCOLORIZATIONCOLORCHANGED")
        return
    ps = (
        'Add-Type @"\n'
        'using System;using System.Runtime.InteropServices;\n'
        'public class B{[DllImport("user32.dll")] public static extern IntPtr '
        'SendMessageTimeout(IntPtr h,uint m,IntPtr w,IntPtr l,uint f,uint t,out IntPtr r);}\n'
        '"@\n'
        '$r=[IntPtr]::Zero\n'
        '[void][B]::SendMessageTimeout([IntPtr]0xffff,0x0320,[IntPtr]::Zero,'
        '[IntPtr]::Zero,2,4000,[ref]$r)\n'
    )
    r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps],
                       capture_output=True, cwd="/mnt/c")
    ctx.say("acento difundido" if r.returncode == 0 else
            "! no se pudo difundir el cambio de acento; se verá al reiniciar sesión")


def apply_windhawk(pal: dict, snap: state.Snapshot, ctx, win_home, remove: bool = False) -> bool:
    print("· Windhawk (barra, Inicio, reloj, Explorador y notificaciones)")
    if not pathlib.Path("/mnt/c/Program Files/Windhawk").is_dir():
        ctx.say("Windhawk no está instalado, salto")
        return False

    wanted = (windhawk.TASKBAR_MOD, windhawk.ICONSIZE_MOD, windhawk.START_MOD,
              windhawk.STARTPOS_MOD, windhawk.STARTICON_MOD, windhawk.BORDER_MOD,
              windhawk.CLOCK_MOD, windhawk.EXPLORER_MOD, windhawk.COLUMNS_MOD,
              windhawk.NOTIF_MOD)
    # El manifiesto y el código no pueden divergir en silencio: si añades un mod
    # aquí y olvidas su ficha, el que instale esto en otra máquina se queda sin
    # saber cómo se llama en el buscador.
    sin_ficha = [m for m in wanted if m not in windhawk.catalog()]
    if sin_ficha:
        raise SystemExit("sin ficha en windows/mods.json: " + ", ".join(sin_ficha))

    missing = [m for m in wanted if not windhawk.installed(m)]
    if missing:
        # No se puede instalar un mod desde fuera: Windhawk los compila en local
        # desde su interfaz y no expone CLI. Se configura lo que haya y se avisa
        # con el nombre buscable, que es lo único que sirve en la pestaña Explore.
        ctx.say(f"faltan {len(missing)} de {len(wanted)} mods; configuro el resto")
        for line in windhawk.missing_report(missing):
            print(line)
    wanted = tuple(m for m in wanted if windhawk.installed(m))

    if windhawk.STARTICON_MOD in wanted:
        import icons
        icon_dir = win_home / "AppData/Local/claude-terminal-theme/icons"
        if ctx.dry:
            ctx.say(f"asterisco de Inicio en {icon_dir}/start-claude.png")
        else:
            snap.capture_file(icon_dir / "start-claude.png")
            ctx.say(f"asterisco de Inicio → {icons.build_start(pal, icon_dir).name}")
    if not wanted:
        return False
    off = [m for m in wanted if windhawk.enabled(m) is False]
    if off:
        ctx.say("desactivados ahora mismo, los activo: " + ", ".join(off))

    if remove:
        ctx.say("la config de Windhawk se revierte con --uninstall desde el snapshot")
        return False

    # el estado original de cada mod, para poder devolverlo tal cual
    for mod in wanted:
        snap.capture_regkey(f"{windhawk.MODS_KEY}\\{mod}\\Settings")
        snap.capture_reg(f"{windhawk.MODS_KEY}\\{mod}", "SettingsChangeTime")
        snap.capture_reg(f"{windhawk.MODS_KEY}\\{mod}", "Disabled")

    builders = {
        windhawk.TASKBAR_MOD:  windhawk.taskbar_settings,
        windhawk.ICONSIZE_MOD: windhawk.iconsize_settings,
        windhawk.START_MOD:    windhawk.start_settings,
        windhawk.STARTPOS_MOD: windhawk.startpos_settings,
        windhawk.STARTICON_MOD: windhawk.starticon_settings,
        windhawk.BORDER_MOD:    windhawk.border_settings,
        windhawk.CLOCK_MOD:    windhawk.clock_settings,
        windhawk.EXPLORER_MOD: windhawk.explorer_settings,
        windhawk.COLUMNS_MOD:  windhawk.columns_settings,
        windhawk.NOTIF_MOD:    windhawk.notification_settings,
    }
    blocks = {m: builders[m](pal) for m in wanted}
    # el del reloj venía apagado; sin esto no se carga
    mod_values = {m: {"Disabled": 0} for m in wanted}
    content = windhawk.reg_file(blocks, mod_values)
    n = sum(len(v) for v in blocks.values())
    ctx.say(f"{n} ajustes en {len(blocks)} mods: " + ", ".join(m.replace("windows-11-", "") for m in blocks))

    if ctx.dry:
        ctx.say("no se importa nada; el .reg se habría escrito y pedido UAC")
        return False

    out = (win_home or pathlib.Path("/mnt/c/Users/Public")) / "claude-theme-backup"
    reg_path = out / "windhawk-claude.reg"
    windhawk.write_reg(reg_path, content)
    win_path = subprocess.run(["wslpath", "-w", str(reg_path)],
                              capture_output=True, text=True).stdout.strip()
    ctx.say(f"importando con UAC: {win_path}")
    print("  → acepta el diálogo de Control de cuentas de usuario")
    ok, msg = windhawk.import_elevated(win_path)
    ctx.say(("ok, " if ok else "! ") + msg)
    return ok
