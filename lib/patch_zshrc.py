#!/usr/bin/env python3
"""Deja ZSH_THEME y la lista de plugins del .zshrc como los quiere el tema.

Idempotente y conservador: respeta los plugins que ya haya, solo añade los dos
que necesita el resaltado, y pone zsh-syntax-highlighting el último (lo exige
el propio plugin).
"""
import os, pathlib, re, sys

NEEDED = ["zsh-autosuggestions", "zsh-syntax-highlighting"]
LAST = "zsh-syntax-highlighting"

path = pathlib.Path(os.environ.get("ZSHRC", pathlib.Path.home() / ".zshrc"))
if not path.exists():
    sys.exit(f"no existe {path}")
src = path.read_text(encoding="utf-8")
out = src

# ── ZSH_THEME ──
if re.search(r'^\s*ZSH_THEME=.*$', out, re.M):
    out = re.sub(r'^\s*ZSH_THEME=.*$', 'ZSH_THEME="claude"', out, count=1, flags=re.M)
else:
    out = 'ZSH_THEME="claude"\n' + out

# ── plugins=( … ) ──
m = re.search(r'^\s*plugins=\(([^)]*)\)', out, re.M)
if m:
    have = m.group(1).split()
    for p in NEEDED:
        if p not in have:
            have.append(p)
    have = [p for p in have if p != LAST] + [LAST]   # el highlighter, siempre el último
    out = out[:m.start()] + f"plugins=({' '.join(have)})" + out[m.end():]
else:
    out += f"\nplugins=({' '.join(NEEDED)})\n"

# ── truecolor: sin esto los hex se cuantizan a 256 colores ──
if "COLORTERM" not in out:
    out = out.rstrip("\n") + "\n\n# El tema usa color de 24 bits\nexport COLORTERM=truecolor\n"

if out != src:
    path.write_text(out, encoding="utf-8")
    print("  .zshrc actualizado")
else:
    print("  .zshrc ya estaba bien")
