#!/usr/bin/env python3
"""Genera los artefactos derivados de palette.json.

palette.json es la única fuente de verdad: todo lo que se instala (variables de
zsh, esquema de Windows Terminal, bloque de VS Code, perfil de PowerShell y los
valores de registro del acento) sale de aquí.
"""
from __future__ import annotations
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load(path: pathlib.Path | None = None) -> dict:
    return json.loads((path or ROOT / "palette.json").read_text(encoding="utf-8"))


# ── conversiones de color ─────────────────────────────────────────────
def rgb(hex_: str) -> tuple[int, int, int]:
    h = hex_.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def sgr(hex_: str, layer: str = "fg") -> str:
    """#RRGGBB → '38;2;R;G;B' (o 48;… para fondo)."""
    r, g, b = rgb(hex_)
    return f"{38 if layer == 'fg' else 48};2;{r};{g};{b}"


def abgr(hex_: str, alpha: str = "FF") -> str:
    """#RRGGBB → 0xAABBGGRR, el orden que usa el registro de Windows."""
    r, g, b = rgb(hex_)
    return f"0x{alpha.lower()}{b:02x}{g:02x}{r:02x}"


def argb(hex_: str, alpha: str = "FF") -> str:
    """#RRGGBB → 0xAARRGGBB, el orden de ColorizationColor."""
    r, g, b = rgb(hex_)
    return f"0x{alpha.lower()}{r:02x}{g:02x}{b:02x}"


def accent_palette_blob(ramp: list[str]) -> str:
    """Los 8 tonos → 32 bytes 'RRGGBB00' concatenados, como los guarda Windows."""
    if len(ramp) != 8:
        raise ValueError(f"windowsAccent.ramp debe tener 8 colores, tiene {len(ramp)}")
    return "".join(c.lstrip("#").upper() + "00" for c in ramp)


# ── artefactos ────────────────────────────────────────────────────────
def palette_zsh(p: dict) -> str:
    out = [
        "# GENERADO por lib/render.py desde palette.json — no editar a mano.",
        "# Cambia palette.json y vuelve a lanzar ./install.sh",
        "",
    ]
    for name, role in p["roles"].items():
        u = name.upper()
        out.append(f"typeset -g CC_HEX_{u}='{role['hex']}'")
        out.append(f"typeset -g CC_HEXB_{u}='{role['bright']}'")
        out.append(f"typeset -g CC_{u}='{sgr(role['hex'])}'")
    out.append("")
    for name, hex_ in p["surfaces"].items():
        u = name.upper()
        out.append(f"typeset -g CC_HEX_{u}='{hex_}'")
        out.append(f"typeset -g CC_{u}='{sgr(hex_)}'")
    # ¿La fuente del terminal trae los glifos de la zona de uso privado? eza y
    # compañía los usan para sus iconos, y Cascadia Code a secas NO los tiene:
    # sin esto salen todos como «?».
    out.append(f"typeset -g CC_NERD_GLYPHS='{1 if p['font'].get('nerdGlyphs') else 0}'")
    out.append(f"typeset -g CC_BG_SEL='{sgr(p['surfaces']['selection'], 'bg')}'")
    out.append(f"typeset -g CC_BG_DARK='{sgr(p['surfaces']['bgAlt'], 'bg')}'")
    out.append("")
    return "\n".join(out) + "\n"


def wt_scheme(p: dict) -> dict:
    a = p["ansi"]
    return {
        "name": p["name"],
        "background": p["surfaces"]["bg"],
        "foreground": p["surfaces"]["fg"],
        "cursorColor": p["roles"]["teal"]["hex"],
        "selectionBackground": p["surfaces"]["selection"],
        **{k: v for k, v in a.items()},
    }


def wt_theme(p: dict) -> dict:
    return {
        "name": p["name"],
        "window": {"applicationTheme": "dark"},
        "tab": {"background": p["surfaces"]["bgAlt"],
                "unfocusedBackground": p["surfaces"]["bg"],
                "showCloseButton": "always"},
        "tabRow": {"background": p["surfaces"]["bg"],
                   "unfocusedBackground": "#050708"},
    }


def wt_defaults(p: dict) -> dict:
    return {
        "colorScheme": p["name"],
        "font": {"face": p["font"]["face"], "size": p["font"]["sizeTerminal"], "weight": "normal"},
        "padding": "14, 10, 14, 10",
        "cursorShape": "filledBox",
        "antialiasingMode": "grayscale",
        "scrollbarState": "hidden",
        "useAcrylic": False,
        "opacity": 100,
        "intenseTextStyle": "bright",
        "historySize": 20000,
        "bellStyle": "none",
        "experimental.retroTerminalEffect": False,
    }


def vscode_colors(p: dict) -> dict:
    s, a, r = p["surfaces"], p["ansi"], p["roles"]
    cap = lambda k: k[0].upper() + k[1:]
    out = {
        "terminal.background": s["bg"],
        "terminal.foreground": s["fg"],
        "terminal.border": s["border"],
        "terminal.selectionBackground": s["selection"],
        "terminalCursor.foreground": r["teal"]["hex"],
        "terminalCursor.background": s["bg"],
        "terminal.inactiveSelectionBackground": "#0F1F24",
        "terminal.findMatchBackground": p["windowsAccent"]["start"],
        "terminal.findMatchHighlightBackground": p["windowsAccent"]["ramp"][5],
        "panel.background": s["bg"],
        "panel.border": s["border"],
    }
    for k, v in a.items():
        out[f"terminal.ansi{cap(k)}"] = v
    return out


def registry_values(p: dict) -> list[tuple[str, str, str, str]]:
    """(clave, nombre, tipo, dato) — lo que escribe el instalador."""
    w = p["windowsAccent"]
    A = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Accent"
    D = r"HKCU\Software\Microsoft\Windows\DWM"
    al = w["colorizationAlpha"]
    return [
        (A, "AccentPalette",         "REG_BINARY", accent_palette_blob(w["ramp"])),
        (A, "AccentColorMenu",       "REG_DWORD",  abgr(w["base"])),
        (A, "StartColorMenu",        "REG_DWORD",  abgr(w["start"])),
        (D, "AccentColor",           "REG_DWORD",  abgr(w["base"])),
        (D, "AccentColorInactive",   "REG_DWORD",  abgr(w.get("inactiveBorder", w["start"]))),
        (D, "ColorizationColor",     "REG_DWORD",  argb(w["base"], al)),
        (D, "ColorizationAfterglow", "REG_DWORD",  argb(w["base"], al)),
    ]


def ps_substitutions(p: dict) -> dict[str, str]:
    """Placeholders @@NOMBRE@@ del perfil de PowerShell."""
    sub = {"FG": sgr(p["surfaces"]["fg"]), "SEL": sgr(p["surfaces"]["selection"], "bg")}
    for name, role in p["roles"].items():
        sub[name.upper()] = sgr(role["hex"])
    for name, role in p["roles"].items():
        sub[f"HEX_{name.upper()}"] = role["hex"]
    return sub


# ── atajos ────────────────────────────────────────────────────────────
# El chuletario vive en palette.json y las ataduras en el código. Aquí solo se
# traduce lo primero al idioma de cada superficie: arrays de zsh para la tira
# del prompt, y un literal de AutoHotkey para el OSD de Windows.
#
# La duplicación entre lo que se ENSEÑA y lo que está ATADO la vigila
# lib/selftest.py, que pregunta a `bindkey` por cada tecla anunciada. Sin eso
# las dos listas derivan y el chuletario acaba mintiendo, que es peor que no
# tenerlo.
def app_hints(p: dict) -> list[list[str]]:
    """Las teclas del submapa «abrir», derivadas de keys.windows.apps.

    No se escriben a mano en `modes.apps.hints` a propósito: la tecla, la
    etiqueta y el ejecutable son el mismo dato y viven en una sola línea.
    """
    apps = p["keys"]["windows"].get("apps", [])
    return [[key, label] for key, label, _run in apps] + [["Esc", "volver"]]


def mode_hints(p: dict, surface: str, mode: str) -> list[list[str]]:
    m = p["keys"][surface]["modes"][mode]
    if surface == "windows" and mode == "apps":
        return app_hints(p)
    return [list(h) for h in m.get("hints", [])]


def _zq(s: str) -> str:
    """Entre comillas SIMPLES para zsh: nada se expande, ni un $EDITOR de una
    descripción ni un `$` de los atajos de línea. La comilla simple se cierra,
    se escapa y se reabre, que es la única forma que tiene zsh."""
    return "'" + s.replace("'", "'\\''") + "'"


def keymap_zsh(p: dict) -> str:
    """claude-35-keymap.zsh — el chuletario y los ajustes, para la capa 40."""
    k = p["keys"]
    sh = k["shell"]
    # palette.json escribe las rutas con ~ porque el lado Windows también las
    # lee. Dentro de comillas dobles zsh NO expande la tilde, así que aquí se
    # traduce a $HOME o CC_KEYS_STATE apuntaría a un directorio llamado «~».
    statefile = k["stateFile"].replace("~/", "$HOME/")
    out = [
        "# GENERADO por lib/render.py desde palette.json — no editar a mano.",
        "# Cambia palette.json y vuelve a lanzar ./install.sh",
        "#",
        "# Solo DATOS. Quien los ata a teclas es claude-40-keys.zsh.",
        "",
        f"typeset -g CC_KEYS_HINTS='{k.get('hints', 'on')}'",
        f'typeset -g CC_KEYS_STATE="{statefile}"',
        f"typeset -g CC_KEYS_TIMEOUT='{int(sh.get('keyTimeout', 15))}'",
        f"typeset -g CC_KEYS_ESCAPE='{sh.get('escape', '')}'",
        f"typeset -g CC_KEYS_HOTKEY='{k['windows'].get('hotkeyLabel', '')}'",
    ]
    cur = sh.get("cursor", {})
    for name in ("normal", "insert", "replace"):
        out.append(f"typeset -g CC_KEYS_CURSOR_{name.upper()}='{int(cur.get(name, 2))}'")
    showin = " ".join(f"'{m}'" for m in sh.get("showIn", []))
    out.append(f"typeset -ga CC_KEYS_SHOWIN=({showin})")
    out.append("")

    # Un array plano de pares por modo: zsh no tiene arrays de arrays, y un
    # asociativo perdería el orden, que aquí es el orden en que se aprenden.
    for surface in ("shell", "windows"):
        for mode in k[surface]["modes"]:
            m = k[surface]["modes"][mode]
            var = f"CC_KEYS_{surface.upper()}_{mode.upper()}"
            out.append(f"typeset -g {var}_BADGE='{m['badge']}'")
            out.append(f"typeset -g {var}_ROLE='{p['roles'][m['role']]['hex']}'")
            pairs = " ".join(_zq(c) for h in mode_hints(p, surface, mode) for c in h)
            out.append(f"typeset -ga {var}=({pairs})")
        names = " ".join(f"'{m}'" for m in k[surface]["modes"])
        out.append(f"typeset -ga CC_KEYS_{surface.upper()}_MODES=({names})")
        out.append("")
    return "\n".join(out) + "\n"


def _ahk_str(s: str) -> str:
    """Literal de AutoHotkey v2: solo las comillas dobles se escapan, duplicándolas."""
    return '"' + s.replace('"', '""') + '"'


def ahk_substitutions(p: dict) -> dict[str, str]:
    """Placeholders @@NOMBRE@@ del script de AutoHotkey."""
    k, s, ro = p["keys"], p["surfaces"], p["roles"]
    w = k["windows"]
    osd = w["osd"]

    modes = []
    for mode, m in w["modes"].items():
        hints = ", ".join(f"[{_ahk_str(a)}, {_ahk_str(b)}]"
                          for a, b in mode_hints(p, "windows", mode))
        modes.append(
            f'MODES[{_ahk_str(mode)}] := {{ badge: {_ahk_str(m["badge"])}, '
            f'role: {_ahk_str(ro[m["role"]]["hex"].lstrip("#"))}, hints: [{hints}] }}')

    apps = [f'APPS[{_ahk_str(key)}] := {_ahk_str(run)}'
            for key, _label, run in w.get("apps", [])]

    def bare(hex_: str) -> str:
        return hex_.lstrip("#")

    return {
        "HOTKEY":        w["hotkey"],
        "HOTKEY_LABEL":  w.get("hotkeyLabel", w["hotkey"]),
        "EXIT_KEY":      w.get("exitKey", "Escape"),
        "PASSTHROUGH":   str(int(w.get("passthroughMs", 400))),
        "OSD_HEIGHT":    str(int(osd.get("height", 34))),
        "OSD_RADIUS":    str(int(osd.get("cornerRadius", 10))),
        "OSD_MARGIN":    str(int(osd.get("marginBottom", 10))),
        "OSD_PADDING":   str(int(osd.get("padding", 14))),
        "OSD_FONTSIZE":  str(int(osd.get("fontSize", 10))),
        "FONT":          p["windowsDesktop"]["clock"].get("fontFamily", "Cascadia Mono"),
        "BG":            bare(s["bg"]),
        "BORDER":        bare(s["border"]),
        "KEYCOLOR":      bare(ro["green"]["hex"]),
        "DESCCOLOR":     bare(ro["grey"]["hex"]),
        "MODES":         "\n".join(modes),
        "APPS":          "\n".join(apps) or ";  (sin apps definidas en palette.json)",
    }


if __name__ == "__main__":
    pal = load()
    what = sys.argv[1] if len(sys.argv) > 1 else "palette.zsh"
    if what == "palette.zsh":
        sys.stdout.write(palette_zsh(pal))
    elif what == "scheme":
        json.dump(wt_scheme(pal), sys.stdout, indent=2, ensure_ascii=False)
    elif what == "vscode":
        json.dump(vscode_colors(pal), sys.stdout, indent=2, ensure_ascii=False)
    elif what == "registry":
        for k, n, t, d in registry_values(pal):
            print(f"{k}\t{n}\t{t}\t{d}")
    elif what == "keymap.zsh":
        sys.stdout.write(keymap_zsh(pal))
    elif what == "keys.ahk":
        for k, v in ahk_substitutions(pal).items():
            print(f"{k}\t{v}")
    else:
        sys.exit(f"artefacto desconocido: {what}")
