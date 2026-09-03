#!/usr/bin/env python3
"""Aplica la paleta al lado Windows desde WSL (o desde Linux con /mnt/c montado).

Todo es idempotente: relanzarlo deja el mismo resultado. Antes de tocar un
fichero que ya existía se guarda una copia en <fichero>.bak-claude-<timestamp>,
y las claves de registro se exportan a %USERPROFILE%\\claude-theme-backup.
"""
from __future__ import annotations
import argparse, collections, datetime, glob, json, os, pathlib, shutil, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import render, state, desktop, uninstall, flow, keys  # noqa: E402

STAMP = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
MARKER_KEYS_VSCODE = ("terminal.background", "terminal.ansiCyan", "panel.background")


class Ctx:
    def __init__(self, dry: bool):
        self.dry = dry
        self.changed: list[str] = []
        self.snap = state.Snapshot(dry)

    def say(self, what: str):
        print(("  [dry] " if self.dry else "  ") + what)

    def note(self, what: str):
        self.changed.append(what)


# ── localizar Windows ─────────────────────────────────────────────────
def win_userprofile() -> pathlib.Path | None:
    """Ruta WSL del %USERPROFILE% del usuario de Windows."""
    try:
        out = subprocess.run(["cmd.exe", "/c", "echo %USERPROFILE%"],
                             capture_output=True, text=True, timeout=20,
                             cwd="/mnt/c").stdout.strip()
    except Exception:
        return None
    if not out or "%" in out:
        return None
    try:
        p = subprocess.run(["wslpath", "-u", out], capture_output=True,
                           text=True, timeout=10).stdout.strip()
    except Exception:
        return None
    return pathlib.Path(p) if p and pathlib.Path(p).is_dir() else None


def find_wt_settings() -> pathlib.Path | None:
    pats = [
        "/mnt/c/Users/*/AppData/Local/Packages/Microsoft.WindowsTerminal_*/LocalState/settings.json",
        "/mnt/c/Users/*/AppData/Local/Packages/Microsoft.WindowsTerminalPreview_*/LocalState/settings.json",
        "/mnt/c/Users/*/AppData/Local/Microsoft/Windows Terminal/settings.json",
    ]
    hits = [pathlib.Path(h) for pat in pats for h in glob.glob(pat)]
    return hits[0] if hits else None


def find_vscode_settings(home: pathlib.Path | None) -> pathlib.Path | None:
    if not home:
        return None
    for flavour in ("Code", "Code - Insiders", "VSCodium"):
        p = home / "AppData/Roaming" / flavour / "User/settings.json"
        if p.exists():
            return p
    return None


def find_ps_profile(home: pathlib.Path | None) -> pathlib.Path | None:
    if not home:
        return None
    for docs in ("Documents", "OneDrive/Documentos", "OneDrive/Documents", "Documentos"):
        d = home / docs / "WindowsPowerShell"
        if (home / docs).is_dir():
            return d / "Microsoft.PowerShell_profile.ps1"
    return None


# ── utilidades ────────────────────────────────────────────────────────
def backup(path: pathlib.Path, ctx: Ctx):
    ctx.snap.capture_file(path)          # así --uninstall sabe devolverlo
    if path.exists():
        dst = path.with_name(path.name + f".bak-claude-{STAMP}")
        ctx.say(f"backup → {dst.name}")
        if not ctx.dry:
            shutil.copy2(path, dst)


def load_json(path: pathlib.Path) -> collections.OrderedDict:
    txt = path.read_text(encoding="utf-8-sig")
    return json.loads(txt, object_pairs_hook=collections.OrderedDict)


def dump_json(path: pathlib.Path, data, ctx: Ctx, indent=4, ascii_=False):
    if ctx.dry:
        return
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=indent, ensure_ascii=ascii_)
        fh.write("\n")


# ── Windows Terminal ──────────────────────────────────────────────────
def apply_wt(pal: dict, ctx: Ctx, remove: bool = False):
    path = find_wt_settings()
    if not path:
        print("  · Windows Terminal: no encontrado, salto")
        return
    print(f"· Windows Terminal → {path}")
    d = load_json(path)
    name = pal["name"]
    backup(path, ctx)

    if remove:
        d["schemes"] = [s for s in d.get("schemes", []) if s.get("name") != name]
        d["themes"] = [t for t in d.get("themes", []) if t.get("name") != name]
        if d.get("theme") == name:
            d.pop("theme", None)
        if d.get("profiles", {}).get("defaults", {}).get("colorScheme") == name:
            d["profiles"]["defaults"] = {}
        ctx.say("esquema, tema y defaults retirados")
    else:
        d.setdefault("schemes", [])
        d["schemes"] = [s for s in d["schemes"] if s.get("name") != name] + [render.wt_scheme(pal)]
        d["themes"] = [t for t in d.get("themes", []) if t.get("name") != name] + [render.wt_theme(pal)]
        d["theme"] = name
        d.setdefault("profiles", {})["defaults"] = render.wt_defaults(pal)
        # lo que se hereda de defaults no debe repetirse por perfil
        for prof in d["profiles"].get("list", []):
            for k in ("colorScheme", "font", "cursorShape", "opacity", "useAcrylic",
                      "experimental.retroTerminalEffect"):
                prof.pop(k, None)
        d["useAcrylicInTabRow"] = False
        ctx.say(f"esquema «{name}», tema de ventana y profiles.defaults aplicados")
    dump_json(path, d, ctx, indent=4, ascii_=True)
    ctx.note("Windows Terminal")


# ── VS Code ───────────────────────────────────────────────────────────
def apply_vscode(pal: dict, home, ctx: Ctx, remove: bool = False):
    path = find_vscode_settings(home)
    if not path:
        print("  · VS Code: no encontrado, salto")
        return
    print(f"· VS Code → {path}")
    d = load_json(path)
    backup(path, ctx)
    colors = render.vscode_colors(pal)

    if remove:
        cc = d.get("workbench.colorCustomizations", {})
        for k in colors:
            cc.pop(k, None)
        if not cc:
            d.pop("workbench.colorCustomizations", None)
        for k in ("terminal.integrated.fontFamily", "terminal.integrated.fontSize",
                  "terminal.integrated.cursorStyle", "terminal.integrated.cursorBlinking"):
            d.pop(k, None)
        ctx.say(f"{len(colors)} claves de color retiradas")
    else:
        cc = d.setdefault("workbench.colorCustomizations", collections.OrderedDict())
        cc.update(colors)
        f = pal["font"]
        d["terminal.integrated.fontFamily"] = f"'{f['face']}', 'Cascadia Mono', monospace"
        d["terminal.integrated.fontSize"] = f["sizeVSCode"]
        d["terminal.integrated.cursorStyle"] = "block"
        d["terminal.integrated.cursorBlinking"] = True
        ctx.say(f"{len(colors)} claves de color + fuente {f['face']}")
    dump_json(path, d, ctx, indent=4, ascii_=False)
    ctx.note("VS Code")


# ── perfil de PowerShell ──────────────────────────────────────────────
def apply_ps(pal: dict, home, ctx: Ctx, remove: bool = False):
    path = find_ps_profile(home)
    if not path:
        print("  · PowerShell: no localizo Documents\\WindowsPowerShell, salto")
        return
    print(f"· PowerShell → {path}")
    if remove:
        if path.exists():
            backup(path, ctx)
            ctx.say("perfil borrado (queda el .bak)")
            if not ctx.dry:
                path.unlink()
        ctx.note("PowerShell")
        return

    tmpl = (render.ROOT / "windows/Microsoft.PowerShell_profile.ps1.tmpl").read_text(encoding="utf-8")
    for key, val in render.ps_substitutions(pal).items():
        tmpl = tmpl.replace(f"@@{key}@@", val)
    left = [t for t in tmpl.split("@@") if t.isupper() and t.isidentifier()]
    if left:
        sys.exit(f"placeholders sin resolver en la plantilla: {sorted(set(left))}")
    backup(path, ctx)
    ctx.say("perfil escrito (UTF-8 con BOM, CRLF)")
    if not ctx.dry:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="\r\n") as fh:
            fh.write(tmpl)
    ctx.note("PowerShell")


# ── acento de Windows ─────────────────────────────────────────────────
def apply_accent(pal: dict, home, ctx: Ctx, remove: bool = False):
    if not shutil.which("reg.exe"):
        print("  · acento: reg.exe no accesible (¿interop de WSL apagado?), salto")
        return
    print("· acento de Windows → registro HKCU")
    if remove:
        print("  el acento no se revierte solo: restaura los .reg de claude-theme-backup")
        return

    if home:
        bdir = home / "claude-theme-backup"
        ctx.say(f"exportando claves a {bdir}")
        if not ctx.dry:
            bdir.mkdir(exist_ok=True)
            wdir = subprocess.run(["wslpath", "-w", str(bdir)], capture_output=True,
                                  text=True).stdout.strip()
            for key in (r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Accent",
                        r"HKCU\Software\Microsoft\Windows\DWM",
                        r"HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"):
                out = os.path.join(wdir, key.rsplit("\\", 1)[-1] + f".{STAMP}.reg")
                subprocess.run(["reg.exe", "export", key, out, "/y"],
                               capture_output=True, cwd="/mnt/c")

    for key, name, typ, data in render.registry_values(pal):
        ctx.snap.capture_reg(key, name)
        ctx.say(f"{name} = {data}")
        if not ctx.dry:
            r = subprocess.run(["reg.exe", "add", key, "/v", name, "/t", typ,
                                "/d", data, "/f"], capture_output=True, cwd="/mnt/c")
            if r.returncode != 0:
                print(f"    ! falló {name}: {r.stderr.decode('cp850', 'replace').strip()}")
    if not ctx.dry:
        subprocess.run(["rundll32.exe", "user32.dll,UpdatePerUserSystemParameters", "1", ",", "True"],
                       capture_output=True, cwd="/mnt/c")
    ctx.note("acento de Windows")
    print("  el escritorio no repinta del todo hasta reiniciar explorer:")
    print("    powershell.exe -Command \"Stop-Process -Name explorer -Force\"")


# ── el registro de pasos ──────────────────────────────────────────────
# ESTA es la lista de pasos, y la única. De aquí salen el orden de ejecución, el
# --skip y su texto de ayuda, así que añadir un paso es añadir una línea.
#
# Antes había tres listas que nadie comprobaba entre sí: los nueve `if`, el
# literal del help y el orden. Ya habían derivado — el help decía
# «icons,launcher» cuando se ejecutaba launcher antes que icons.
#
# `run(ctx)` devuelve True si hace falta reiniciar explorer para ver el cambio.
#
# Las firmas de abajo NO son uniformes: apply_taskbar recibe (snap, ctx, pal) y
# apply_pinned_icons (pal, snap, ctx, home). Se adaptan aquí a propósito, en vez
# de tocarlas, porque este cambio no toca comportamiento. Por lo mismo los
# cuatro primeros pasos llaman a ctx.note() por dentro y los cinco últimos desde
# aquí: se respeta tal cual estaba.
Step = collections.namedtuple("Step", "key label run")


def build_steps(pal: dict | None, home) -> list[Step]:
    """Los pasos, en orden. Las funciones son perezosas: construir la lista no
    ejecuta nada, y por eso se puede llamar con (None, None) solo para leer las
    claves antes de tener la paleta cargada."""
    def wt(ctx):      apply_wt(pal, ctx);           return False
    def vscode(ctx):  apply_vscode(pal, home, ctx); return False
    def ps(ctx):      apply_ps(pal, home, ctx);     return False

    def accent(ctx):
        apply_accent(pal, home, ctx)
        desktop.broadcast_colorchange(ctx)     # escribirlo no lo aplica; hay que avisar
        return False

    def taskbar(ctx):
        restart = desktop.apply_taskbar(ctx.snap, ctx, pal)
        ctx.note("barra de tareas")             # se anota siempre, como antes
        return restart

    def menu(ctx):
        if desktop.apply_context_menu(ctx.snap, ctx):
            ctx.note("menú contextual")
        return False

    def launcher(ctx):
        if flow.apply(pal, ctx.snap, ctx, home):
            ctx.note("buscador flotante")
        return False

    def keymap(ctx):
        if not keys.apply(pal, ctx.snap, ctx, home):
            return False
        ctx.note("atajos de ventanas")
        return False

    def icons(ctx):
        if not desktop.apply_pinned_icons(pal, ctx.snap, ctx, home):
            return False
        ctx.note("iconos de los anclados")
        return True

    def windhawk(ctx):
        if not desktop.apply_windhawk(pal, ctx.snap, ctx, home):
            return False
        ctx.note("Windhawk")
        return True

    return [
        Step("wt",       "Windows Terminal",       wt),
        Step("vscode",   "VS Code",                vscode),
        Step("ps",       "PowerShell",             ps),
        Step("accent",   "acento de Windows",      accent),
        Step("taskbar",  "barra de tareas",        taskbar),
        Step("menu",     "menú contextual",        menu),
        Step("launcher", "buscador flotante",      launcher),
        Step("keys",     "atajos de ventanas",     keymap),
        Step("icons",    "iconos de los anclados", icons),
        Step("windhawk", "Windhawk",               windhawk),
    ]


STEP_KEYS = [s.key for s in build_steps(None, None)]


# ── main ──────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Aplica el tema Claude CLI al lado Windows")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--skip", default="",
                    help="lista separada por comas: " + ",".join(STEP_KEYS))
    args = ap.parse_args()

    if not pathlib.Path("/mnt/c").is_dir():
        sys.exit("no veo /mnt/c: esto hay que lanzarlo desde WSL")

    pal = render.load()
    home = win_userprofile()

    if args.uninstall:
        uninstall.run(dry=args.dry_run, win_home=home)
        return

    ctx = Ctx(args.dry_run)
    steps = build_steps(pal, home)
    skip = {s.strip() for s in args.skip.split(",") if s.strip()}
    # Antes un `--skip windhwak` se aplicaba entero sin decir nada. Ahora para.
    unknown = skip - {s.key for s in steps}
    if unknown:
        sys.exit(f"--skip no conoce: {', '.join(sorted(unknown))}\n"
                 f"los pasos son: {', '.join(s.key for s in steps)}")
    print(f"paleta «{pal['name']}» · %USERPROFILE% = {home or 'desconocido'}\n")

    restart = False
    for step in steps:
        if step.key not in skip:
            restart |= bool(step.run(ctx))

    ctx.snap.save()
    print("\n" + ("nada que hacer" if not ctx.changed else "listo: " + ", ".join(ctx.changed)))
    if restart and not ctx.dry:
        print("\nreinicia explorer para ver el dock y la barra:")
        print("  powershell.exe -Command \"Stop-Process -Name explorer -Force\"")


if __name__ == "__main__":
    main()
