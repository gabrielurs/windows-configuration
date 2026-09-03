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


def parse(out: str) -> tuple[dict[str, str], str]:
    """Saca los pares clave=valor y el bloque de `ls`.

    Hay que limpiar antes: bajo pty el prompt mete secuencias de escape y
    títulos de ventana (OSC) en medio de la salida.
    """
    clean = re.sub(r"\x1b][0-9];[^\x07\x1b]*(\x07|\x1b\\)", "", out)
    clean = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", clean).replace("\r", "")
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


def check_shell(r: Report, pal: dict) -> None:
    r.section("shell (zsh bajo pty)")
    out, err = zsh_under_pty(PROBE)
    if err:
        r.check("la sonda arranca", False, err)
        return
    f, (ls_block, ls_control) = parse(out)
    if not f:
        r.check("la sonda arranca", False, "no devolvió ningún hecho")
        return

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
                        ("registry",    lambda s: "\t" in s)):
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
    check_shell(r, pal)
    check_delta(r, pal)
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
