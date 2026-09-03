#!/usr/bin/env python3
"""Los atajos de vim para las ventanas de Windows, con su banda de ayuda.

Windows no tiene nada parecido a un modo de teclado, así que —igual que con el
buscador— en vez de pelearse con él se pone al lado algo que sí obedece:
AutoHotkey v2, con un script generado desde palette.json.

Lo que deja instalado, todo bajo %LOCALAPPDATA%\\claude-terminal-theme:

    claude-keys.ahk    el script, con los colores y el chuletario resueltos
    keys-idle.ico      el icono de bandeja fuera del modo (gris)
    keys-active.ico    y dentro del modo (teal) — lo único de la barra de
                       tareas que reacciona al instante
    hints              «on» u «off»; lo escribe `claude-keys` desde la shell y
                       lo sondea el script. Un interruptor, dos superficies.

El paso manual que NO hay: AutoHotkey se instala con winget desde lib/deps.sh.
Si no está, este paso se salta diciéndolo y el resto del tema va igual.
"""
from __future__ import annotations
import glob, pathlib, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import render, icons  # noqa: E402

RUN_KEY = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "ClaudeKeys"
APPDIR = "AppData/Local/claude-terminal-theme"
SCRIPT = "claude-keys.ahk"
TRAY_GLYPH = "❯"


def find_ahk(win_home: pathlib.Path | None) -> pathlib.Path | None:
    """El intérprete de AutoHotkey **v2**.

    La v1 no vale y hay que descartarla a propósito: su ejecutable se llama
    igual y vive en el directorio de al lado, así que un glob descuidado coge la
    v1, el script no compila y el error que sale —«This line does not contain a
    recognized action»— no dice en ningún momento que el problema sea la versión.
    """
    pats = [
        "/mnt/c/Program Files/AutoHotkey/v2/AutoHotkey*.exe",
        "/mnt/c/Program Files (x86)/AutoHotkey/v2/AutoHotkey*.exe",
    ]
    if win_home:
        pats.append(str(win_home / "AppData/Local/Programs/AutoHotkey/v2/AutoHotkey*.exe"))
    hits = [pathlib.Path(h) for pat in pats for h in glob.glob(pat)]
    # AutoHotkey64.exe antes que AutoHotkey32.exe, y nunca los *_UIA.exe
    hits = [h for h in hits if "UIA" not in h.name]
    hits.sort(key=lambda p: ("64" not in p.name, p.name))
    return hits[0] if hits else None


def render_script(pal: dict) -> str:
    tmpl = (render.ROOT / "windows/claude-keys.ahk.tmpl").read_text(encoding="utf-8")
    for key, val in render.ahk_substitutions(pal).items():
        tmpl = tmpl.replace(f"@@{key}@@", val)
    left = [t for t in tmpl.split("@@") if t.isupper() and t.isidentifier()]
    if left:
        sys.exit(f"placeholders sin resolver en claude-keys.ahk.tmpl: {sorted(set(left))}")
    return tmpl


def apply(pal: dict, snap, ctx, win_home, remove: bool = False) -> bool:
    """Deja el script, sus iconos y el arranque. True si tocó algo."""
    if remove:
        return False
    print("· atajos de ventanas (AutoHotkey)")
    if not win_home:
        ctx.say("no localizo %USERPROFILE%, salto")
        return False

    ahk = find_ahk(win_home)
    if not ahk:
        ctx.say("AutoHotkey v2 no está — winget install AutoHotkey.AutoHotkey")
        ctx.say("(el modo de la shell funciona igual; esto es solo el lado Windows)")
        return False

    outdir = win_home / APPDIR
    script = outdir / SCRIPT
    hints = outdir / "hints"
    ico_idle = outdir / "keys-idle.ico"
    ico_active = outdir / "keys-active.ico"

    for f in (script, hints, ico_idle, ico_active):
        snap.capture_file(f)
    snap.capture_reg(RUN_KEY, RUN_NAME)

    k = pal["keys"]
    if ctx.dry:
        ctx.say(f"{SCRIPT} + 2 iconos en {outdir}")
        ctx.say(f"modo con {k['windows'].get('hotkeyLabel')}, banda «{k.get('hints')}»")
        ctx.say(f"arranque en {RUN_NAME} → {ahk.name} {SCRIPT}")
        return True

    outdir.mkdir(parents=True, exist_ok=True)
    # CRLF y sin BOM: AutoHotkey lee UTF-8 y el BOM le da igual, pero el CRLF
    # importa si algún día alguien abre esto con el Bloc de notas.
    with script.open("w", encoding="utf-8", newline="\r\n") as fh:
        fh.write(render_script(pal))
    ctx.say(f"{SCRIPT} generado desde la paleta")

    tray = k["windows"].get("tray", {})
    bg = pal["surfaces"]["bgAlt"]
    icons.make_ico(TRAY_GLYPH, pal["roles"][tray.get("idleRole", "grey")]["hex"],
                   ico_idle, bg=bg)
    icons.make_ico(TRAY_GLYPH, pal["roles"][tray.get("activeRole", "teal")]["hex"],
                   ico_active, bg=bg)
    ctx.say("iconos de bandeja: gris fuera del modo, teal dentro")

    # El estado de fábrica de palette.json solo se escribe si el usuario no ha
    # decidido ya: si el fichero está, es que alguien hizo `claude-keys off` y
    # reinstalar no es motivo para volverle a encender la banda.
    if not hints.exists():
        hints.write_text(k.get("hints", "on"), encoding="utf-8")
    ctx.say(f"banda: {hints.read_text(encoding='utf-8').strip()}")

    win_ahk = _winpath(ahk)
    win_script = _winpath(script)
    subprocess.run(["reg.exe", "add", RUN_KEY, "/v", RUN_NAME, "/t", "REG_SZ",
                    "/d", f'"{win_ahk}" "{win_script}"', "/f"],
                   capture_output=True, cwd="/mnt/c")
    ctx.say("arranca con el equipo")

    # #SingleInstance Force hace que el nuevo desaloje al viejo, así que no hace
    # falta matar nada: basta con lanzarlo.
    subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                    f"Start-Process '{win_ahk}' -ArgumentList '\"{win_script}\"'"],
                   capture_output=True, cwd="/mnt/c")
    ctx.say(f"en marcha — {k['windows'].get('hotkeyLabel')} abre el modo")
    return True


def stop(dry: bool = False) -> None:
    """Para el script. Lo llama el desinstalador antes de borrar el fichero."""
    if dry:
        print("  [dry] parando claude-keys.ahk")
        return
    r = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process -Filter \"Name LIKE 'AutoHotkey%'\" | "
         "Where-Object { $_.CommandLine -like '*claude-keys.ahk*' } | "
         "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
        capture_output=True, cwd="/mnt/c")
    if r.returncode == 0:
        print("  claude-keys.ahk parado")


def _winpath(p: pathlib.Path) -> str:
    return subprocess.run(["wslpath", "-w", str(p)],
                          capture_output=True, text=True).stdout.strip()


if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(SCRIPT)
    out.write_text(render_script(render.load()), encoding="utf-8")
    print(f"  {SCRIPT} → {out}")
