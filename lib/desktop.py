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
SEARCH = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Search"
STUCK = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\StuckRects3"

# valor → (clave, nombre, tipo, dato, explicación)
TASKBAR = [
    (ADVANCED, "TaskbarAl",            "REG_DWORD", "1", "iconos centrados"),
    (ADVANCED, "ShowTaskViewButton",   "REG_DWORD", "0", "sin vista de tareas"),
    (ADVANCED, "TaskbarDa",            "REG_DWORD", "0", "sin widgets"),
    (ADVANCED, "TaskbarMn",            "REG_DWORD", "0", "sin chat"),
    (ADVANCED, "TaskbarGlomLevel",     "REG_DWORD", "2", "nunca combinar botones"),
    (ADVANCED, "MMTaskbarGlomLevel",   "REG_DWORD", "2", "ídem en pantallas secundarias"),
    (SEARCH,   "SearchboxTaskbarMode", "REG_DWORD", "1", "búsqueda reducida a icono"),
]

# El Explorador: lo que el propio diseño reconoce como alcanzable de forma
# nativa — compacto, extensiones a la vista, ocultos visibles pero apagados.
EXPLORER = [
    (ADVANCED, "UseCompactMode", "REG_DWORD", "1", "espaciado compacto"),
    (ADVANCED, "HideFileExt",    "REG_DWORD", "0", "extensiones siempre a la vista"),
    (ADVANCED, "Hidden",         "REG_DWORD", "1", "mostrar ficheros ocultos"),
    (ADVANCED, "ShowSuperHidden","REG_DWORD", "0", "pero no los del sistema"),
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


def apply_taskbar(snap: state.Snapshot, ctx, remove: bool = False) -> bool:
    """Devuelve True si algo cambió (y por tanto hay que reiniciar explorer)."""
    if remove:
        return False
    print("· barra de tareas y Explorador (HKCU)")
    touched = False
    for key, name, typ, data, why in TASKBAR + EXPLORER:
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


def apply_windhawk(pal: dict, snap: state.Snapshot, ctx, win_home, remove: bool = False) -> bool:
    print("· Windhawk (barra, menú Inicio y reloj)")
    if not pathlib.Path("/mnt/c/Program Files/Windhawk").is_dir():
        ctx.say("Windhawk no está instalado, salto")
        return False

    wanted = (windhawk.TASKBAR_MOD, windhawk.START_MOD, windhawk.CLOCK_MOD)
    missing = [m for m in wanted if not windhawk.installed(m)]
    if missing:
        ctx.say("faltan mods, instálalos desde la interfaz de Windhawk: " + ", ".join(missing))
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

    blocks = {
        windhawk.TASKBAR_MOD: windhawk.taskbar_settings(pal),
        windhawk.START_MOD: windhawk.start_settings(pal),
        windhawk.CLOCK_MOD: windhawk.clock_settings(pal),
    }
    # el del reloj venía apagado; sin esto no se carga
    mod_values = {m: {"Disabled": 0} for m in wanted}
    content = windhawk.reg_file(blocks, mod_values)
    n = sum(len(v) for v in blocks.values())
    ctx.say(f"{n} ajustes: barra sin tema base + TranslucentStartMenu + reloj de dos líneas")

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
