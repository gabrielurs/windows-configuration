#!/usr/bin/env python3
"""Genera los iconos de los accesos directos anclados a la barra.

El diseño dibuja cada app como un glifo monoespaciado en su color de la paleta.
Eso solo se puede aplicar a lo que está ANCLADO: el icono de un acceso directo
sí es nuestro, pero el de una app en ejecución lo pone la propia app y no hay
por dónde cogerlo sin tocar sus binarios.

Un .ico con varios tamaños, fondo transparente y el glifo centrado.

Aviso sobre el resultado: Windows enseña el icono del acceso directo solo
mientras la app NO está en ejecución. En cuanto se abre, la barra pasa a usar el
icono de la propia ventana. O sea que esto se nota en los anclados en reposo, no
en los que están abiertos.
"""
from __future__ import annotations
import glob, pathlib, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import render  # noqa: E402

SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)

# glifo y rol de la paleta para cada app, tal cual los asigna el diseño
APPS = {
    "File Explorer": ("▤", "teal"),
    "Google Chrome": ("◉", "purple"),
    "Windows Terminal": ("❯", "green"),
    "Visual Studio Code": ("◈", "blue"),
    "Claude": ("✦", "amber"),
    "Ubuntu": ("❯", "green"),
}

# Ojo: NO vale comprobar la cobertura con `font.getmask(g).getbbox()`. El glifo
# ausente se dibuja como un rectángulo, que también tiene caja, así que esa
# comprobación da positivo para cualquier fuente y se acaban generando iconos
# llenos de tofu. Hay que preguntar por el codepoint de verdad.
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _fonts_with(glyphs: str) -> set[str]:
    """Fuentes que cubren TODOS estos codepoints, según fontconfig.

    Se usa fc-list en vez de una librería de fuentes para no añadir dependencias:
    fontconfig ya está en cualquier Linux con fuentes instaladas.
    """
    charset = " ".join(f"{ord(g):04X}" for g in glyphs)
    try:
        out = subprocess.run(["fc-list", f":charset={charset}", "file"],
                             capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return set()
    return {ln.split(":")[0].strip() for ln in out.splitlines() if ln.strip()}


def _font_path(glyphs: str = "") -> str:
    ok = _fonts_with(glyphs) if glyphs else set()
    for c in FONT_CANDIDATES:
        if pathlib.Path(c).exists() and (not glyphs or c in ok):
            return c
    if ok:
        return sorted(ok)[0]
    raise RuntimeError(
        f"ninguna fuente del sistema cubre estos glifos: {glyphs!r}. "
        "Instala fonts-dejavu-core.")


def make_ico(glyph: str, hex_color: str, out: pathlib.Path,
             bg: str | None = None, radius_ratio: float = 0.22) -> pathlib.Path:
    from PIL import Image, ImageDraw, ImageFont
    font_path = _font_path(glyph)
    base = 256
    im = Image.new("RGBA", (base, base), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    if bg:
        r = int(base * radius_ratio)
        d.rounded_rectangle([0, 0, base - 1, base - 1], radius=r,
                            fill=render.rgb(bg) + (255,))

    # buscar el tamaño de fuente que llene ~62% del lienzo
    size = base
    while size > 8:
        f = ImageFont.truetype(font_path, size)
        bbox = d.textbbox((0, 0), glyph, font=f)
        if (bbox[2] - bbox[0]) <= base * 0.62 and (bbox[3] - bbox[1]) <= base * 0.62:
            break
        size -= 4
    f = ImageFont.truetype(font_path, size)
    bbox = d.textbbox((0, 0), glyph, font=f)
    x = (base - (bbox[2] - bbox[0])) / 2 - bbox[0]
    y = (base - (bbox[3] - bbox[1])) / 2 - bbox[1]
    d.text((x, y), glyph, font=f, fill=render.rgb(hex_color) + (255,))

    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, format="ICO", sizes=[(s, s) for s in SIZES])
    return out


def build_all(pal: dict, outdir: pathlib.Path) -> dict[str, pathlib.Path]:
    """Un .ico por app conocida. Devuelve {nombre de app: ruta}."""
    made = {}
    bg = pal["surfaces"]["bgAlt"]
    for app, (glyph, role) in APPS.items():
        color = pal["roles"][role]["hex"]
        made[app] = make_ico(glyph, color, outdir / f"{role}-{app.replace(' ', '-')}.ico", bg=bg)
    return made


if __name__ == "__main__":
    pal = render.load()
    out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else render.ROOT / "windows/icons"
    for app, path in build_all(pal, out).items():
        print(f"  {app:22} → {path.name}")
