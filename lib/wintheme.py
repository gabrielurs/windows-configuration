#!/usr/bin/env python3
"""El tema de Windows, guardado con nombre.

Solo si la paleta trae `windowsDesktop.themeName`.

Todo lo que este repo cambia de Personalización (fondo, acento, modo claro) lo
cambia por el registro o por la API, y Windows lo recoge en `Custom.theme`, que
enseña como «Tema sin guardar». Ese fichero es de usar y tirar: elegir cualquier
otro tema en Configuración lo pisa, y con él se va la única copia de «fondo +
acento + modo» que Windows sabe volver a poner de un clic.

Esto NO aplica un tema —aplicar un .theme reescribe fondo, colores y sonidos, y
es justo lo que no se quiere—. Copia el que Windows ya tiene escrito y le pone
nombre: la copia sale en la galería de Configuración > Personalización > Temas,
y se vuelve a ella de un clic. Lo que hay en pantalla no cambia.

«Tema actual» sigue diciendo «Personalizado», y no tiene arreglo sin aplicarlo:
se probó a apuntar `CurrentTheme` a la copia (2026-11-16) y Configuración lo
devuelve a `Custom.theme` nada más abrir la página de Temas.

Los punteros no viajan en el tema: se copia la sección tal cual, y en esta
máquina `ThemeChangesMousePointers` es 0, así que Windows la ignora.
"""
from __future__ import annotations
import pathlib, re, subprocess, sys, uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import state  # noqa: E402

THEMES = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Themes"
# El GUID sale del nombre: reinstalar no cambia de identidad al tema.
NS = uuid.UUID("7a45d383-7335-4327-9e88-a7d68c77cdca")


def _unix(win: str) -> pathlib.Path | None:
    r = subprocess.run(["wslpath", "-u", win], capture_output=True, text=True)
    return pathlib.Path(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None


def _win(path) -> str:
    return subprocess.run(["wslpath", "-w", str(path)],
                          capture_output=True, text=True).stdout.strip()


def named(text: str, name: str) -> str:
    """El mismo .theme con otro DisplayName y otro ThemeId. Si no trae alguno de
    los dos, devuelve '' y no se guarda nada: mejor sin nombre que a medias."""
    tid = "{" + str(uuid.uuid5(NS, name)).upper() + "}"
    out, n1 = re.subn(r"(?m)^DisplayName=.*$", lambda _: f"DisplayName={name}", text, count=1)
    out, n2 = re.subn(r"(?m)^ThemeId=.*$", lambda _: f"ThemeId={tid}", out, count=1)
    return out if n1 and n2 else ""


def apply(pal: dict, snap: state.Snapshot, ctx, win_home) -> bool:
    name = pal["windowsDesktop"].get("themeName")
    if not name or not win_home:
        return False
    print("· tema de Windows con nombre")
    cur = state.read_reg(THEMES, "CurrentTheme")
    src = _unix(cur[1]) if cur else None
    if src and src.name == f"{name}.theme":
        ctx.say(f"el tema actual ya es «{name}»")
        return False
    if not src or not src.is_file():
        ctx.say("! no encuentro el tema actual; lo dejo como está")
        return False
    dest = win_home / "AppData/Local/Microsoft/Windows/Themes" / f"{name}.theme"
    # cp1252 y sin BOM, que es como los escribe Windows (el © de la cabecera)
    want = named(src.read_text(encoding="cp1252"), name)
    if not want:
        ctx.say("! el tema actual no trae DisplayName o ThemeId; no lo toco")
        return False
    if dest.is_file() and dest.read_text(encoding="cp1252") == want:
        ctx.say(f"«{name}» ya está guardado y al día")
        return False
    snap.capture_file(dest)
    snap.save()
    ctx.say(f"«{name}» ← {src.name}")
    if ctx.dry:
        return True
    dest.write_text(want, encoding="cp1252", newline="\r\n")
    return True
