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


def _overlay(base: dict, over: dict) -> dict:
    """Superpone `over` sobre una COPIA de `base`, clave a clave. Las claves «_»
    son notas y no se copian: si no, una nota del bloque claro taparía la del
    oscuro y el diccionario resultante mentiría sobre de dónde sale cada valor."""
    out = dict(base)
    for k, v in over.items():
        if k.startswith("_"):
            continue
        out[k] = _overlay(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def desktop(p: dict) -> dict:
    """La paleta que ve el ESCRITORIO de Windows: la de siempre en oscuro, y en
    claro la misma con el bloque `light` encima."""
    if p.get("windowsMode", "dark") != "light":
        return p
    return _overlay(p, p.get("light", {}))


def terminal(p: dict) -> dict:
    """La paleta de Windows Terminal, PowerShell y zsh, con su propio
    interruptor (`terminalMode`). VS Code no pasa por aquí: su workbench es
    oscuro y su terminal se queda con la paleta de siempre."""
    if p.get("terminalMode", "dark") != "light":
        return p
    return _overlay(p, p.get("light", {}))


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
    head = [
        "# GENERADO por lib/render.py desde palette.json — no editar a mano.",
        "# Cambia palette.json y vuelve a lanzar ./install.sh",
        "",
    ]
    if p.get("terminalMode", "dark") != "light":
        return "\n".join(head + _palette_zsh_vars(p)) + "\n"
    # zsh es el mismo en Windows Terminal y en VS Code, pero VS Code se queda
    # oscuro: los pasteles del claro sobre su fondo negro, o al revés, no se
    # leen. La paleta se elige al arrancar la shell, por el terminal que la abre.
    dark, light = _palette_zsh_vars(p), _palette_zsh_vars(terminal(p))
    ind = lambda rows: ["  " + r if r else r for r in rows]
    return "\n".join(head + [
        "# terminalMode=light: claro en Windows Terminal, oscuro en VS Code",
        "if [[ $TERM_PROGRAM == vscode ]]; then",
        "  typeset -g CC_MODE=dark", *ind(dark),
        "else",
        "  typeset -g CC_MODE=light", *ind(light),
        "fi",
    ]) + "\n"


def _palette_zsh_vars(p: dict) -> list[str]:
    out: list[str] = []
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
    # ¿Cada pestaña de Windows Terminal entra sola en tmux? (claude-05-tmux.zsh)
    # Segundos a partir de los cuales un comando avisa al terminar (0 = nunca)
    out.append(f"typeset -g CC_BELL_SECS='{int(p.get('notify', {}).get('afterSeconds', 0))}'")
    out.append(f"typeset -g CC_TMUX_AUTO='{1 if p.get('tmux', {}).get('autostart') else 0}'")
    # La palabra cambiada de un diff (delta): el color de la línea —verde en las
    # altas, rojo en las bajas— al 15% sobre su fondo. Antes iba en el gris de la
    # selección en las dos, y una baja no se distinguía de una alta. Más del 15%
    # destaca más pero hunde la sintaxis de encima por debajo de 3:1 (medido).
    sf, ro = p["surfaces"], p["roles"]
    if "diffPlus" in sf and "diffMinus" in sf:
        out.append(f"typeset -g CC_HEX_DIFFPLUSEMPH='{mix(ro['green']['hex'], sf['diffPlus'], 0.15)}'")
        out.append(f"typeset -g CC_HEX_DIFFMINUSEMPH='{mix(ro['red']['hex'], sf['diffMinus'], 0.15)}'")
    out.append(f"typeset -g CC_BG_SEL='{sgr(p['surfaces']['selection'], 'bg')}'")
    out.append(f"typeset -g CC_BG_DARK='{sgr(p['surfaces']['bgAlt'], 'bg')}'")
    out.append("")
    return out


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
    w = p.get("windowsTerminal", {})       # solo lo define el bloque `light`
    s = p["surfaces"]
    return {
        "name": p["name"],
        "window": {"applicationTheme": w.get("applicationTheme", "dark")},
        "tab": {"background": w.get("tab", s["bgAlt"]),
                "unfocusedBackground": w.get("tabUnfocused", s["bg"]),
                "showCloseButton": w.get("showCloseButton", "always")},
        "tabRow": {"background": w.get("tabRow", s["bg"]),
                   "unfocusedBackground": w.get("tabRowUnfocused", "#050708")},
    }


def wt_defaults(p: dict) -> dict:
    return {
        "colorScheme": p["name"],
        "font": {"face": p["font"]["face"], "size": p["font"]["sizeTerminal"], "weight": "normal",
                 **({"cellHeight": p["font"]["cellHeight"]} if p["font"].get("cellHeight") else {}),
                 **({"features": p["font"]["features"]} if p["font"].get("features") else {})},
        "padding": "14, 10, 14, 10",
        "cursorShape": "filledBox",
        "antialiasingMode": p["font"].get("antialiasing", "grayscale"),
        "scrollbarState": "hidden",
        "useAcrylic": False,
        "opacity": 100,
        "intenseTextStyle": p.get("windowsTerminal", {}).get("intenseTextStyle", "bright"),
        "historySize": 20000,
        # El timbre no suena nunca. Con `notify`, hace parpadear el icono de la
        # barra de tareas, que solo se ve si la ventana no tiene el foco.
        "bellStyle": "taskbar" if p.get("notify", {}).get("afterSeconds") else "none",
        "experimental.retroTerminalEffect": False,
        # Las marcas las manda la shell (OSC 133, en claude.zsh-theme); esto
        # hace que el terminal las tenga en cuenta. Estable desde la 1.21.
        "autoMarkPrompts": True,
    }


# Acciones propias de Windows Terminal, en su formato de la 1.24: la acción
# lleva un id y la tecla apunta al id. El prefijo es lo que permite quitarlas y
# volverlas a poner sin tocar las del usuario.
WT_ACTION_PREFIX = "User.claude."
WT_ACTIONS = [
    # (id, tecla, comando) — Ctrl+↑/↓ son las que sugiere la documentación y
    # zsh no las usa (medido: sin atadura en ningún keymap).
    ("prevPrompt", "ctrl+up", {"action": "scrollToMark", "direction": "previous"}),
    ("nextPrompt", "ctrl+down", {"action": "scrollToMark", "direction": "next"}),
    ("selectOutput", "ctrl+shift+o", {"action": "selectOutput", "direction": "prev"}),
    # El terminal desplegable: baja desde arriba de la pantalla y se esconde con
    # la misma tecla, estés donde estés. sc(41) es la tecla a la izquierda del 1
    # por POSICIÓN —º en un teclado español, ` en uno americano—: con el
    # carácter, la tecla cambiaría según la distribución.
    ("quake", "win+sc(41)", {"action": "quakeMode"}),
    # Sin franja superior: ni pestañas ni título, todo el alto para el texto.
    # La fila de pestañas mide 40 px y Windows Terminal no deja estrecharla;
    # esto la quita y la devuelve con la misma tecla.
    ("focus", "alt+f11", {"action": "toggleFocusMode"}),
]
WT_TAB_WIDTH = "titleLength"
# Perfiles que sobran en el menú de nueva pestaña. Azure por su origen y cmd por
# su guid, que es fijo en todas las máquinas; por nombre no, que va traducido.
WT_HIDE = {"sources": ("Windows.Terminal.Azure",),
           "guids": ("{0caa0dad-35be-5f56-a8ff-afceeeaa6101}",)}


def wt_actions() -> tuple[list[dict], list[dict]]:
    """(actions, keybindings) que añade el tema."""
    acts = [{"command": cmd, "id": WT_ACTION_PREFIX + i} for i, _, cmd in WT_ACTIONS]
    keys = [{"id": WT_ACTION_PREFIX + i, "keys": k} for i, k, _ in WT_ACTIONS]
    return acts, keys


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


def contrast(a: str, b: str) -> float:
    """Contraste WCAG entre dos hex."""
    def lum(h: str) -> float:
        def ch(c: int) -> float:
            c /= 255
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        r, g, b_ = rgb(h)
        return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b_)
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def mix(fg: str, bg: str, a: float) -> str:
    """`fg` al `a` sobre `bg`, en sRGB. Así se derivan los fondos de diff y los
    tintes: no se eligen a ojo."""
    f, b = rgb(fg), rgb(bg)
    return "#" + "".join(f"{round(y * (1 - a) + x * a):02X}" for x, y in zip(f, b))


# Qué color lleva cada cosa en el código, por rol de la paleta. Se buscó que
# se lea como el resto del tema —ámbar para los literales, como en la línea de
# comandos; morado para lo que es del lenguaje— y que lo que no es dato se
# aparte: comentarios en gris y en cursiva, operadores y puntuación en el
# color del texto apagado.
BAT_SCOPES = [
    ("Comentario", "comment, punctuation.definition.comment", "grey", "italic"),
    ("Cadena", "string, punctuation.definition.string, string.quoted", "amber", ""),
    ("Escape", "constant.character.escape, string.regexp", "orange", ""),
    ("Número y constante", "constant.numeric, constant.language, constant.other, support.constant", "orange", ""),
    ("Palabra clave", "keyword, storage, storage.type, storage.modifier, keyword.control", "purple", ""),
    ("Operador y puntuación", "keyword.operator, punctuation.separator, punctuation.terminator, "
     "punctuation.accessor, punctuation.section, meta.brace", "@fgDim", ""),
    ("Función", "entity.name.function, support.function, meta.function-call variable.function, "
     "variable.function", "blue", ""),
    ("Tipo y clase", "entity.name.type, entity.name.class, support.type, support.class, "
     "entity.other.inherited-class, storage.type.class", "teal", ""),
    ("self, this", "variable.language", "purple", "italic"),
    ("Parámetro", "variable.parameter", "@fg", "italic"),
    ("Clave de objeto", "support.type.property-name, meta.object-literal.key, "
     "meta.mapping.key string, entity.name.tag.yaml", "green", ""),
    ("Etiqueta", "entity.name.tag", "blue", ""),
    ("Atributo", "entity.other.attribute-name", "teal", ""),
    ("Decorador", "meta.decorator, entity.name.function.decorator, punctuation.definition.annotation",
     "orange", ""),
    ("Variable de shell", "variable.other.normal.shell, variable.other.special.shell, "
     "punctuation.definition.variable", "green", ""),
    ("Título", "markup.heading, entity.name.section", "teal", "bold"),
    ("Negrita", "markup.bold", "@fg", "bold"),
    ("Cursiva", "markup.italic", "@fg", "italic"),
    ("Código en línea", "markup.raw, markup.inline.raw", "green", ""),
    ("Enlace", "markup.underline.link, string.other.link", "blue", "underline"),
    ("Cita", "markup.quote", "grey", "italic"),
    ("Lista", "punctuation.definition.list, markup.list.numbered punctuation", "purple", ""),
    ("Alta", "markup.inserted", "green", ""),
    ("Baja", "markup.deleted", "red", ""),
    ("Cambio", "markup.changed", "amber", ""),
    ("Cabecera de diff", "meta.diff.header, meta.diff.range", "blue", ""),
    ("Inválido", "invalid", "red", "underline"),
]


def bat_theme(p: dict, name: str) -> str:
    """Un .tmTheme para bat (y delta, que usa los de bat) sacado de la paleta.

    El tema `ansi` que se usaba antes pinta con los 16 colores del terminal,
    pero con un reparto fijo que no es el de la paleta: los comentarios salían
    verdes, como los strings, y los operadores morados como las palabras clave.
    """
    import plistlib
    s, ro = p["surfaces"], p["roles"]

    def color(ref: str) -> str:
        c = s[ref[1:]] if ref.startswith("@") else ro[ref]["hex"]
        # El gris de los comentarios es el de las flechas y separadores, y en
        # oscuro da 4.32:1 sobre el fondo. Un comentario se lee: si no llega a
        # 4.5, el texto apagado de la paleta.
        if ref == "grey" and contrast(c, s["bg"]) < 4.5:
            c = s["fgDim"]
        return c

    rules = [{"settings": {
        "background": s["bg"], "foreground": s["fg"], "caret": s["fg"],
        "selection": s["selection"], "lineHighlight": s.get("bgPanel", s["bg"]),
        "gutterForeground": s["ghost"], "invisibles": s["ghost"],
    }}]
    for label, scope, ref, style in BAT_SCOPES:
        st = {"foreground": color(ref)}
        if style:
            st["fontStyle"] = style
        rules.append({"name": label, "scope": scope, "settings": st})
    return plistlib.dumps({"name": name, "settings": rules}).decode()


def claude_theme(p: dict) -> dict:
    """El tema de Claude Code para el terminal claro —custom:terminal-light—,
    GENERADO desde la paleta: los mismos roles que zsh y Windows Terminal, y los
    mismo fondo que el terminal y que la statusline. El mensaje del usuario va en
    la TARJETA, un escalón por encima de ese fondo, como en el tema oscuro va un
    escalón por encima del negro. Las claves y su orden son las del tema oscuro
    «Terminal» de claude-code-themes.

    Antes era un JSON escrito a mano con otra paleta que la del terminal, y eso
    es exactamente lo que hacía que cada cosa tuviera su blanco y sus colores."""
    t = terminal(dict(p, terminalMode="light"))
    s = t["surfaces"]
    r = {k: v["hex"] for k, v in t["roles"].items()}
    br = {k: v["bright"] for k, v in t["roles"].items()}
    acc = desktop(dict(p, windowsMode="light"))["windowsAccent"]
    canvas, base, line, card = s["bg"], s["bgAlt"], s["border"], s.get("card", s["bgAlt"])
    shim = lambda c: mix(c, "#FFFFFF", 0.25)       # el brillo de las animaciones
    pink, indigo = "#A04374", "#535FB5"            # OKLCH L 0.52 C 0.135, h 350 y 277
    o = {
        "claude": r["teal"], "claudeShimmer": shim(r["teal"]),
        "text": s["fg"], "inactive": s["fgDim"], "subtle": s["ghost"], "suggestion": r["grey"],
        "permission": r["purple"], "permissionShimmer": shim(r["purple"]),
        "remember": r["blue"], "success": r["green"], "error": r["red"], "warning": r["amber"],
        "merged": r["purple"],
        "promptBorder": acc["base"], "promptBorderShimmer": acc["ramp"][2],
        "planMode": r["blue"], "autoAccept": r["green"], "bashBorder": r["purple"],
        "diffAdded": s["diffPlus"], "diffRemoved": s["diffMinus"],
        "diffAddedWord": mix(r["green"], canvas, 0.32), "diffRemovedWord": mix(r["red"], canvas, 0.32),
        "userMessageBackground": card, "selectionBg": s["selection"],
        "rate_limit_fill": r["blue"], "rate_limit_empty": line,
        "briefLabelYou": s["fgDim"], "briefLabelClaude": r["teal"],
        "skill": r["purple"], "effortUltra": br["purple"],
        "ide": r["blue"], "professionalBlue": r["blue"], "chromeYellow": r["amber"],
        "warningShimmer": shim(r["amber"]), "fastMode": r["orange"], "fastModeShimmer": shim(r["orange"]),
        "claudeBlue_FOR_SYSTEM_SPINNER": r["teal"], "claudeBlueShimmer_FOR_SYSTEM_SPINNER": shim(r["teal"]),
        "clawd_body": r["teal"], "clawd_background": canvas,
        "background": r["teal"], "inverseText": "#FFFFFF",   # tinta sobre el teal, no un fondo
        "inactiveShimmer": s["ghost"], "autoAcceptShimmer": shim(r["green"]),
        "diffAddedDimmed": mix(r["green"], canvas, 0.08), "diffRemovedDimmed": mix(r["red"], canvas, 0.08),
        "userMessageBackgroundHover": mix("#000000", card, 0.05),
        "composerSidebarBackground": base,
        "bashMessageBackgroundColor": mix(r["purple"], canvas, 0.06),
        "memoryBackgroundColor": mix(r["blue"], canvas, 0.06),
    }
    sub = {"red": "red", "orange": "orange", "yellow": "amber", "green": "green",
           "cyan": "teal", "blue": "blue", "purple": "purple"}
    for name, role in sub.items():
        o[f"{name}_FOR_SUBAGENTS_ONLY"] = r[role]
    o["pink_FOR_SUBAGENTS_ONLY"] = pink
    rainbow = {"red": r["red"], "orange": r["orange"], "yellow": r["amber"], "green": r["green"],
               "blue": r["blue"], "indigo": indigo, "violet": r["purple"]}
    for name, c in rainbow.items():
        o[f"rainbow_{name}"] = c
    for name, c in rainbow.items():
        o[f"rainbow_{name}_shimmer"] = shim(c)
    return {"name": "Terminal Light", "base": "light",
            "overrides": {k: v.lower() for k, v in o.items()}}


def registry_values(p: dict) -> list[tuple[str, str, str, str]]:
    """(clave, nombre, tipo, dato) — lo que escribe el instalador."""
    w = p["windowsAccent"]
    A = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Accent"
    D = r"HKCU\Software\Microsoft\Windows\DWM"
    al = w["colorizationAlpha"]
    out = [
        (A, "AccentPalette",         "REG_BINARY", accent_palette_blob(w["ramp"])),
        (A, "AccentColorMenu",       "REG_DWORD",  abgr(w["base"])),
        (A, "StartColorMenu",        "REG_DWORD",  abgr(w["start"])),
        (D, "AccentColor",           "REG_DWORD",  abgr(w["base"])),
        (D, "AccentColorInactive",   "REG_DWORD",  abgr(w.get("inactiveBorder", w["start"]))),
        (D, "ColorizationColor",     "REG_DWORD",  argb(w["base"], al)),
        (D, "ColorizationAfterglow", "REG_DWORD",  argb(w["base"], al)),
    ]
    # El modo de apps va a juego con el de los mods. Si no, pasa lo que pasó:
    # Windows en claro desde Configuración y la barra, el Inicio y medio
    # Explorador en negro, porque los mods llevan los colores escritos. Sin
    # `windowsMode` en la paleta no se toca, como antes de existir la clave.
    if "windowsMode" in p:
        P = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        light = "0x1" if p["windowsMode"] == "light" else "0x0"
        out += [(P, "AppsUseLightTheme",    "REG_DWORD", light),
                (P, "SystemUsesLightTheme", "REG_DWORD", light)]
    return out


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
        f"typeset -g CC_KEYS_MAXLINES='{int(sh.get('maxLines', 3))}'",
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
            # El color del rol NO se escribe en hex: apunta a la variable de la
            # paleta, que claude-00 ya eligió según el terminal (claro en
            # Windows Terminal, oscuro en VS Code). Con el hex escrito, la
            # insignia NORMAL salía en el morado pastel del oscuro sobre el
            # fondo claro, a 2.6:1. El hex oscuro queda de respaldo.
            role = m["role"]
            out.append(f'typeset -g {var}_ROLE="${{CC_HEX_{role.upper()}:-{p["roles"][role]["hex"]}}}"')
            pairs = " ".join(_zq(c) for h in mode_hints(p, surface, mode) for c in h)
            out.append(f"typeset -ga {var}=({pairs})")
        names = " ".join(f"'{m}'" for m in k[surface]["modes"])
        out.append(f"typeset -ga CC_KEYS_{surface.upper()}_MODES=({names})")
        out.append("")
    return "\n".join(out) + "\n"


def _ahk_str(s: str) -> str:
    """Literal de AutoHotkey v2: solo las comillas dobles se escapan, duplicándolas."""
    return '"' + s.replace('"', '""') + '"'


def ahk_send(hotkey: str) -> str:
    """«Ctrl + Space» (como lo guarda Flow) → «^{Space}» (como lo manda AutoHotkey)."""
    mods = {"ctrl": "^", "alt": "!", "shift": "+", "win": "#"}
    parts = [t.strip() for t in hotkey.split("+") if t.strip()]
    pre = "".join(mods[t.lower()] for t in parts[:-1])
    key = parts[-1]
    return pre + (key.lower() if len(key) == 1 else "{" + key + "}")


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
        # cpu · ram · rama a la izquierda de la barra (ver la plantilla)
        "STATS_ON":      "1" if p["windowsDesktop"]["taskbar"].get("stats", {}).get("show") else "0",
        "STATS_X":       str(int(p["windowsDesktop"]["taskbar"].get("stats", {}).get("x", 52))),
        "STATS_URL":     f"http://127.0.0.1:{int(p['windowsDesktop'].get('gitBranch', {}).get('port', 8756))}/",
        "STATS_BG":      bare(s["bgAlt"]),
        "STATS_FG":      bare(s["fg"]),
        "STATS_DIM":     bare(ro["grey"]["hex"]),
        "STATS_SIZE":    str(int(p["windowsDesktop"]["taskbar"].get("stats", {}).get("fontSize", 9))),
        "START_FLOW":    "1" if p["windowsDesktop"]["launcher"].get("startOpensFlow") else "0",
        "FLOW_KEYS":     _ahk_str(ahk_send(p["windowsDesktop"]["launcher"].get("hotkey", "Ctrl + Space"))),
    }


def tmux_conf(p: dict) -> str:
    """tmux con la paleta. Solo aspecto, y tres ajustes sin los cuales el resto
    del tema no llega a través de tmux: color de 24 bits, la forma del cursor y
    un Esc que no tarde medio segundo.

    Lo que NO toca, a propósito: el prefijo, las teclas y la numeración de
    ventanas y paneles. Hay scripts que abren paneles y los nombran por índice;
    un `base-index 1` aquí los rompería sin decir nada.

    Con `tmux.autostart` en la paleta, tmux pasa a ser donde se vive, y entonces
    sí van dos cosas de comportamiento: el ratón —sin él la rueda no mueve el
    historial, manda flechas a la shell— y un historial tan largo como el que
    tenía Windows Terminal (20.000 líneas; tmux trae 2.000).

    La barra va en el mismo tono que el terminal —un solo fondo— y la ventana
    activa se marca por color y negrita, no por una pastilla.
    """
    s, ro = p["surfaces"], p["roles"]
    teal, amber = ro["teal"]["hex"], ro["amber"]["hex"]
    return "\n".join([
        "# Generado por lib/render.py desde palette.json. No editar a mano:",
        "# lo tuyo va en ~/.config/tmux/local.conf, que se carga al final.",
        "",
        "# ── lo que hace falta para que el tema pase a través de tmux ──",
        'set -g default-terminal "tmux-256color"',
        "# color de 24 bits: sin esto tmux redondea la paleta a 256",
        'set -as terminal-features ",xterm-256color:RGB"',
        "# la forma del cursor (DECSCUSR): el terminfo de xterm-256color no trae",
        "# Ss/Se y tmux se comería la barra de INSERT y el bloque de NORMAL",
        "set -as terminal-overrides ',xterm*:Ss=\\E[%p1%d q:Se=\\E[2 q'",
        "# Claude Code baja a 256 colores en cuanto ve $TMUX, salvo que se le diga",
        "# que este tmux sí pasa los 24 bits (arriba). Sin esto la banda de la",
        "# statusline sale en #EEEEEE —el gris 255 de la paleta de 256— sobre el",
        "# #F3F3F3 del terminal, y los roles en sus vecinos más cercanos.",
        "set-environment -g CLAUDE_CODE_TMUX_TRUECOLOR 1",
        "# Esc: por defecto tmux espera 500 ms por si es una secuencia, y el modo",
        "# vim de la shell se nota pegajoso",
        "set -sg escape-time 10",
        "set -g focus-events on",
        "# el título de la pestaña: tmux no lo pasa si no se le pide. El del programa",
        "# si puso uno (Claude Code pone el de la sesión); si no, el nombre de la",
        "# ventana, que la shell mantiene con la carpeta o el comando en marcha.",
        "set -g set-titles on",
        "set -g set-titles-string '#{?#{==:#{pane_title},#{host}},#W,#T}'",
        *([
            "",
            "# ── tmux arranca solo en cada pestaña (tmux.autostart) ──",
            "# la rueda mueve el historial; para seleccionar como en Windows",
            "# Terminal, Mayús+arrastrar",
            "set -g mouse on",
            "set -g history-limit 20000",
            "# con una sola ventana la barra no dice nada («0 zsh»): se esconde, y",
            "# la pestaña se ve como un terminal a secas. Vuelve sola con la segunda.",
            *[f"set-hook -g {ev} 'if -F \"#{{==:#{{session_windows}},1}}\" \"set status off\" \"set status on\"'"
              for ev in ("session-created", "window-linked", "window-unlinked")],
        ] if p.get("tmux", {}).get("autostart") else []),
        *([
            "",
            "# ── teclas (tmux.keys) ──",
            "# el modo copia, con las teclas de vim: era lo único del terminal que",
            "# seguía en emacs. v selecciona, y copia y sale.",
            "setw -g mode-keys vi",
            "bind -T copy-mode-vi v send -X begin-selection",
            "bind -T copy-mode-vi y send -X copy-selection-and-cancel",
            "# dividir y abrir ventana en la carpeta del panel, no en la de inicio de",
            "# la sesión. Las mismas teclas de serie: solo cambia dónde abren.",
            "bind '\"' split-window -v -c '#{pane_current_path}'",
            "bind % split-window -h -c '#{pane_current_path}'",
            "bind c new-window -c '#{pane_current_path}'",
        ] if p.get("tmux", {}).get("keys") else []),
        "",
        "# ── la barra ──",
        f'set -g status-style "bg={s["bg"]},fg={s["fgDim"]}"',
        "set -g status-left-length 40",
        "# el nombre de la sesión solo si dice algo: las de cada pestaña se llaman",
        "# wt-<pid> y enseñarlo es ruido; una con nombre propio (orq-…) sí sale",
        f'set -g status-left "#{{?#{{m:wt-*,#S}}, ,#[fg={teal}#,bold] #S #[fg={s["border"]}#,nobold]│ }}"',
        f'set -g status-right "#{{?client_prefix,#[fg={amber}#,bold]PREFIJO ,}}"',
        f'setw -g window-status-format "#[fg={s["fgDim"]}]#I #W "',
        f'setw -g window-status-current-format "#[fg={teal},bold]#I #W "',
        'setw -g window-status-separator ""',
        f'setw -g window-status-activity-style "fg={amber}"',
        f'setw -g window-status-bell-style "fg={ro["red"]["hex"]},bold"',
        "",
        "# ── paneles, mensajes y selección ──",
        f'set -g pane-border-style "fg={s["border"]}"',
        f'set -g pane-active-border-style "fg={teal}"',
        f'set -g message-style "bg={s["selection"]},fg={s["fg"]}"',
        f'set -g message-command-style "bg={s["selection"]},fg={s["fg"]}"',
        f'setw -g mode-style "bg={s["selection"]},fg={s["fg"]}"',
        f'set -g display-panes-colour "{s["fgDim"]}"',
        f'set -g display-panes-active-colour "{teal}"',
        f'setw -g clock-mode-colour "{teal}"',
        "",
        "if-shell '[ -f ~/.config/tmux/local.conf ]' 'source-file ~/.config/tmux/local.conf'",
        "",
    ])


# ── las herramientas de pantalla completa ─────────────────────────────
# btop, lazygit y vim traen su propio reparto de colores y no miran el del
# terminal: sin esto, btop pinta su fondo oscuro de serie sobre el terminal claro.
# Los tres dejan el FONDO sin pintar —el del terminal— para que siga habiendo un
# solo tono, y solo ponen tinta.

def btop_theme(p: dict) -> str:
    """Tema de btop. Las claves son las de los temas que trae (adwaita.theme).
    Los degradados van de teal a ámbar a rojo: reposo, carga, alarma."""
    s, ro = p["surfaces"], p["roles"]
    teal, amber, red, blue, green = (ro[k]["hex"] for k in ("teal", "amber", "red", "blue", "green"))
    rows = [
        ("main_bg", ""),                 # vacío = el fondo del terminal
        ("main_fg", s["fg"]), ("title", s["fg"]), ("hi_fg", teal),
        ("selected_bg", s["selection"]), ("selected_fg", s["fg"]),
        ("inactive_fg", s["ghost"]), ("graph_text", s["fgDim"]), ("meter_bg", s["border"]),
        ("proc_misc", teal),
        ("cpu_box", s["border"]), ("mem_box", s["border"]), ("net_box", s["border"]),
        ("proc_box", s["border"]), ("div_line", s["border"]),
    ]
    for name, (a, b, c) in {
        "temp": (teal, amber, red), "cpu": (teal, amber, red),
        "free": (green, green, green), "cached": (blue, blue, blue),
        "available": (teal, teal, teal), "used": (teal, amber, red),
        "download": (blue, blue, blue), "upload": (ro["purple"]["hex"],) * 3,
        "process": (teal, amber, red),
    }.items():
        rows += [(f"{name}_start", a), (f"{name}_mid", b), (f"{name}_end", c)]
    return ("# Generado por lib/render.py desde palette.json. No editar a mano.\n"
            + "".join(f'theme[{k}]="{v}"\n' for k, v in rows))


LAZYGIT_MARK = "# Generado por lib/render.py desde palette.json."


def lazygit_config(p: dict) -> str:
    """Solo `gui`: colores e iconos. Las claves salen de `lazygit --config`."""
    s, ro = p["surfaces"], p["roles"]
    q = lambda c: f"'{c}'"
    return "\n".join([
        LAZYGIT_MARK + " Lo tuyo, debajo de `gui:` no: en otro fichero",
        "# y con LG_CONFIG_FILE, o quita esta primera línea y el instalador no lo vuelve a tocar.",
        "gui:",
        f"  nerdFontsVersion: {q('3') if p['font'].get('nerdGlyphs') else q('')}",
        "  border: rounded",
        "  theme:",
        f"    activeBorderColor: [{q(ro['teal']['hex'])}, bold]",
        # ghost y no border: los títulos de panel van en este color, y en el
        # gris de las líneas (#E5E5E5 sobre #F3F3F3) no se leían
        f"    inactiveBorderColor: [{q(s['ghost'])}]",
        f"    searchingActiveBorderColor: [{q(ro['amber']['hex'])}, bold]",
        f"    optionsTextColor: [{q(ro['blue']['hex'])}]",
        f"    selectedLineBgColor: [{q(s['selection'])}]",
        f"    inactiveViewSelectedLineBgColor: [{q(s['border'])}]",
        f"    cherryPickedCommitFgColor: [{q(s['fg'])}]",
        f"    cherryPickedCommitBgColor: [{q(s['selection'])}]",
        f"    markedBaseCommitFgColor: [{q(s['fg'])}]",
        f"    markedBaseCommitBgColor: [{q(s['diffPlus'] if 'diffPlus' in s else s['selection'])}]",
        f"    unstagedChangesColor: [{q(ro['red']['hex'])}]",
        f"    defaultFgColor: [{q(s['fg'])}]",
        "",
    ])


def vim_colors(p: dict, name: str) -> str:
    """Esquema de vim con el mismo reparto que el tema de bat (BAT_SCOPES):
    cadenas ámbar, palabras clave moradas, funciones azules, tipos teal."""
    s, ro = p["surfaces"], p["roles"]
    c = lambda k: ro[k]["hex"]
    hi = lambda g, fg="NONE", bg="NONE", attr="NONE": (
        f"hi {g} guifg={fg} guibg={bg} gui={attr} cterm={attr}")
    light = contrast(s["fg"], "#FFFFFF") > contrast(s["fg"], "#000000")
    return "\n".join([
        f'" {name}.vim — generado por lib/render.py desde palette.json. No editar a mano.',
        "hi clear", "if exists('syntax_on') | syntax reset | endif",
        f"let g:colors_name = '{name}'", f"set background={'light' if light else 'dark'}",
        hi("Normal", s["fg"]),                       # sin fondo: el del terminal
        hi("Comment", c("grey"), attr="italic"),
        hi("String", c("amber")), hi("Character", c("amber")),
        hi("Constant", c("orange")), hi("Number", c("orange")), hi("Boolean", c("orange")),
        hi("Special", c("orange")), hi("SpecialChar", c("orange")),
        hi("Statement", c("purple")), hi("Keyword", c("purple")), hi("Conditional", c("purple")),
        hi("Repeat", c("purple")), hi("StorageClass", c("purple")), hi("PreProc", c("purple")),
        hi("Operator", s["fgDim"]), hi("Delimiter", s["fgDim"]),
        hi("Function", c("blue")), hi("Identifier", s["fg"]),
        hi("Type", c("teal")), hi("Structure", c("teal")), hi("Title", c("teal"), attr="bold"),
        hi("Underlined", c("blue"), attr="underline"),
        hi("Todo", c("amber"), attr="bold"), hi("Error", c("red"), attr="underline"),
        hi("ErrorMsg", c("red")), hi("WarningMsg", c("amber")), hi("MoreMsg", c("teal")),
        hi("Question", c("teal")), hi("Directory", c("teal")),
        hi("LineNr", s["ghost"]), hi("CursorLineNr", c("teal"), attr="bold"),
        hi("CursorLine", bg=s.get("card", s["bgAlt"])), hi("ColorColumn", bg=s["border"]),
        hi("SignColumn"), hi("FoldColumn", s["ghost"]), hi("Folded", s["fgDim"], s["border"]),
        hi("NonText", s["ghost"]), hi("SpecialKey", s["ghost"]), hi("EndOfBuffer", s["border"]),
        hi("Visual", bg=s["selection"]), hi("Search", s["fg"], s["selection"]),
        hi("IncSearch", s["bg"], c("teal")), hi("MatchParen", c("teal"), attr="bold,underline"),
        hi("Pmenu", s["fg"], s["border"]), hi("PmenuSel", s["fg"], s["selection"]),
        hi("PmenuSbar", bg=s["border"]), hi("PmenuThumb", bg=s["ghost"]),
        hi("StatusLine", s["fg"], s["border"]), hi("StatusLineNC", s["fgDim"], s["border"]),
        hi("VertSplit", s["border"]), hi("TabLine", s["fgDim"], s["border"]),
        hi("TabLineSel", c("teal"), attr="bold"), hi("TabLineFill", bg=s["border"]),
        hi("DiffAdd", bg=s.get("diffPlus", s["selection"])),
        hi("DiffDelete", c("red"), s.get("diffMinus", s["selection"])),
        hi("DiffChange", bg=s["border"]), hi("DiffText", bg=s["selection"], attr="bold"),
        hi("SpellBad", attr="undercurl") + f" guisp={c('red')}",
        "",
    ])


VIMRC_MARK = '" Generado por claude-terminal-theme.'


def vimrc() -> str:
    """Un .vimrc mínimo, solo si no había ninguno: color y cursor. Nada de
    teclas ni de plugins; eso es de cada cual."""
    return "\n".join([
        VIMRC_MARK + " Quita esta línea y el instalador no lo vuelve a tocar.",
        "set nocompatible",
        "syntax on",
        "filetype plugin indent on",
        '" color de 24 bits, también dentro de tmux (que no anuncia t_8f/t_8b)',
        r'let &t_8f = "\<Esc>[38;2;%lu;%lu;%lum"',
        r'let &t_8b = "\<Esc>[48;2;%lu;%lu;%lum"',
        "set termguicolors",
        '" claro en Windows Terminal, oscuro en VS Code: como el resto del tema',
        "execute 'colorscheme claude-' . ($TERM_PROGRAM ==# 'vscode' ? 'dark' : 'light')",
        '" el cursor dice el modo, igual que en la shell: barra al insertar, bloque en normal',
        r'let &t_SI = "\<Esc>[6 q"',
        r'let &t_SR = "\<Esc>[4 q"',
        r'let &t_EI = "\<Esc>[2 q"',
        '" Esc sin espera: el mismo motivo que escape-time en tmux',
        "set ttimeout ttimeoutlen=10",
        "",
    ])


if __name__ == "__main__":
    pal = load()
    what = sys.argv[1] if len(sys.argv) > 1 else "palette.zsh"
    if what == "palette.zsh":
        sys.stdout.write(palette_zsh(pal))
    elif what == "scheme":
        json.dump(wt_scheme(terminal(pal)), sys.stdout, indent=2, ensure_ascii=False)
    elif what == "vscode":
        json.dump(vscode_colors(pal), sys.stdout, indent=2, ensure_ascii=False)
    elif what == "registry":
        for k, n, t, d in registry_values(desktop(pal)):
            print(f"{k}\t{n}\t{t}\t{d}")
    elif what == "keymap.zsh":
        sys.stdout.write(keymap_zsh(pal))
    elif what == "claude-theme":
        json.dump(claude_theme(pal), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    elif what in ("bat-theme-light", "bat-theme-dark"):
        mode = what.rsplit("-", 1)[1]
        # El claro sale del bloque `light` aunque terminalMode esté en dark: el
        # tema que se elige en cada terminal lo decide la shell (CC_MODE).
        tp = terminal(dict(pal, terminalMode="light")) if mode == "light" else pal
        sys.stdout.write(bat_theme(tp, f"claude-{mode}"))
    elif what == "btop.theme":
        sys.stdout.write(btop_theme(terminal(pal)))
    elif what == "lazygit.yml":
        sys.stdout.write(lazygit_config(terminal(pal)))
    elif what in ("vim-light", "vim-dark"):
        mode = what.rsplit("-", 1)[1]
        tp = terminal(dict(pal, terminalMode="light")) if mode == "light" else pal
        sys.stdout.write(vim_colors(tp, f"claude-{mode}"))
    elif what == "vimrc":
        sys.stdout.write(vimrc())
    elif what == "tmux.conf":
        sys.stdout.write(tmux_conf(terminal(pal)))
    elif what == "keys.ahk":
        for k, v in ahk_substitutions(desktop(pal)).items():
            print(f"{k}\t{v}")
    else:
        sys.exit(f"artefacto desconocido: {what}")
