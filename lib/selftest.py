#!/usr/bin/env python3
"""Comprueba los invariantes del tema. `./install.sh --self-test`.

Existe por una razón concreta: todo lo del shell se verificó a mano midiendo
píxeles y leyendo `bindkey` en una terminal, y eso no viaja al repo. Quien
cambie un zstyle, un flag de delta o el nombre de un widget no tenía forma de
saber si lo había roto.

El shell se interroga bajo un **pty de verdad**, no con `zsh -i -c`. La
diferencia importa: sin terminal de control, zsh no arranca ZLE y suelta
«can't change option: zle», que parece un fallo del tema y no lo es. Ese falso
positivo costó un rato la primera vez.

Reparto de trabajo: la sonda de zsh solo REPORTA hechos (clave=valor) y las
afirmaciones se hacen aquí. Así se leen todas juntas y en un solo idioma.
"""
from __future__ import annotations
import json, os, pathlib, pty, re, select, shutil, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import render  # noqa: E402

TEAL, GREEN, RED, GREY, AMBER = (
    "\033[38;2;77;214;193m", "\033[38;2;87;227;137m", "\033[38;2;242;119;122m",
    "\033[38;2;107;118;131m", "\033[38;2;232;196;106m")
OFF = "\033[0m"

# La zona de uso privado: donde las Nerd Fonts ponen sus glifos y donde una
# fuente normal no tiene nada que dibujar.
PUA = re.compile("[\ue000-\uf8ff]")

PROBE = r"""
# NADA de `emulate -L zsh` aquí. Se probó y falsea la medida: sin -R, emulate
# resetea las opciones de compatibilidad, y AUTO_CD es una de ellas — la sonda
# decía «off» mientras el shell real la tenía en «on». Un test que normaliza el
# entorno no puede medir el entorno.
print "histsize=$HISTSIZE"
print "savehist=$SAVEHIST"
for o in share_history hist_ignore_all_dups hist_ignore_space hist_verify \
         auto_cd auto_pushd auto_menu always_to_end complete_in_word; do
  print "opt_$o=${${(M)options[$o]:#on}:-off}"
done
print "wordchars=$WORDCHARS"
print "ls_colors_len=${#LS_COLORS}"
print "grep_colors=${GREP_COLORS:+set}"
for k in '^R:ctrl_r' '^T:ctrl_t' '\ec:alt_c' '^[[H:home' '^[[F:end' \
         '^[[3~:del' '^[[1;5C:ctrl_right' '^H:ctrl_bs'; do
  print "key_${k##*:}=${$(bindkey "${k%%:*}")##* }"
done
print "menusel_shifttab=${$(bindkey -M menuselect '^[[Z')##* }"
print "alias_ls=$(alias ls 2>/dev/null)"
print "bat_theme=$BAT_THEME"
print "fzf_cmd=$FZF_DEFAULT_COMMAND"
print "git_pager=${GIT_PAGER%% *}"
print "nerd_glyphs=$CC_NERD_GLYPHS"
print "eza_colors=${EZA_COLORS:+set}"
print "z_is=$(whence -w z 2>/dev/null)"
# ── modo vim y la tira de atajos ──
print "vi_main=$(bindkey -lL main)"
print "keytimeout=$KEYTIMEOUT"
print "keys_hotkey=$CC_KEYS_HOTKEY"
print "has_render=${+functions[_claude_keys_render]}"
print "has_command=${+functions[claude-keys]}"
print "prompt_has_bar=${${PROMPT}[(I)*_claude_keys_bar*]}"
print "pre_redraw=${widgets[zle-line-pre-redraw]}"
# COLUMNS fijo a 80: es el caso peor y el que hace falta para saber si el tope
# de filas se respeta. Sin fijarlo, la medida depende del ancho del pty.
COLUMNS=80
for _m in normal visual viopp insert; do
  _claude_keys_mode=$_m; CC_KEYS_ON=1; _claude_keys_render
  print "bar_${_m}_len=${#_claude_keys_bar}"
  print "bar_${_m}_lines=${#${(f)_claude_keys_bar}}"
done
CC_KEYS_ON=0; _claude_keys_mode=normal; _claude_keys_render
print "bar_off_len=${#_claude_keys_bar}"
# Cada tecla que el chuletario ANUNCIA, preguntada a zsh. Es lo que impide que
# palette.json y las ataduras deriven en silencio.
print "BINDINGS_BEGIN"
for _spec in "${CC_SELFTEST_TOKENS[@]}"; do
  _km=${_spec%%|*}; _rest=${_spec#*|}; _mode=${_rest%%|*}; _tok=${_rest#*|}
  case $_tok in
    "<ESC>")  _tok=$'\e' ;;
    "<ALTC>") _tok=$'\ec' ;;
  esac
  _out=$(bindkey -M $_km -- "$_tok" 2>&1)
  _first=$(bindkey -M $_km -- "${_tok[1]}" 2>&1)
  print -r -- "BIND|$_km|$_mode|$_tok|${_out##* }|${_first##* }"
done
print "BINDINGS_END"
# Sin tubería y en un directorio de juguete, a propósito. Con `ls | head` el
# --icons=auto se apaga solo por no haber terminal al otro lado, y entonces esta
# comprobación no puede fallar NUNCA: era un falso negativo. Se descubrió
# rompiendo el tema aposta y viendo que el test seguía en verde.
_cct=${TMPDIR:-/tmp}/claude-selftest-dir
rm -rf $_cct; mkdir -p $_cct/uncarpeta
: > $_cct/uno.py; : > $_cct/dos.json; : > $_cct/tres.tar.gz
print "LS_OUTPUT_BEGIN"
(cd $_cct && ls)
print "LS_OUTPUT_END"
# Control: con --icons=always TIENE que haber glifos. Si aquí tampoco sale
# ninguno, el detector está roto y la comprobación de arriba estaría pasando
# por vacuidad, no por estar bien.
print "LS_CONTROL_BEGIN"
(cd $_cct && ${commands[eza]:-true} --icons=always 2>/dev/null)
print "LS_CONTROL_END"
rm -rf $_cct
"""


# vicmd, viins, visual y viopp NO son cuatro mapas independientes: `visual` y
# `viopp` son capas finas encima de `vicmd`, y una tecla que no esté en ellas se
# resuelve allí. Por eso `w` en operador-pendiente sale «undefined-key» y aun
# así `dw` funciona: hay que preguntar también al mapa de abajo o el test
# suspende teclas que sí están.
KEYMAP_OF = {"normal": "vicmd", "insert": "viins", "visual": "visual", "viopp": "viopp"}
FALLBACK_OF = {"visual": "vicmd", "viopp": "vicmd"}


# Lo que el chuletario escribe para que lo lea un humano, traducido a lo que
# entiende `bindkey`. Sin esto, «Alt+c» se preguntaba tal cual —no existe— y
# pasaba por el respaldo del primer carácter, o sea sin comprobar nada.
TOK_ALIAS = {"Esc": "<ESC>", "Alt+c": "<ALTC>"}

# Las teclas donde el chuletario dice algo CONCRETO y donde equivocarse no da
# ningún error visible: la tecla responde, solo que hace otra cosa.
SEMANTICA = {
    ("vicmd", "u"): "undo",
    ("vicmd", "^r"): "redo",
    ("vicmd", "."): "vi-repeat-change",
    ("vicmd", "v"): "visual-mode",
    ("vicmd", "V"): "visual-line-mode",
    ("vicmd", "/"): "vi-history-search-backward",
    ("vicmd", "cs"): "change-surround",
    ("vicmd", "ds"): "delete-surround",
    ("vicmd", "ys"): "add-surround",
    ("vicmd", "^x^e"): "edit-command-line",
    ("viins", "<ESC>"): "vi-cmd-mode",
    ("viins", "jk"): "vi-cmd-mode",
    ("viins", "^a"): "beginning-of-line",
    ("viins", "^e"): "end-of-line",
    ("viins", "^w"): "backward-kill-word",
    ("viins", "^x^e"): "edit-command-line",
    ("viopp", "iw"): "select-in-word",
    ("viopp", 'i"'): "select-quoted",
    ("viopp", "i("): "select-bracketed",
    ("visual", "S"): "add-surround",
}


def announced_tokens(pal: dict) -> list[tuple[str, str, str]]:
    """(modo, keymap, tecla) por cada atajo que el chuletario enseña."""
    out = []
    for mode, m in pal["keys"]["shell"]["modes"].items():
        for keys, _desc in m["hints"]:
            for tok in keys.split():
                out.append((mode, KEYMAP_OF[mode], TOK_ALIAS.get(tok, tok)))
    return out


def tokens_prelude(pal: dict) -> str:
    """El array que consume la sonda. Se inyecta delante para que PROBE no
    tenga que saber nada de palette.json."""
    rows = []
    for mode, km, tok in announced_tokens(pal):
        rows.append("  '" + f"{km}|{mode}|{tok}".replace("'", "'\\''") + "'")
    return "typeset -a CC_SELFTEST_TOKENS=(\n" + "\n".join(rows) + "\n)\n"


def zsh_under_pty(script: str, timeout: int = 60) -> tuple[str, str]:
    """Lanza zsh interactivo con una terminal de control real.

    Devuelve (salida, error). El pty es lo que hace que ZLE arranque y que
    `bindkey` diga la verdad sobre los widgets de fzf.
    """
    if not shutil.which("zsh"):
        return "", "no hay zsh"
    tmp = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / "claude-selftest-probe.zsh"
    tmp.write_text(script, encoding="utf-8")
    master, slave = pty.openpty()
    try:
        proc = subprocess.Popen(["zsh", "-i", str(tmp)], stdin=slave,
                                stdout=slave, stderr=slave, close_fds=True)
    except Exception as e:                      # pragma: no cover
        os.close(master); os.close(slave); return "", str(e)
    os.close(slave)
    chunks: list[bytes] = []
    while True:
        try:
            ready, _, _ = select.select([master], [], [], timeout)
            if not ready:
                break
            data = os.read(master, 65536)
            if not data:
                break
            chunks.append(data)
        except OSError:
            break
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:           # pragma: no cover
        proc.kill()
    os.close(master)
    tmp.unlink(missing_ok=True)
    return b"".join(chunks).decode("utf-8", "replace"), ""


def clean_pty(out: str) -> str:
    """Bajo pty el prompt mete secuencias de escape y títulos de ventana (OSC)
    en medio de la salida. Esto las quita."""
    txt = re.sub(r"\x1b][0-9];[^\x07\x1b]*(\x07|\x1b\\)", "", out)
    return re.sub(r"\x1b\[[0-9;?]*[ -/]*[A-Za-z@]", "", txt).replace("\r", "")


def bind_rows(out: str) -> list[tuple[str, str, str, str, str]]:
    """(keymap, modo, tecla, widget de la secuencia, widget del primer carácter)."""
    rows = []
    for line in clean_pty(out).split("\n"):
        if not line.startswith("BIND|"):
            continue
        parts = line.rstrip().split("|")
        if len(parts) == 6:
            rows.append((parts[1], parts[2], parts[3], parts[4], parts[5]))
    return rows


def parse(out: str) -> tuple[dict[str, str], str]:
    """Saca los pares clave=valor y el bloque de `ls`."""
    clean = clean_pty(out)
    facts: dict[str, str] = {}
    for line in clean.split("\n"):
        m = re.match(r"^([a-z][a-z0-9_]*)=(.*)$", line)
        if m and m.group(1) not in facts:
            facts[m.group(1)] = m.group(2).strip()
    def between(a, b):
        return clean.split(a, 1)[1].split(b, 1)[0] if a in clean and b in clean else ""
    return facts, (between("LS_OUTPUT_BEGIN", "LS_OUTPUT_END"),
                   between("LS_CONTROL_BEGIN", "LS_CONTROL_END"))


class Report:
    def __init__(self) -> None:
        self.ok = self.bad = 0
        self.skipped = 0

    def section(self, name: str) -> None:
        print(f"{TEAL}·{OFF} {name}")

    def check(self, label: str, cond: bool, detail: str = "") -> None:
        if cond:
            self.ok += 1
            print(f"  {label:<38} {GREEN}ok{OFF}")
        else:
            self.bad += 1
            print(f"  {label:<38} {RED}FALLA{OFF}  {GREY}{detail}{OFF}")

    def skip(self, label: str, why: str) -> None:
        self.skipped += 1
        print(f"  {label:<38} {GREY}—  {why}{OFF}")


def check_shell(r: Report, pal: dict) -> str:
    r.section("shell (zsh bajo pty)")
    out, err = zsh_under_pty(tokens_prelude(pal) + PROBE)
    if err:
        r.check("la sonda arranca", False, err)
        return ""
    f, (ls_block, ls_control) = parse(out)
    if not f:
        r.check("la sonda arranca", False, "no devolvió ningún hecho")
        return ""

    r.check("historial de 100k dentro y fuera",
            f.get("histsize") == "100000" and f.get("savehist") == "100000",
            f"HISTSIZE={f.get('histsize')} SAVEHIST={f.get('savehist')}")
    r.check("historial compartido entre pestañas",
            f.get("opt_share_history") == "on", f.get("opt_share_history", "?"))
    r.check("historial sin duplicados",
            f.get("opt_hist_ignore_all_dups") == "on")
    for opt, label in (("auto_cd", "auto_cd"), ("auto_pushd", "auto_pushd"),
                       ("auto_menu", "auto_menu"), ("always_to_end", "always_to_end")):
        r.check(f"opción {label}", f.get(f"opt_{opt}") == "on")

    # La barra fuera de WORDCHARS es lo que hace que Ctrl+W borre UN tramo de
    # ruta en vez de la ruta entera. Es fácil de perder al tocar el fichero.
    r.check("WORDCHARS sin la barra (Ctrl+W por tramos)",
            "/" not in f.get("wordchars", "/"), f.get("wordchars", ""))

    r.check("LS_COLORS poblado", int(f.get("ls_colors_len") or 0) > 500,
            f"{f.get('ls_colors_len')} caracteres")
    r.check("GREP_COLORS puesto", f.get("grep_colors") == "set")

    for key, want, label in (
            ("key_home", "beginning-of-line", "Inicio"),
            ("key_end", "end-of-line", "Fin"),
            ("key_del", "delete-char", "Supr"),
            ("key_ctrl_right", "forward-word", "Ctrl+→"),
            ("key_ctrl_bs", "backward-kill-word", "Ctrl+Retroceso"),
            ("menusel_shifttab", "reverse-menu-complete", "Shift+Tab en el menú")):
        r.check(f"tecla {label}", f.get(key) == want, f"es «{f.get(key)}»")

    # ── lo que depende de que la herramienta esté ──
    if shutil.which("fzf"):
        for key, want, label in (("key_ctrl_r", "fzf-history-widget", "Ctrl+R"),
                                 ("key_ctrl_t", "fzf-file-widget", "Ctrl+T"),
                                 ("key_alt_c", "fzf-cd-widget", "Alt+C")):
            r.check(f"{label} lo coge fzf", f.get(key) == want, f"es «{f.get(key)}»")
    else:
        r.skip("atajos de fzf", "fzf no instalado")

    if shutil.which("bat") or shutil.which("batcat"):
        r.check("bat sigue los ANSI del terminal", f.get("bat_theme") == "ansi",
                f.get("bat_theme", ""))
    else:
        r.skip("tema de bat", "bat no instalado")

    if shutil.which("zoxide"):
        r.check("zoxide define «z»", f.get("z_is", "").startswith("z:"), f.get("z_is", ""))
    else:
        r.skip("zoxide", "no instalado")

    # ── los iconos: el fallo que motivó todo esto ──
    want_icons = "always" if pal["font"].get("nerdGlyphs") else "never"
    if shutil.which("eza"):
        r.check(f"eza con --icons={want_icons} (font.nerdGlyphs)",
                f"--icons={want_icons}" in f.get("alias_ls", ""), f.get("alias_ls", ""))
        r.check("EZA_COLORS con la paleta", f.get("eza_colors") == "set")
        # La prueba de verdad: si la fuente no tiene glifos, que no salga NINGUNO.
        pua = PUA.findall(ls_block)
        if pal["font"].get("nerdGlyphs"):
            r.skip("ls sin glifos ausentes", "nerdGlyphs=true, se esperan")
        else:
            # El control primero: si --icons=always tampoco produce glifos, esta
            # comprobación no vale nada y hay que decirlo, no cantar victoria.
            if not PUA.findall(ls_control):
                r.skip("ls sin glifos que la fuente no tiene",
                       "el control no produjo glifos; no se puede afirmar nada")
            else:
                r.check("ls sin glifos que la fuente no tiene",
                        not pua, f"{len(pua)} codepoints en la zona de uso privado")
    else:
        r.skip("iconos de eza", "eza no instalado")
    return out


def check_keys(r: Report, pal: dict, out: str) -> None:
    """El modo vim y —lo que de verdad importa— que el chuletario no mienta."""
    r.section("atajos (modo vim y chuletario)")
    f, _ = parse(out)
    if not f:
        r.check("la sonda devolvió hechos", False, "sin salida")
        return

    r.check("el keymap activo es vi",
            "viins" in f.get("vi_main", ""), f.get("vi_main", "?"))
    r.check(f"KEYTIMEOUT = {pal['keys']['shell']['keyTimeout']} (Esc responde)",
            f.get("keytimeout") == str(pal["keys"]["shell"]["keyTimeout"]),
            f.get("keytimeout", "?"))
    r.check("el PROMPT reserva sitio a la tira",
            f.get("prompt_has_bar", "0") != "0",
            "el tema no referencia _claude_keys_bar")
    r.check("`claude-keys` existe", f.get("has_command") == "1")
    r.check("la tira tiene quien la pinte", f.get("has_render") == "1")
    r.check("la shell conoce la tecla de Windows",
            f.get("keys_hotkey") == pal["keys"]["windows"]["hotkeyLabel"],
            f.get("keys_hotkey", "?"))

    # Encadenar y no PISAR: oh-my-zsh carga zsh-syntax-highlighting antes que
    # esta capa y los dos quieren el mismo gancho. `azhw` es el repartidor de
    # add-zle-hook-widget; si aquí sale otra cosa, alguien se ha comido al otro.
    r.check("los ganchos de ZLE se encadenan",
            "azhw" in f.get("pre_redraw", ""), f.get("pre_redraw", "?"))

    # La tira: llena en los modos de `showIn`, vacía en el resto y con el
    # interruptor apagado. Es la diferencia entre which-key y una línea fija.
    for mode in pal["keys"]["shell"]["showIn"]:
        r.check(f"la tira se pinta en {mode}",
                int(f.get(f"bar_{mode}_len") or 0) > 40,
                f"{f.get(f'bar_{mode}_len')} caracteres")
    off = [m for m in ("normal", "insert", "visual", "viopp")
           if m not in pal["keys"]["shell"]["showIn"]]
    for mode in off:
        r.check(f"la tira calla en {mode}",
                int(f.get(f"bar_{mode}_len") or 0) == 0,
                f"{f.get(f'bar_{mode}_len')} caracteres")
    r.check("con el interruptor en off no hay tira",
            int(f.get("bar_off_len") or 0) == 0, f.get("bar_off_len", "?"))

    # El tope de filas, medido a 80 columnas, que es donde duele. Sin él la
    # lista entera se comía seis filas del terminal cada vez que pulsabas Esc.
    tope = int(pal["keys"]["shell"].get("maxLines", 3))
    for mode in pal["keys"]["shell"]["showIn"]:
        n = int(f.get(f"bar_{mode}_lines") or 0)
        r.check(f"la tira de {mode} cabe en {tope} filas a 80 columnas",
                0 < n <= tope, f"{n} filas")

    # ── el chuletario contra bindkey ──
    rows = bind_rows(out)
    esperadas = len(announced_tokens(pal))
    r.check("la sonda devuelve las ataduras", len(rows) == esperadas,
            f"{len(rows)} de {esperadas} filas")
    if not rows:
        # Sin filas, la comprobación de abajo pasaría por vacuidad y cantaría
        # victoria sobre nada. Se dice que no se pudo medir, que es la verdad.
        r.skip("cada atajo anunciado está atado", "la sonda no devolvió ataduras")
        return
    huerfanas = []
    for km, mode, tok, seq, first in rows:
        # El respaldo «mira el primer carácter» sirve para ciw, dd o ci", donde
        # la primera tecla es el operador y el resto lo lee zsh después. Para un
        # ^r NO sirve: el primer carácter es el acento circunflejo, que en vicmd
        # es vi-first-non-blank, así que CUALQUIER atajo de control pasaba el
        # test por la puerta de atrás. Se descubrió metiendo un ^q inventado en
        # palette.json y viendo que el test seguía en verde.
        caret = len(tok) > 1 and tok.startswith("^")
        if seq != "undefined-key":
            continue
        # `self-insert` no es una atadura, es «esta tecla se escribe a sí
        # misma». En viins TODO carácter imprimible cae ahí, así que aceptarlo
        # como respaldo hacía que cualquier atajo inventado de INSERT pasara.
        if not caret and first not in ("undefined-key", "self-insert"):
            continue
        huerfanas.append(f"{mode}:{tok}")
    # Las capas `visual` y `viopp` resuelven en vicmd lo que no definen, así que
    # una tecla solo está huérfana de verdad si tampoco está ahí abajo.
    # Segunda vuelta solo para los modos que TIENEN mapa de abajo. Un huérfano de
    # `normal` ya se preguntó en vicmd la primera vez; volver a preguntarlo sería
    # la misma respuesta con otro nombre.
    conresp = [t for t in huerfanas if t.split(":", 1)[0] in FALLBACK_OF]
    if conresp:
        fb, _ = zsh_under_pty("\n".join(
            f'print -r -- "FB|{t}|${{$(bindkey -M {FALLBACK_OF[t.split(":", 1)[0]]} '
            f'-- {shlex_q(t.split(":", 1)[1])} 2>&1)##* }}"' for t in conresp))
        alive = {ln.split("|")[1] for ln in clean_pty(fb).split("\n")
                 if ln.startswith("FB|") and not ln.rstrip().endswith("undefined-key")}
        huerfanas = [t for t in huerfanas if t not in alive]
    r.check("cada atajo anunciado está atado", not huerfanas,
            "sin atar: " + ", ".join(huerfanas[:6]))

    # Estar atada no basta: hay que estarlo A LO QUE EL CHULETARIO DICE. Esto
    # existe porque `^r` en vicmd anunciaba «rehacer» y abría el buscador de
    # fzf —que lo ata él solo, en su propio key-bindings.zsh— y la comprobación
    # de arriba lo daba por bueno, porque atado sí estaba.
    mal = []
    for km, mode, tok, seq, _first in rows:
        want = SEMANTICA.get((km, tok))
        if want and seq != want:
            mal.append(f"{mode}:{tok} es «{seq}», no «{want}»")
    r.check("y atado a lo que el chuletario dice", not mal, "; ".join(mal[:3]))


def shlex_q(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def check_keys_windows(r: Report, pal: dict) -> None:
    """El lado Windows no se puede EJECUTAR desde aquí, pero sí leer.

    Es una comprobación de texto y lo es a sabiendas: no prueba que el atajo
    haga lo correcto, prueba que ninguna tecla del chuletario se quede sin
    código. Eso es justo la deriva que se cuela al añadir una línea a
    palette.json y olvidarse de la plantilla.
    """
    r.section("atajos de Windows (lectura estática)")
    root = pathlib.Path(__file__).resolve().parent.parent
    tmpl = root / "windows/claude-keys.ahk.tmpl"
    if not tmpl.exists():
        r.check("la plantilla existe", False, str(tmpl))
        return
    sys.path.insert(0, str(root / "lib"))
    import keys as keysmod                                   # noqa: E402

    try:
        src = keysmod.render_script(pal)
    except SystemExit as e:
        r.check("la plantilla se resuelve entera", False, str(e))
        return
    r.check("la plantilla se resuelve entera", "@@" not in src)
    r.check("declara AutoHotkey v2", "#Requires AutoHotkey v2.0" in src)

    w = pal["keys"]["windows"]
    # El $ delante no es adorno: sin él AutoHotkey no usa el hook de teclado y
    # el estado físico de las teclas deja de rastrearse, con lo que mantener
    # pulsado para recuperar el menú de ventana no funciona nunca.
    r.check(f"el modo se abre con {w['hotkeyLabel']} (con hook)",
            f"\n${w['hotkey']}::" in src, w["hotkey"])

    # Cada tecla anunciada tiene su `case` en la función del submapa. `Esc` lo
    # trata Act() para todos, y las cifras van por expresión regular.
    fn_of = {"normal": "ActNormal", "window": "ActWindow", "desktop": "ActDesktop"}
    bodies = {}
    for mode, fn in fn_of.items():
        m = re.search(rf"^{fn}\(key\) \{{(.*?)^\}}", src, re.S | re.M)
        bodies[mode] = m.group(1) if m else ""
    faltan = []
    for mode, m in w["modes"].items():
        for keyfield, _desc in m.get("hints", []):
            for tok in keyfield.split():
                if tok == "Esc":
                    continue
                if mode == "apps":
                    if f'APPS["{tok}"]' not in src:
                        faltan.append(f"{mode}:{tok}")
                    continue
                if tok == "1-9":
                    if "[1-9]" not in bodies[mode]:
                        faltan.append(f"{mode}:1-9")
                    continue
                if f'"{tok}"' not in bodies.get(mode, ""):
                    faltan.append(f"{mode}:{tok}")
    r.check("cada tecla del chuletario tiene código", not faltan,
            "sin código: " + ", ".join(faltan[:6]))

    # El cajón de sastre: sin él, una tecla suelta dentro del modo se escribe en
    # la aplicación de debajo.
    r.check("todas las letras y cifras se capturan en modo",
            'StrSplit("abcdefghijklmnopqrstuvwxyz0123456789")' in src)
    # WS_EX_NOACTIVATE. Si la banda robara el foco, «maximizar la ventana
    # activa» maximizaría la banda.
    r.check("la banda no roba el foco", "+E0x08000020" in src)

    # OnExit por debajo del primer atajo es código muerto: la sección de
    # autoejecución de AutoHotkey termina ahí. Costó una tarde de sondas.
    hot = src.find(f"\n${w['hotkey']}::")
    r.check("OnExit se registra (va antes del primer atajo)",
            0 < src.find("OnExit(") < hot, "está por debajo del primer atajo")

    # El Trim de AutoHotkey recorta espacios y tabuladores, NO saltos de línea,
    # y la shell escribe el fichero con `print`. Sin los caracteres explícitos la
    # banda no aparecía nunca y no daba ningún error.
    r.check("el interruptor se lee sin el salto de línea",
            'Trim(FileRead(HINTFILE), " `t`r`n")' in src)

    _ahk_loads(r, pal, src)


def _ahk_loads(r: Report, pal: dict, src: str) -> None:
    """Que AutoHotkey lo CARGUE, no solo que el texto tenga buena pinta.

    `/ErrorStdOut` es lo que hace esto posible desde aquí: sin él, un error de
    sintaxis abre un diálogo en el escritorio de Windows y desde WSL solo se ve
    un proceso que no responde. Con él, el error sale por la salida estándar.

    Se valida con `/validate` cuando existe y, si no, cargando el script de
    verdad con el modo apagado y matándolo enseguida.
    """
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import keys as keysmod                                   # noqa: E402

    if not pathlib.Path("/mnt/c").is_dir():
        r.skip("AutoHotkey carga el script", "esto no es WSL")
        return
    import apply_windows                                     # noqa: E402
    ahk = keysmod.find_ahk(apply_windows.win_userprofile())
    if not ahk:
        r.skip("AutoHotkey carga el script", "AutoHotkey v2 no instalado")
        return

    tmp = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / "claude-selftest-keys.ahk"
    with tmp.open("w", encoding="utf-8", newline="\r\n") as fh:
        # ExitApp al final de la autoejecución: carga, comprueba y se va sin
        # dejar un proceso ni robar Alt+Space durante el test.
        fh.write(src.replace("OnExit((*) => HideOSD())",
                             "OnExit((*) => HideOSD())\nExitApp()", 1))
    win = subprocess.run(["wslpath", "-w", str(tmp)],
                         capture_output=True, text=True).stdout.strip()
    try:
        # En BYTES, no en texto. AutoHotkey escribe sus errores en la página de
        # códigos del sistema, no en UTF-8, y con text=True el propio decodeo
        # revienta y tapa el error de verdad — que es justo lo que se quería ver.
        out = subprocess.run([str(ahk), "/ErrorStdOut", win], capture_output=True,
                             timeout=45, cwd="/mnt/c")
        msg = (out.stdout + out.stderr).decode("cp850", "replace").strip().replace("\r", "")
    except Exception as e:                                  # pragma: no cover
        msg = str(e)
    finally:
        tmp.unlink(missing_ok=True)
    r.check("AutoHotkey carga el script sin errores", not msg,
            msg.splitlines()[0][:70] if msg else "")


def check_delta(r: Report, pal: dict) -> None:
    if not shutil.which("delta"):
        r.skip("delta ve la paleta", "delta no instalado")
        return
    # Este comprueba el fallo que costó más de encontrar: delta lee el gitconfig
    # con libgit2, así que NO honra GIT_CONFIG_COUNT. Si alguien vuelve a esa vía
    # «más limpia», git config seguirá dando la razón y delta pintará con lo
    # suyo. Aquí se le pregunta a delta directamente.
    out, _ = zsh_under_pty('eval "${GIT_PAGER} --show-config" 2>/dev/null\n')
    clean = re.sub(r"\x1b][0-9];[^\x07\x1b]*(\x07|\x1b\\)", "", out)
    clean = re.sub(r"\x1b\[[0-9;]*m", "", clean)
    teal = pal["roles"]["teal"]["hex"].lower()
    plus = pal["surfaces"]["diffPlus"].lower()
    minus = pal["surfaces"]["diffMinus"].lower()
    low = clean.lower()
    r.check("delta pinta el fichero en teal", teal in low, "no aparece en --show-config")
    r.check("delta con los fondos de la paleta", plus in low and minus in low)
    r.check("delta distingue + de −", plus != minus)


def check_render(r: Report, pal: dict) -> None:
    r.section("render (palette.json → las superficies)")
    root = pathlib.Path(__file__).resolve().parent.parent
    for what, probe in (("palette.zsh", lambda s: "CC_HEX_TEAL" in s),
                        ("scheme",      lambda s: json.loads(s).get("cyan")),
                        ("vscode",      lambda s: json.loads(s).get("terminal.background")),
                        ("registry",    lambda s: "\t" in s),
                        ("keymap.zsh",  lambda s: "CC_KEYS_SHELL_NORMAL" in s),
                        ("keys.ahk",    lambda s: "MODES[" in s)):
        try:
            out = subprocess.run([sys.executable, str(root / "lib/render.py"), what],
                                 capture_output=True, text=True, timeout=30)
            r.check(f"genera {what}", out.returncode == 0 and bool(probe(out.stdout)),
                    (out.stderr or "").strip()[:60])
        except Exception as e:
            r.check(f"genera {what}", False, str(e)[:60])

    # palette.json es la única fuente de verdad: si esto se rompe, el resto miente.
    teal = pal["roles"]["teal"]["hex"]
    r.check("ansi.cyan == roles.teal (bat y delta dependen)",
            pal["ansi"]["cyan"].lower() == teal.lower(),
            f"{pal['ansi']['cyan']} vs {teal}")
    r.check("font.nerdGlyphs declarado", "nerdGlyphs" in pal["font"])


def main() -> int:
    pal = render.load()
    print(f"{TEAL}auto-test{OFF} {GREY}paleta «{pal['name']}»{OFF}\n")
    r = Report()
    probe = check_shell(r, pal)
    check_delta(r, pal)
    print()
    check_keys(r, pal, probe)
    print()
    check_keys_windows(r, pal)
    print()
    check_render(r, pal)
    print()
    total = r.ok + r.bad
    color = GREEN if r.bad == 0 else RED
    extra = f", {r.skipped} saltados" if r.skipped else ""
    print(f"{color}{r.ok}/{total} ok{OFF}{GREY}{extra}{OFF}")
    return 1 if r.bad else 0


if __name__ == "__main__":
    sys.exit(main())
