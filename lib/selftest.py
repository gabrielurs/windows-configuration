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
#
# Lo que SÍ se apaga, y solo para esta shell: el listado al entrar en un
# directorio —ensuciaría el bloque de `ls` de abajo; se mide aparte—, el apunte
# de zoxide —metería los directorios de juguete en tu historial de saltos— y el
# fichero que lee la barra de Windows, que enseñaría la rama del repo de prueba.
CC_CD_LS_LINES=0
chpwd_functions=(${chpwd_functions:#__zoxide_hook})
_claude_repo_file=${TMPDIR:-/tmp}/claude-selftest-repo
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
print "cdpath=$cdpath"
print "named_p=${nameddirs[p]}"
print "ftb_loaded=${+functions[fzf-tab-complete]}"
print "tab_viins=${$(bindkey -M viins '^I')##* }"
zstyle -s ':completion:*' menu _ccv; print "compl_menu=$_ccv"
print "chpwd_ls=${chpwd_functions[(Ie)_claude_cd_ls]}"
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
# ── Alt+↑ ← →: la lógica, sin ZLE ──
# Los widgets no se pueden disparar desde un script, pero lo que hacen vive en
# `_claude_nav`, que es una función normal. Ida, vuelta, adelante, y que un cd
# cualquiera olvide el adelante.
_ccn=${TMPDIR:-/tmp}/claude-selftest-nav
rm -rf $_ccn; mkdir -p $_ccn/a/b
cd $_ccn/a/b
_claude_nav up;      print "nav_up=${PWD#$_ccn}"
_claude_nav back;    print "nav_back=${PWD#$_ccn}"
_claude_nav forward; print "nav_forward=${PWD#$_ccn}"
_claude_nav back; cd $_ccn/a
_claude_nav forward; print "nav_forgot=$?"
# ── la ruta del prompt dentro de un repo ──
if (( $+commands[git] )); then
  mkdir -p $_ccn/mi-repo/uno/dos/tres/cuatro
  command git -C $_ccn/mi-repo init -q 2>/dev/null
  cd $_ccn/mi-repo/uno;               _claude_repo_track; print "cwd_repo=$_claude_cwd"
  cd $_ccn/mi-repo/uno/dos/tres/cuatro; _claude_repo_track; print "cwd_deep=$_claude_cwd"
  cd $_ccn;                           _claude_repo_track; print "cwd_plain=$_claude_cwd"
fi
# ── el listado al entrar, con su tope ──
mkdir -p $_ccn/lsdir; : > $_ccn/lsdir/f{01..30}
COLUMNS=20 CC_CD_LS_LINES=5
print "CDLS_BEGIN"
cd $_ccn/lsdir
print "CDLS_END"
CC_CD_LS_LINES=0; COLUMNS=80
cd /; rm -rf $_ccn
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
#
# Las flechas con Alt van en la notación de `bindkey` y no con un marcador: la
# entiende tal cual, y al empezar por ^ el test ya no las deja pasar por el
# respaldo del primer carácter.
TOK_ALIAS = {"Esc": "<ESC>", "Alt+c": "<ALTC>", "Tab": "^I",
             "Alt+↑": "^[[1;3A", "Alt+←": "^[[1;3D", "Alt+→": "^[[1;3C"}

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
    ("viins", "^[[1;3A"): "_claude_cd_up",
    ("viins", "^[[1;3D"): "_claude_cd_back",
    ("viins", "^[[1;3C"): "_claude_cd_forward",
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
    # [0-9]+ y no [0-9]: el título es OSC 0/2/7, pero las marcas de Windows
    # Terminal son OSC 133 y 9;9. Con un solo dígito se colaban en la salida y la
    # sonda leía «]133;C» como parte de los datos: 32 fallos que no eran de la shell.
    txt = re.sub(r"\x1b][0-9]+;[^\x07\x1b]*(\x07|\x1b\\)", "", out)
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
        # El tema propio del modo de la shell; ansi solo si no está instalado.
        bat = shutil.which("bat") or shutil.which("batcat")
        mode = ("light" if pal.get("terminalMode") == "light"
                and os.environ.get("TERM_PROGRAM") != "vscode" else "dark")
        cfg = subprocess.run([bat, "--config-dir"], capture_output=True, text=True).stdout.strip()
        want = f"claude-{mode}" if pathlib.Path(cfg, "themes", f"claude-{mode}.tmTheme").exists() else "ansi"
        r.check(f"bat usa el tema del modo ({want})", f.get("bat_theme") == want,
                f.get("bat_theme", ""))
    else:
        r.skip("tema de bat", "bat no instalado")

    if shutil.which("zoxide"):
        r.check("zoxide define «z»", f.get("z_is", "").startswith("z:"), f.get("z_is", ""))
    else:
        r.skip("zoxide", "no instalado")

    check_navigation(r, f, out)

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


def check_navigation(r: Report, f: dict[str, str], out: str) -> None:
    """cdpath, Alt+flechas, fzf-tab, la ruta del prompt y el listado al entrar."""
    home = pathlib.Path.home()
    proj = next((d for d in ("projects", "proyectos", "src", "code")
                 if (home / d).is_dir()), None)
    if proj:
        r.check(f"cdpath y ~p apuntan a ~/{proj}",
                f.get("cdpath") == str(home / proj) and f.get("named_p") == str(home / proj),
                f"cdpath={f.get('cdpath')} ~p={f.get('named_p')}")
    else:
        r.skip("cdpath y ~p", "no hay carpeta de proyectos")

    r.check("Alt+↑ sube", f.get("nav_up") == "/a", f.get("nav_up", "?"))
    r.check("Alt+← vuelve", f.get("nav_back") == "/a/b", f.get("nav_back", "?"))
    r.check("Alt+→ deshace el volver", f.get("nav_forward") == "/a", f.get("nav_forward", "?"))
    # rc 1: no había adónde ir. Si fuera 0, un cd normal no habría borrado el
    # adelante y Alt+→ te llevaría a un sitio que ya no tiene sentido.
    r.check("un cd normal olvida el adelante", f.get("nav_forgot") == "1",
            f"rc={f.get('nav_forgot')}")

    custom = pathlib.Path(os.environ.get("ZSH_CUSTOM")
                          or pathlib.Path(os.environ.get("ZSH") or home / ".oh-my-zsh") / "custom")
    if (custom / "plugins/fzf-tab").is_dir():
        r.check("fzf-tab cargado", f.get("ftb_loaded") == "1",
                "el plugin está pero no se carga: ¿falta en plugins=( ) del .zshrc?")
        r.check("Tab lo coge fzf-tab (viins)", f.get("tab_viins") == "fzf-tab-complete",
                f"es «{f.get('tab_viins')}»")
        # Con `menu select` zsh abre su menú antes y fzf-tab no ve el prefijo.
        r.check("el menú de zsh no se adelanta", f.get("compl_menu") == "no",
                f"menu={f.get('compl_menu')}")
    else:
        r.skip("fzf-tab", "no instalado")

    if shutil.which("git"):
        # %B…%b es el nombre del repo en negrita; el … aparece a partir de 4 tramos.
        r.check("prompt: ruta relativa al repo",
                f.get("cwd_repo") == "%Bmi-repo%b/uno", f.get("cwd_repo", "?"))
        deep = f.get("cwd_deep", "")
        r.check("prompt: tramos de más resumidos",
                deep.startswith("%Bmi-repo%b/") and "…" in deep and deep.endswith("tres/cuatro"),
                deep)
        r.check("prompt: fuera de un repo, como siempre",
                "%~" in f.get("cwd_plain", ""), f.get("cwd_plain", "?"))
    else:
        r.skip("ruta relativa al repo", "git no instalado")

    if shutil.which("eza"):
        clean = clean_pty(out)
        block = clean.split("CDLS_BEGIN", 1)[-1].split("CDLS_END", 1)[0] if "CDLS_BEGIN" in clean else ""
        r.check("al entrar se lista el directorio", f.get("chpwd_ls", "0") != "0" and "f01" in block,
                "no salió nada" if "f01" not in block else "el gancho no está en chpwd")
        # Sin contar columnas: eza reparte en rejilla y cuántas caben depende de
        # su versión. Lo que importa es que haya resumen, que f30 —la última— no
        # salga y que no pase del tope. Lo primero que se escribió aquí esperaba
        # una columna y falló con el listado bien cortado.
        filas = [ln for ln in block.strip().split("\n") if ln.strip()]
        r.check("y con tope de filas",
                re.search(r"… \d+ filas más", block) is not None and "f30" not in block
                and len(filas) <= 5 + 1,
                f"{len(filas)} filas: " + " | ".join(filas)[:60])
    else:
        r.skip("listado al entrar", "eza no instalado")


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

    # Dos invariantes que solo se ven USANDO la shell, no leyéndola, y que por
    # eso son fáciles de perder al reordenar la capa. Se comprueban sobre el
    # fuente porque el efecto —lo que queda en el scrollback— no se puede medir
    # desde una sonda que no es un widget de ZLE.
    capa = (pathlib.Path(__file__).resolve().parent.parent
            / "shell/claude-40-keys.zsh").read_text(encoding="utf-8")
    ini = capa.split("_claude_keys_line_init() {", 1)[-1].split("}", 1)[0]
    fin = capa.split("_claude_keys_line_finish() {", 1)[-1].split("\n}", 1)[0]
    # zsh CONSERVA el keymap entre líneas: sin esto, ejecutas desde NORMAL y el
    # prompt siguiente sigue en NORMAL, con la tira puesta y sin tocar nada.
    r.check("cada línea nueva empieza en INSERT", "zle -K viins" in ini)
    # Sin esto, cada orden lanzada desde NORMAL deja sus filas de ayuda clavadas
    # en el scrollback para siempre.
    r.check("la tira se borra antes de aceptar la línea",
            "_claude_keys_bar=\"\"" in fin and "reset-prompt" in fin)


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

    # Inicio abre Flow: sin el ~ la tecla Win dejaría de llegar a Windows y
    # Win+E, Win+L… morirían; sin el vkE8, Inicio se abriría encima de Flow.
    if pal["windowsDesktop"]["launcher"].get("startOpensFlow"):
        r.check("Inicio abre Flow: Win sola, Win+S y el clic",
                all(t in src for t in ("~LWin:: Send(\"{Blind}{vkE8}\")", "~LWin Up::",
                                       "#s:: Send(FLOW_KEYS)", "&& OverStartButton()")))
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
        # Por patrón y no por la línea literal: al añadir HideStats() al OnExit
        # el reemplazo dejó de casar SIN AVISAR, el script de prueba ya no salía,
        # agotaba los 45 s y se quedaba vivo robando Alt+Space. Si no casa, que
        # falle aquí y diga por qué.
        patched, n = re.subn(r"(?m)^(OnExit\(.*\))\s*$", r"\1\nExitApp()", src, count=1)
        if n != 1:
            r.check("AutoHotkey carga el script sin errores", False,
                    "no encuentro el OnExit donde colgar el ExitApp de la prueba")
            return
        fh.write(patched)
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
    # La shell bajo pty elige paleta igual que una de verdad: oscura en VS Code,
    # la de terminalMode en el resto. Se espera la que le toca.
    if os.environ.get("TERM_PROGRAM") != "vscode":
        pal = render.terminal(pal)
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
    check_light(r, pal)


def _contrast(a: str, b: str) -> float:
    """Contraste WCAG 2.x entre dos #RRGGBB."""
    def lum(h: str) -> float:
        c = [x / 255 for x in render.rgb(h)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def light_backgrounds(pal: dict) -> dict[str, str]:
    """Cada fondo OPACO que el modo claro pinta, sacado de lo que se genera de
    verdad —ajustes de Windhawk, XAML de Flow, la banda de AHK, el tema de
    Windows Terminal— y no de la paleta, que podría decir una cosa mientras
    un generador pinta otra. {dónde: #RRGGBB}"""
    import windhawk, flow
    d = render.desktop(dict(pal, windowsMode="light"))
    t = render.terminal(dict(pal, terminalMode="light"))
    out: dict[str, str] = {}
    # Lo que NO es fondo aunque vaya en Background/Fill: líneas, indicadores y
    # el subrayado de las pestañas. Esos van en LÍNEA o en acento.
    lines = ("Stroke", "BorderLine", "RunningIndicator")
    for name in ("taskbar_settings", "start_settings", "notification_settings", "explorer_settings"):
        st = getattr(windhawk, name)(d)
        for k, v in st.items():
            if not isinstance(v, str):
                continue
            m = re.search(r'(CommonBgBrush|Background|Fill)[^=]*:?=<SolidColorBrush Color="#FF([0-9A-F]{6})"', v)
            if not m:
                continue
            tgt = st.get(k.split(".styles[")[0] + ".target", k)
            if not any(x in tgt for x in lines):
                out[f"{name.split('_')[0]}:{tgt.split(' > ')[-1][:40]}"] = "#" + m.group(2)
    x = flow.theme_xaml(d)
    out["flow:ventana"] = re.search(r'Property="Background" Value="(#[0-9A-Fa-f]{6})"', x).group(1)
    out["ahk:banda"] = "#" + render.ahk_substitutions(d)["BG"]
    out["iconos:fondo"] = d["surfaces"]["bgAlt"]
    wt = render.wt_theme(t)
    for part in ("tab", "tabRow"):
        for k in ("background", "unfocusedBackground"):
            out[f"wt:{part}.{k}"] = wt[part][k]
    out["wt:terminal"] = render.wt_scheme(t)["background"]
    out["zsh:CC_BG_DARK"] = t["surfaces"]["bgAlt"]
    return {k: v.upper() for k, v in out.items()}


def check_two_tones(r: Report, pal: dict) -> None:
    """El fallo que motivó las dos últimas versiones del claro: primero siete
    blancos, unos azulados y otros neutros; después el terminal en blanco y su
    statusline en la base, con la franja de abajo como una zona aparte. Ahora el
    fondo es UNO, la base, en todo lo que pintamos. La única excepción es el
    contenido del Explorador, que va al blanco de su lista Win32 porque esa no
    se deja pintar."""
    s = render.terminal(dict(pal, terminalMode="light"))["surfaces"]
    base = s["bgAlt"].upper()
    ex = render.desktop(dict(pal, windowsMode="light"))["windowsDesktop"]["explorer"]["surfaces"]
    win32 = {ex.get(k, base).upper() for k in ("canvas", "field")}
    bg = light_backgrounds(pal)
    extra = {k: v for k, v in bg.items()
             if v != base and not (k.startswith("explorer:") and v in win32)}
    r.check(f"claro: un solo fondo ({base}, y el Win32 del Explorador)",
            not extra and s["bg"].upper() == base,
            "; ".join(f"{k}={v}" for k, v in list(extra.items())[:3]) or f"terminal {s['bg']}")


def check_light(r: Report, pal: dict) -> None:
    """La variante clara existe porque los roles oscuros son pasteles y sobre
    blanco no se leen. Esto es lo que no puede volver a pasar. Se mide SIEMPRE,
    esté puesto el modo que esté: quien edite el bloque `light` con todo en
    oscuro tiene que enterarse igual."""
    if "light" not in pal:
        r.skip("modo claro", "palette.json no define el bloque light")
        return
    for key in ("windowsMode", "terminalMode"):
        r.check(f"{key} es light o dark", pal.get(key, "dark") in ("light", "dark"),
                str(pal.get(key)))
    d = render.terminal(dict(pal, terminalMode="light"))
    s = d["surfaces"]
    inks = {"fg": s["fg"], "fgDim": s["fgDim"],
            **{k: v["hex"] for k, v in d["roles"].items()},
            **{f"{k}.bright": v["bright"] for k, v in d["roles"].items()}}
    bad = [f"{k} {v} {_contrast(v, bg):.2f} sobre {bgk}"
           for k, v in inks.items() for bgk, bg in (("bg", s["bg"]), ("bgAlt", s["bgAlt"]))
           if _contrast(v, bg) < 4.5]
    r.check("claro: texto >= 4.5:1 sobre bg y bgAlt", not bad, "; ".join(bad[:3]))
    bad = [f"{k} {v} {_contrast(v, s['bg']):.2f}" for k, v in d["ansi"].items()
           if _contrast(v, s["bg"]) < 4.5]
    r.check("claro: los 16 ANSI >= 4.5:1", not bad, "; ".join(bad[:3]))
    r.check("claro: ansi.cyan == roles.teal", d["ansi"]["cyan"].lower() == d["roles"]["teal"]["hex"].lower(),
            f"{d['ansi']['cyan']} vs {d['roles']['teal']['hex']}")
    base = render.desktop(dict(pal, windowsMode="light"))["windowsAccent"]["base"]
    r.check("claro: borde activo >= 3:1 sobre blanco", _contrast(base, s["bg"]) >= 3,
            f"{base} {_contrast(base, s['bg']):.2f}")
    # VS Code se queda oscuro, y zsh es el mismo dentro que fuera: la paleta de
    # zsh tiene que llevar las dos ramas, y la de VS Code ser la oscura.
    z = render.palette_zsh(dict(pal, terminalMode="light"))
    vs = z.split("then", 1)[-1].split("else", 1)[0]
    r.check("claro: zsh en VS Code sigue oscuro",
            "TERM_PROGRAM == vscode" in z and f"CC_HEX_BG='{pal['surfaces']['bg']}'" in vs
            and f"CC_HEX_BG='{s['bg']}'" in z.split("else", 1)[-1])
    check_two_tones(r, pal)
    # Los colores de las insignias de modo (NORMAL, INSERT…) tienen que seguir a
    # la paleta del terminal y no llevar el hex escrito: así salió el NORMAL en el
    # morado pastel del oscuro sobre el fondo claro.
    km = [ln for ln in render.keymap_zsh(pal).splitlines() if "_ROLE=" in ln]
    r.check("claro: las insignias de modo siguen a la paleta",
            bool(km) and all('="${CC_HEX_' in ln for ln in km),
            next((ln for ln in km if '="${CC_HEX_' not in ln), "sin _ROLE")[:60])
    # El tema de Claude Code sale de esta paleta (render.claude_theme). Si el
    # instalado no coincide, alguien lo editó a mano o no se regeneró, y el
    # terminal y Claude Code vuelven a tener cada uno sus colores.
    cc = pathlib.Path(os.environ.get("CLAUDE_CONFIG_DIR") or pathlib.Path.home() / ".claude") / "themes/terminal-light.json"
    if cc.exists():
        r.check("claro: tema de Claude Code == generado", json.loads(cc.read_text()) == render.claude_theme(pal),
                "lib/render.py claude-theme > " + str(cc))
    else:
        r.skip("claro: tema de Claude Code", f"no está instalado en {cc}")
    if shutil.which("zsh"):
        tmp = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / "claude-selftest-palette.zsh"
        tmp.write_text(z, encoding="utf-8")
        p = subprocess.run(["zsh", "-n", str(tmp)], capture_output=True, text=True)
        tmp.unlink(missing_ok=True)
        r.check("claro: la paleta de zsh es zsh válido", p.returncode == 0, p.stderr.strip()[:60])
    check_desktop_choices(r, pal)
    check_bat_themes(r, pal)


def check_bat_themes(r: Report, pal: dict) -> None:
    """El tema de código: cada color se lee sobre su fondo, y el instalado es el
    que sale de la paleta (si no, alguien lo tocó a mano o no se regeneró)."""
    import plistlib
    for mode in ("light", "dark"):
        tp = render.terminal(dict(pal, terminalMode="light")) if mode == "light" else pal
        src = render.bat_theme(tp, f"claude-{mode}")
        d = plistlib.loads(src.encode())
        bg = d["settings"][0]["settings"]["background"]
        bad = [f"{x['name']} {x['settings']['foreground']} {render.contrast(x['settings']['foreground'], bg):.2f}"
               for x in d["settings"][1:] if render.contrast(x["settings"]["foreground"], bg) < 4.5]
        r.check(f"bat {mode}: todo >= 4.5:1 sobre el fondo", not bad, "; ".join(bad[:3]))
        bat = shutil.which("bat") or shutil.which("batcat")
        if not bat:
            r.skip(f"bat {mode}: instalado == generado", "bat no está")
            continue
        cfg = subprocess.run([bat, "--config-dir"], capture_output=True, text=True).stdout.strip()
        f = pathlib.Path(cfg, "themes", f"claude-{mode}.tmTheme")
        if f.exists():
            r.check(f"bat {mode}: instalado == generado", f.read_text() == src,
                    f"python3 lib/render.py bat-theme-{mode} > {f}")
        else:
            r.skip(f"bat {mode}: instalado == generado", f"no está en {f}")


def check_desktop_choices(r: Report, pal: dict) -> None:
    """Lo que el escritorio lee de la paleta sin ser color: un valor que no esté
    en la lista para el instalador a medias, y un fondo que no existe no se pone."""
    import desktop, wallpaper
    wd = pal["windowsDesktop"]
    r.check("escritorio: pinnedIcons es glyphs o stock",
            wd.get("pinnedIcons", "glyphs") in ("glyphs", "stock"), str(wd.get("pinnedIcons")))
    r.check("escritorio: taskbar.search es válido",
            wd["taskbar"].get("search", "icon") in desktop.SEARCH_MODES, str(wd["taskbar"].get("search")))
    # Los colores por estado de la barra van como recursos de tema: los
    # selectores con estado del README del mod no casan en la build 26200 (ver
    # HANDOFF). Si alguien los devuelve a controlStyles, vuelven a no pintar.
    import windhawk
    tb = windhawk.taskbar_settings(render.desktop(pal))
    res = " ".join(str(v) for k, v in tb.items() if k.startswith("themeResourceVariables"))
    r.check("barra: estados por recurso (indicador y botón activo)",
            all(k in res for k in ("RunningIndicatorActiveBrush", "ShellTaskbarItemFillColorSecondaryBrush"))
            and not any("TaskListLabeledButtonPanel" in str(v) for v in tb.values()), res[:60])
    # tmux: solo aspecto. Un base-index o un prefijo aquí rompería a quien abre
    # paneles por índice, y nadie lo vería hasta que fallase.
    conf = render.tmux_conf(render.terminal(pal))
    r.check("tmux: ni prefijo ni índices, y nada de desatar teclas",
            not re.search(r"base-index|prefix |unbind", conf.replace("client_prefix", "")),
            "el tmux.conf generado toca comportamiento")
    binds = re.findall(r"^bind (?:-T (\S+) )?(\S+)", conf, re.M)
    r.check("tmux: las ataduras son las cinco previstas, y solo con tmux.keys",
            sorted(binds) == (sorted([("copy-mode-vi", "v"), ("copy-mode-vi", "y"), ("", "'\"'"), ("", "%"), ("", "c")])
                              if pal.get("tmux", {}).get("keys") else []), str(binds))
    auto = bool(pal.get("tmux", {}).get("autostart"))
    r.check("tmux: ratón e historial largo solo con autostart",
            ("set -g mouse on" in conf) == auto and ("history-limit" in conf) == auto, f"autostart={auto}")
    layer = (render.ROOT / "shell/claude-05-tmux.zsh").read_text(encoding="utf-8")
    r.check("tmux al abrir: solo en WT, fuera de tmux y de Claude Code, y con salida si falla",
            all(g in layer for g in ("-o interactive", "-n $WT_SESSION", "-z $TMUX", "-z $CLAUDECODE"))
            and "&& exit" in layer and "exec tmux" not in layer.split("if [[ -o interactive")[1], "guardas")
    r.check("tmux: la barra va en el fondo del terminal",
            f'status-style "bg={render.terminal(pal)["surfaces"]["bg"]},' in conf, "status-style")
    # La integración con Windows Terminal: solo allí y fuera de tmux, y las
    # acciones del tema con su prefijo, que es lo que permite retirarlas.
    theme = (render.ROOT / "shell/claude.zsh-theme").read_text(encoding="utf-8")
    r.check("shell: OSC 133 solo en Windows Terminal y fuera de tmux",
            "if [[ -n $WT_SESSION && -z $TMUX ]]; then" in theme and theme.count("133;A") == 1, "guarda")
    acts, keys = render.wt_actions()
    r.check("WT: cada acción del tema tiene su tecla y su prefijo",
            len(acts) == len(keys) and all(a["id"].startswith(render.WT_ACTION_PREFIX) for a in acts + keys),
            str(len(acts)))
    # La cabecera del Explorador: ocultar la barra de comandos sin ajustar el
    # contenedor deja un hueco en blanco; las dos cosas van juntas o ninguna.
    ex = windhawk.explorer_settings(render.desktop(pal))
    hidden = any("CommandBarControl" in str(ex.get(k, "")) and ex.get(k.replace(".target", ".styles[0]")) == "Visibility=Collapsed"
                 for k in ex if k.endswith(".target"))
    r.check("Explorador: barra de comandos oculta ⇔ contenedor a 87 px",
            (ex["explorerFrameContainerHeight"] == 87) == hidden, str(ex["explorerFrameContainerHeight"]))
    import titlebar
    r.check("título: twips del registro a píxeles", titlebar.px("-330") == 22 and titlebar.px("-270") == 18, "px()")
    # El puntero y el tema con nombre: lo que se puede comprobar sin tocar Windows.
    import pointer, wintheme
    r.check("puntero: el color va como COLORREF (BGR)", pointer.colorref("#BFFF00") == 0xFFBF,
            hex(pointer.colorref("#BFFF00")))
    for mode in ("dark", "light"):
        pt = render.desktop(dict(pal, windowsMode=mode))["windowsDesktop"].get("pointer")
        if pt:
            r.check(f"{mode}: pointer.color es #RRGGBB",
                    bool(re.fullmatch(r"#[0-9A-Fa-f]{6}", pt.get("color", ""))), str(pt.get("color")))
    th = wintheme.named("[Theme]\nDisplayName=Tema sin guardar\nThemeId={X}\n[boot]\n", "Claude Light")
    r.check("tema: la copia cambia nombre e id y nada más",
            "DisplayName=Claude Light\n" in th and "{X}" not in th and th.endswith("[boot]\n")
            and wintheme.named("[Theme]\n", "x") == "", th[:40])
    for mode in ("dark", "light"):
        wp = render.desktop(dict(pal, windowsMode=mode))["windowsDesktop"].get("wallpaper")
        if not wp:
            continue
        r.check(f"{mode}: wallpaper.style es válido", wp.get("style", "fill") in wallpaper.STYLES,
                str(wp.get("style")))
        if not pathlib.Path("/mnt/c").is_dir():
            r.skip(f"{mode}: el fondo existe", "sin /mnt/c")
            continue
        unix = subprocess.run(["wslpath", "-u", wp["image"]], capture_output=True, text=True).stdout.strip()
        r.check(f"{mode}: el fondo existe", bool(unix) and pathlib.Path(unix).is_file(), wp["image"])


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
