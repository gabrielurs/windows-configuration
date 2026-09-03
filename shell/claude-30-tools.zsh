# claude-30-tools.zsh — las herramientas modernas, vestidas con la paleta.
#
# Todo va dentro de un `command -v`: en una máquina donde falte fzf o eza, esta
# capa no hace nada y el shell sigue funcionando igual. Por eso el instalador
# puede copiarla siempre, aunque las dependencias sean opcionales.
#
# Carga después de la 10, así que lo que pise aquí (las alias de ls, GIT_PAGER)
# es deliberado.

# ── fzf ───────────────────────────────────────────────────────────────
if (( $+commands[fzf] )); then
  # Los colores salen de CC_HEX_*, o sea de palette.json. Cambia un hex allí,
  # relanza install.sh y el buscador cambia con todo lo demás.
  export FZF_DEFAULT_OPTS="\
--height=45% --layout=reverse --border=rounded --info=inline --cycle \
--prompt='❯ ' --pointer='▸' --marker='✓' \
--color=fg:${CC_HEX_FG},hl:${CC_HEX_TEAL} \
--color=fg+:${CC_HEX_WHITE},bg+:${CC_HEX_SELECTION},hl+:${CC_HEXB_TEAL} \
--color=info:${CC_HEX_AMBER},prompt:${CC_HEX_TEAL},pointer:${CC_HEX_TEAL} \
--color=marker:${CC_HEX_GREEN},spinner:${CC_HEX_PURPLE} \
--color=header:${CC_HEX_GREY},border:${CC_HEX_BORDER},gutter:-1"

  # fd respeta .gitignore y no se mete en .git; find no hace ni lo uno ni lo otro.
  if (( $+commands[fdfind] || $+commands[fd] )); then
    _ccfd=fdfind; (( $+commands[fd] )) && _ccfd=fd
    export FZF_DEFAULT_COMMAND="$_ccfd --type f --hidden --follow --exclude .git"
    export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
    export FZF_ALT_C_COMMAND="$_ccfd --type d --hidden --follow --exclude .git"
    unset _ccfd
  fi

  # Ctrl+T con vista previa: bat si está, cat si no.
  if (( $+commands[batcat] || $+commands[bat] )); then
    _ccbat=batcat; (( $+commands[bat] )) && _ccbat=bat
    export FZF_CTRL_T_OPTS="--preview '$_ccbat --style=numbers --color=always --theme=ansi {} 2>/dev/null || cat {}' --preview-window=right:60%:border-left"
    unset _ccbat
  fi
  export FZF_ALT_C_OPTS="--preview 'ls -1 --color=always {} 2>/dev/null | head -40' --preview-window=right:50%:border-left"
  # Ctrl+R: la fecha en gris a la izquierda, y la línea entera visible al pulsar ?
  export FZF_CTRL_R_OPTS="--preview 'echo {}' --preview-window=down:3:hidden:wrap --bind '?:toggle-preview'"

  # Ubuntu reparte los scripts de fzf por sitios distintos según la versión, y
  # `fzf --zsh` no existe antes de la 0.48. Se prueban todos y se para en el
  # primero que exista; si no hay ninguno, Ctrl+R sigue siendo el de zsh pelado.
  # El </dev/null no es adorno: si una fzf vieja no reconoce --zsh podría quedarse
  # esperando entrada, y eso es un arranque de shell colgado.
  if fzf --zsh </dev/null >/dev/null 2>&1; then
    source <(fzf --zsh </dev/null)
  else
    for _ccf in /usr/share/doc/fzf/examples /usr/share/fzf/shell \
                /usr/share/fzf "$HOME/.fzf/shell"; do
      [[ -r $_ccf/key-bindings.zsh ]] && { source "$_ccf/key-bindings.zsh"; break }
    done
    for _ccf in /usr/share/zsh/vendor-completions /usr/share/doc/fzf/examples \
                /usr/share/fzf/shell "$HOME/.fzf/shell"; do
      [[ -r $_ccf/completion.zsh ]] && { source "$_ccf/completion.zsh"; break }
      [[ -r $_ccf/_fzf ]] && break
    done
    unset _ccf
  fi
fi

# ── eza: ls con iconos, sin romper el esquema de color ────────────────
# La paleta asigna un color por TIPO de dato, no por extensión. eza respeta eso
# vía EZA_COLORS, y encima añade lo que ls no sabe: el estado de git por fichero.
if (( $+commands[eza] )); then
  export EZA_COLORS="\
di=1;${CC_TEAL}:ln=${CC_BLUE}:ex=${CC_GREEN}:\
uu=${CC_GREY}:gu=${CC_GREY}:un=${CC_GREY}:gn=${CC_GREY}:\
da=${CC_GREY}:sn=${CC_AMBER}:sb=${CC_GREY}:\
ur=${CC_TEAL}:uw=${CC_AMBER}:ux=${CC_GREEN}:ue=${CC_GREEN}:\
gr=${CC_TEAL}:gw=${CC_AMBER}:gx=${CC_GREEN}:\
tr=${CC_TEAL}:tw=${CC_AMBER}:tx=${CC_GREEN}:\
ga=${CC_GREEN}:gm=${CC_AMBER}:gd=${CC_RED}:gv=${CC_PURPLE}:\
xx=${CC_GREY}"

  # Los iconos salen de palette.json, no de una suposición. eza los dibuja con
  # codepoints de la zona de uso privado (U+E000–U+F8FF) y ahí solo hay glifos si
  # la fuente es una Nerd Font; con Cascadia Code a secas salen TODOS como «?».
  # Por eso font.nerdGlyphs viene en false: se pone a true cuando font.face lo es.
  #
  # Ojo con «--icons=auto»: el auto mira si hay terminal, NO si hay glifos. No
  # protege de nada aquí.
  _cci=never; [[ ${CC_NERD_GLYPHS:-0} == 1 ]] && _cci=auto

  alias ls="eza --group-directories-first --icons=$_cci"
  alias ll="eza -l --group-directories-first --icons=$_cci --git --time-style=long-iso"
  alias la="eza -la --group-directories-first --icons=$_cci --git --time-style=long-iso"
  alias lt="eza --tree --level=2 --icons=$_cci --group-directories-first"
  alias tree="eza --tree --icons=$_cci --group-directories-first"
  unset _cci
fi

# ── bat ───────────────────────────────────────────────────────────────
# El tema «ansi» pinta con los 16 colores del terminal, que en palette.json SON
# la paleta (ansi.cyan es el teal). O sea: bat sigue al tema solo, sin .tmTheme.
if (( $+commands[batcat] || $+commands[bat] )); then
  (( $+commands[bat] )) || alias bat='batcat'
  export BAT_THEME=ansi
  export BAT_STYLE='numbers,changes,header'
  # `cat` se deja en paz a propósito: aliasarlo rompe las tuberías de quien
  # espera texto pelado. Para leer con colores, `bat`.
fi

# ── fd ────────────────────────────────────────────────────────────────
# En Debian y Ubuntu el binario se llama fdfind: «fd» ya lo ocupaba otro paquete.
(( $+commands[fdfind] && ! $+commands[fd] )) && alias fd='fdfind'

# ── zoxide: el cd que aprende ─────────────────────────────────────────
# `z proy` salta a lo más visitado que encaje. Se carga al final para que su
# hook de precmd no pelee con el del prompt.
(( $+commands[zoxide] )) && eval "$(zoxide init zsh)"

# ── delta: diffs de git legibles ──────────────────────────────────────
# Los ajustes van como ARGUMENTOS y no por GIT_CONFIG_COUNT, que es lo primero
# que se probó: git sí honra esas variables, pero delta lee el gitconfig con
# libgit2 y ese mecanismo lo implementa el binario de git, no la librería. O sea
# que `git config --get delta.plus-style` devolvía el valor y delta seguía con
# sus colores. Comprobado con `delta --show-config`.
#
# Y tampoco se escribe en tu ~/.gitconfig: ese fichero es tuyo, y si el tema lo
# tocara el desinstalador tendría que restaurarlo.
if (( $+commands[delta] )); then
  export DELTA_PAGER="less -R"
  export GIT_PAGER="delta \
    --syntax-theme=ansi \
    --line-numbers --navigate --hyperlinks \
    --file-style='${CC_HEX_TEAL} bold' \
    --file-decoration-style='${CC_HEX_BORDER} ul' \
    --hunk-header-style='syntax' \
    --hunk-header-decoration-style='${CC_HEX_BORDER}' \
    --line-numbers-left-style='${CC_HEX_GHOST}' \
    --line-numbers-right-style='${CC_HEX_GHOST}' \
    --line-numbers-plus-style='${CC_HEX_GREEN}' \
    --line-numbers-minus-style='${CC_HEX_RED}' \
    --plus-style='syntax ${CC_HEX_DIFFPLUS}' \
    --minus-style='syntax ${CC_HEX_DIFFMINUS}' \
    --plus-emph-style='syntax ${CC_HEX_SELECTION}' \
    --minus-emph-style='syntax ${CC_HEX_SELECTION}'"
fi

# ── tldr ──────────────────────────────────────────────────────────────
(( $+commands[tldr] )) && export TLDR_COLOR_BLANK=white \
  TLDR_COLOR_NAME=cyan TLDR_COLOR_DESCRIPTION=white \
  TLDR_COLOR_EXAMPLE=green TLDR_COLOR_COMMAND=cyan TLDR_COLOR_PARAMETER=yellow
