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

  alias ls='eza --group-directories-first --icons=auto'
  alias ll='eza -l --group-directories-first --icons=auto --git --time-style=long-iso'
  alias la='eza -la --group-directories-first --icons=auto --git --time-style=long-iso'
  alias lt='eza --tree --level=2 --icons=auto --group-directories-first'
  alias tree='eza --tree --icons=auto --group-directories-first'
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
# Configurado por variable de entorno y NO por ~/.gitconfig: así el tema no
# toca un fichero que es tuyo y que el desinstalador tendría que restaurar.
if (( $+commands[delta] )); then
  export GIT_PAGER="delta"
  export DELTA_PAGER="less -R"
  # delta lee su config de git; estas van por env para no escribir en tu gitconfig
  export GIT_CONFIG_COUNT=8
  export GIT_CONFIG_KEY_0=delta.syntax-theme      GIT_CONFIG_VALUE_0=ansi
  export GIT_CONFIG_KEY_1=delta.line-numbers      GIT_CONFIG_VALUE_1=true
  export GIT_CONFIG_KEY_2=delta.navigate          GIT_CONFIG_VALUE_2=true
  export GIT_CONFIG_KEY_3=delta.hyperlinks        GIT_CONFIG_VALUE_3=true
  export GIT_CONFIG_KEY_4=delta.file-style        GIT_CONFIG_VALUE_4="${CC_HEX_TEAL} bold"
  export GIT_CONFIG_KEY_5=delta.hunk-header-style GIT_CONFIG_VALUE_5="${CC_HEX_GREY}"
  export GIT_CONFIG_KEY_6=delta.plus-style        GIT_CONFIG_VALUE_6="syntax ${CC_HEX_BGALT}"
  export GIT_CONFIG_KEY_7=delta.minus-style       GIT_CONFIG_VALUE_7="syntax ${CC_HEX_BGALT}"
fi

# ── tldr ──────────────────────────────────────────────────────────────
(( $+commands[tldr] )) && export TLDR_COLOR_BLANK=white \
  TLDR_COLOR_NAME=cyan TLDR_COLOR_DESCRIPTION=white \
  TLDR_COLOR_EXAMPLE=green TLDR_COLOR_COMMAND=cyan TLDR_COLOR_PARAMETER=yellow
