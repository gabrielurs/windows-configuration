# claude-30-tools.zsh — las herramientas modernas, vestidas con la paleta.
#
# Todo va dentro de un `command -v`: en una máquina donde falte fzf o eza, esta
# capa no hace nada y el shell sigue funcionando igual. Por eso el instalador
# puede copiarla siempre, aunque las dependencias sean opcionales.
#
# Carga después de la 10, así que lo que pise aquí (las alias de ls, GIT_PAGER)
# es deliberado.

# Los iconos de eza, decididos una vez para todo el fichero: las alias, las
# vistas previas de fzf y el listado al cambiar de directorio. Global y no local
# porque el listado lo usa en cada cd, mucho después de cargar esto.
#
# always/never y NUNCA auto. Dos razones: el auto mira si hay terminal, no si
# hay glifos, así que no protege de nada; y encima en eza 0.18.2 —la de Ubuntu
# noble— «auto» no saca iconos ni con un pty delante, con lo que el ajuste
# dependía de la versión instalada. Con always/never hace lo que dice siempre.
typeset -g _claude_icons=never
[[ ${CC_NERD_GLYPHS:-0} == 1 ]] && _claude_icons=always

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
    export FZF_CTRL_T_OPTS="--preview '$_ccbat --style=numbers --color=always --italic-text=always {} 2>/dev/null || cat {}' --preview-window=right:60%:border-left"
    unset _ccbat
  fi
  # Alt+C enseña el árbol a dos niveles, que es lo que dice si ese es el
  # directorio que buscas; una lista plana no lo dice.
  if (( $+commands[eza] )); then
    export FZF_ALT_C_OPTS="--preview 'eza --tree --level=2 --color=always --icons=$_claude_icons --group-directories-first {} 2>/dev/null | head -200' --preview-window=right:50%:border-left"
  else
    export FZF_ALT_C_OPTS="--preview 'ls -1 --color=always {} 2>/dev/null | head -40' --preview-window=right:50%:border-left"
  fi
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

  # ── fzf-tab: el Tab abre fzf en vez del menú de zsh ──
  # Lo carga oh-my-zsh como plugin, ANTES de estas capas: tiene que ir después
  # de compinit y antes de zsh-autosuggestions, que envuelve widgets. Aquí solo
  # se viste, y solo si está: sin él, el menú de la capa 10 sigue como estaba.
  if (( ${+functions[fzf-tab-complete]} )); then
    # Sin `menu no` zsh abre su menú antes y fzf-tab no llega a ver el prefijo.
    zstyle ':completion:*' menu no
    # Los epígrafes son los grupos de fzf-tab, y los quiere SIN secuencias de
    # escape: con las de la capa 10 los grupos desaparecen sin decir nada. Va con
    # el mismo patrón de cinco tramos que usa allí, que si no aquel gana por ser
    # más específico.
    zstyle ':completion:*:*:*:*:descriptions' format '[%d]'
    # Los colores y el borde de FZF_DEFAULT_OPTS, que por defecto no hereda.
    zstyle ':fzf-tab:*' use-fzf-default-opts yes
    zstyle ':fzf-tab:*' switch-group '<' '>'
    # El punto de color de cada grupo, en el orden de la paleta en vez del arco
    # iris ANSI que trae de serie.
    zstyle ':fzf-tab:*' group-colors \
      $'\e['"${CC_TEAL}"'m' $'\e['"${CC_BLUE}"'m' $'\e['"${CC_PURPLE}"'m' \
      $'\e['"${CC_AMBER}"'m' $'\e['"${CC_GREEN}"'m' $'\e['"${CC_GREY}"'m'
    # Vista previa donde dice algo: el contenido del directorio al que vas a
    # entrar, y el fichero que vas a abrir. $realpath lo pone fzf-tab.
    if (( $+commands[eza] )); then
      zstyle ':fzf-tab:complete:(cd|pushd|z|__zoxide_z):*' fzf-preview \
        "eza -1 --color=always --icons=$_claude_icons --group-directories-first \$realpath"
    fi
    if (( $+commands[batcat] || $+commands[bat] )); then
      _ccbat=batcat; (( $+commands[bat] )) && _ccbat=bat
      zstyle ':fzf-tab:complete:(bat|batcat|cat|less|vim|nvim|code):*' fzf-preview \
        "[[ -d \$realpath ]] && ls -1 --color=always \$realpath || $_ccbat --style=numbers --color=always --italic-text=always --line-range=:200 \$realpath 2>/dev/null"
      unset _ccbat
    fi
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
  # Por eso font.nerdGlyphs va a la par que font.face. El valor, arriba del todo.
  alias ls="eza --group-directories-first --icons=$_claude_icons"
  alias ll="eza -l --group-directories-first --icons=$_claude_icons --git --time-style=long-iso"
  alias la="eza -la --group-directories-first --icons=$_claude_icons --git --time-style=long-iso"
  alias lt="eza --tree --level=2 --icons=$_claude_icons --group-directories-first"
  alias tree="eza --tree --icons=$_claude_icons --group-directories-first"

  # ── al entrar en un directorio, qué hay ──
  # En rejilla y con tope de filas: en un node_modules la lista entera se come la
  # pantalla, y lo que se quiere al entrar es un vistazo, no el inventario. Lo
  # que no cabe se resume en una línea. CC_CD_LS_LINES=0 lo apaga.
  #
  # Solo en una shell interactiva con terminal delante: un script que haga cd, o
  # la shell de una herramienta, no tiene por qué recibir listados.
  : ${CC_CD_LS_LINES:=12}
  _claude_cd_ls() {
    [[ -o interactive && -t 1 ]] || return 0
    (( CC_CD_LS_LINES > 0 )) || return 0
    local out
    # --width porque con la salida capturada eza no sabe el ancho y cae a una
    # columna; --color=always por lo mismo.
    out=$(command eza --grid --color=always --icons=$_claude_icons \
            --group-directories-first --width=${COLUMNS:-80} 2>/dev/null) || return 0
    [[ -n $out ]] || return 0
    local -a lines=("${(@f)out}")
    if (( $#lines > CC_CD_LS_LINES )); then
      print -r -- "${(F)lines[1,CC_CD_LS_LINES]}"
      print -P -- "%F{$CC_HEX_GHOST}… $(( $#lines - CC_CD_LS_LINES )) filas más%f"
    else
      print -r -- "$out"
    fi
  }
  autoload -Uz add-zsh-hook
  add-zsh-hook chpwd _claude_cd_ls
fi

# ── bat ───────────────────────────────────────────────────────────────
# Tema propio, generado desde la paleta (`render.py bat-theme-light|dark`, lo
# instala install.sh): el claro en Windows Terminal y el oscuro en VS Code,
# según CC_MODE. El «ansi» de antes pinta con los 16 colores del terminal pero
# con su propio reparto: los comentarios salían verdes, como los strings. Si el
# tema no está instalado, ansi, que al menos sigue a la paleta.
if (( $+commands[batcat] || $+commands[bat] )); then
  _ccbat=batcat; (( $+commands[bat] )) && _ccbat=bat
  # bat trae la cursiva apagada (--italic-text=never) y no hay variable de
  # entorno para encenderla: sin esto los comentarios no salen en cursiva.
  alias bat="$_ccbat --italic-text=always"
  unset _ccbat
  if [[ -f "${XDG_CONFIG_HOME:-$HOME/.config}/bat/themes/claude-${CC_MODE:-dark}.tmTheme" ]]; then
    export BAT_THEME="claude-${CC_MODE:-dark}"
  else
    export BAT_THEME=ansi
  fi
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
    --syntax-theme=${BAT_THEME:-ansi} \
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
    --plus-emph-style='syntax ${CC_HEX_DIFFPLUSEMPH:-$CC_HEX_SELECTION}' \
    --minus-emph-style='syntax ${CC_HEX_DIFFMINUSEMPH:-$CC_HEX_SELECTION}'"
fi

# ── tldr ──────────────────────────────────────────────────────────────
(( $+commands[tldr] )) && export TLDR_COLOR_BLANK=white \
  TLDR_COLOR_NAME=cyan TLDR_COLOR_DESCRIPTION=white \
  TLDR_COLOR_EXAMPLE=green TLDR_COLOR_COMMAND=cyan TLDR_COLOR_PARAMETER=yellow
