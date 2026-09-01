# claude-10-colors.zsh — paleta "Claude CLI" para ls, grep, less, man,
# completado y los plugins de resaltado.
#
# Depende de claude-00-palette.zsh (generado desde palette.json), que oh-my-zsh
# carga antes por orden alfabético y define CC_TEAL, CC_HEX_TEAL, etc.

# ── ls / dircolors ────────────────────────────────────────────────────
() {
  local -a ls
  ls=(
    "no=0" "fi=0"
    "di=01;${CC_TEAL}"                       # directorios
    "ln=${CC_BLUE}"                          # enlaces
    "or=${CC_RED};3"                         # enlace roto
    "mh=${CC_TEAL}"
    "pi=${CC_PURPLE}" "so=${CC_PURPLE}" "do=${CC_PURPLE}"
    "bd=${CC_PURPLE};1" "cd=${CC_PURPLE};1"
    "su=${CC_RED};1" "sg=${CC_RED};1" "ca=${CC_RED}"
    "tw=01;${CC_TEAL}" "ow=01;${CC_TEAL}" "st=01;${CC_TEAL}"
    "ex=${CC_GREEN}"                         # ejecutables
    "mi=${CC_RED};9"
  )
  local e
  # código fuente e identificadores → verde
  for e in sh bash zsh fish py rb pl go rs c h cc cpp hpp java kt swift \
           js mjs cjs ts tsx jsx vue svelte php lua sql r scala ex exs \
           dart hs ml clj el vim; do ls+=("*.$e=${CC_GREEN}"); done
  # datos, config y documentos → azul
  for e in json yaml yml toml ini cfg conf xml env properties plist \
           md markdown rst txt adoc org tex csv tsv lock; do ls+=("*.$e=${CC_BLUE}"); done
  # comprimidos y binarios → ámbar
  for e in tar tgz gz bz2 xz zst zip rar 7z deb rpm jar war apk iso dmg \
           exe dll so a o bin wasm pyc class; do ls+=("*.$e=${CC_AMBER}"); done
  # media → morado
  for e in png jpg jpeg gif bmp svg webp ico tiff mp4 mkv webm mov avi \
           mp3 flac wav ogg m4a pdf ttf otf woff woff2; do ls+=("*.$e=${CC_PURPLE}"); done
  # ruido → gris
  for e in log bak old tmp swp swo orig rej pid cache DS_Store; do ls+=("*.$e=${CC_GREY}"); done
  ls+=("*~=${CC_GREY}" "*.gitignore=${CC_GREY}"
       "*Makefile=${CC_ORANGE}" "*Dockerfile=${CC_ORANGE}")
  export LS_COLORS="${(j.:.)ls}"
}

alias ls='ls --color=auto'
alias ll='ls -lh --color=auto'
alias la='ls -lAh --color=auto'
alias tree='tree -C'

# ── grep / diff ───────────────────────────────────────────────────────
export GREP_COLORS="ms=01;${CC_GREEN}:mc=01;${CC_AMBER}:sl=:cx=${CC_GREY}:fn=${CC_TEAL}:ln=${CC_AMBER}:bn=${CC_AMBER}:se=${CC_GREY}"
alias grep='grep --color=auto'
alias egrep='grep -E --color=auto'
alias fgrep='grep -F --color=auto'
alias diff='diff --color=auto'
command -v ip >/dev/null && alias ip='ip -color=auto'

# ── less / man ────────────────────────────────────────────────────────
# man no emite SGR: pinta con termcap, de ahí GROFF_NO_SGR.
export LESS='-R -F -X -i -M'
export LESS_TERMCAP_mb=$'\e['"${CC_RED}"'m'
export LESS_TERMCAP_md=$'\e[1;'"${CC_TEAL}"'m'                 # negrita → títulos
export LESS_TERMCAP_me=$'\e[0m'
export LESS_TERMCAP_so=$'\e['"${CC_BG_DARK};1;${CC_AMBER}"'m'  # barra de estado
export LESS_TERMCAP_se=$'\e[0m'
export LESS_TERMCAP_us=$'\e[4;'"${CC_GREEN}"'m'                # subrayado → argumentos
export LESS_TERMCAP_ue=$'\e[0m'
export GROFF_NO_SGR=1
export MANPAGER='less'
export MANROFFOPT='-c'
export GIT_PAGER='less -R'

# ── completado ────────────────────────────────────────────────────────
zstyle ':completion:*' list-colors "${(s.:.)LS_COLORS}"
zstyle ':completion:*:*:*:*:descriptions' format $'\e['"${CC_GREY}"'m-- %d --\e[0m'
zstyle ':completion:*:*:*:*:corrections'  format $'\e['"${CC_AMBER}"'m-- %d (errata) --\e[0m'
zstyle ':completion:*:*:*:*:warnings'     format $'\e['"${CC_RED}"'m-- sin coincidencias --\e[0m'
zstyle ':completion:*' menu select

# ── zsh-autosuggestions ───────────────────────────────────────────────
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE="fg=${CC_HEX_GHOST}"
ZSH_AUTOSUGGEST_STRATEGY=(history completion)

# ── zsh-syntax-highlighting ───────────────────────────────────────────
ZSH_HIGHLIGHT_HIGHLIGHTERS=(main brackets pattern)
typeset -gA ZSH_HIGHLIGHT_STYLES
ZSH_HIGHLIGHT_STYLES[unknown-token]="fg=${CC_HEX_RED},bold"
ZSH_HIGHLIGHT_STYLES[reserved-word]="fg=${CC_HEX_PURPLE}"
ZSH_HIGHLIGHT_STYLES[alias]="fg=${CC_HEX_GREEN}"
ZSH_HIGHLIGHT_STYLES[suffix-alias]="fg=${CC_HEX_GREEN}"
ZSH_HIGHLIGHT_STYLES[global-alias]="fg=${CC_HEX_GREEN}"
ZSH_HIGHLIGHT_STYLES[builtin]="fg=${CC_HEX_GREEN}"
ZSH_HIGHLIGHT_STYLES[function]="fg=${CC_HEX_GREEN}"
ZSH_HIGHLIGHT_STYLES[command]="fg=${CC_HEX_GREEN}"
ZSH_HIGHLIGHT_STYLES[hashed-command]="fg=${CC_HEX_GREEN}"
ZSH_HIGHLIGHT_STYLES[arg0]="fg=${CC_HEX_GREEN}"
ZSH_HIGHLIGHT_STYLES[precommand]="fg=${CC_HEX_GREEN},underline"
ZSH_HIGHLIGHT_STYLES[commandseparator]="fg=${CC_HEX_GREY}"
ZSH_HIGHLIGHT_STYLES[autodirectory]="fg=${CC_HEX_TEAL},underline"
ZSH_HIGHLIGHT_STYLES[path]="fg=${CC_HEX_TEAL}"
ZSH_HIGHLIGHT_STYLES[path_pathseparator]="fg=${CC_HEX_GREY}"
ZSH_HIGHLIGHT_STYLES[path_prefix]="fg=${CC_HEX_TEAL},underline"
ZSH_HIGHLIGHT_STYLES[path_prefix_pathseparator]="fg=${CC_HEX_GREY}"
ZSH_HIGHLIGHT_STYLES[globbing]="fg=${CC_HEX_PURPLE}"
ZSH_HIGHLIGHT_STYLES[history-expansion]="fg=${CC_HEX_PURPLE}"
ZSH_HIGHLIGHT_STYLES[single-hyphen-option]="fg=${CC_HEX_PURPLE}"
ZSH_HIGHLIGHT_STYLES[double-hyphen-option]="fg=${CC_HEX_PURPLE}"
ZSH_HIGHLIGHT_STYLES[back-quoted-argument]="fg=${CC_HEX_AMBER}"
ZSH_HIGHLIGHT_STYLES[single-quoted-argument]="fg=${CC_HEX_AMBER}"
ZSH_HIGHLIGHT_STYLES[double-quoted-argument]="fg=${CC_HEX_AMBER}"
ZSH_HIGHLIGHT_STYLES[dollar-quoted-argument]="fg=${CC_HEX_AMBER}"
ZSH_HIGHLIGHT_STYLES[rc-quote]="fg=${CC_HEXB_AMBER}"
ZSH_HIGHLIGHT_STYLES[dollar-double-quoted-argument]="fg=${CC_HEX_BLUE}"
ZSH_HIGHLIGHT_STYLES[back-double-quoted-argument]="fg=${CC_HEX_BLUE}"
ZSH_HIGHLIGHT_STYLES[back-dollar-quoted-argument]="fg=${CC_HEX_BLUE}"
ZSH_HIGHLIGHT_STYLES[assign]="fg=${CC_HEX_BLUE}"
ZSH_HIGHLIGHT_STYLES[named-fd]="fg=${CC_HEX_GREY}"
ZSH_HIGHLIGHT_STYLES[numeric-fd]="fg=${CC_HEX_GREY}"
ZSH_HIGHLIGHT_STYLES[redirection]="fg=${CC_HEX_GREY}"
ZSH_HIGHLIGHT_STYLES[comment]="fg=${CC_HEX_GREY},italic"
ZSH_HIGHLIGHT_STYLES[default]="fg=${CC_HEX_FG}"
ZSH_HIGHLIGHT_STYLES[bracket-error]="fg=${CC_HEX_RED},bold"
ZSH_HIGHLIGHT_STYLES[bracket-level-1]="fg=${CC_HEX_TEAL}"
ZSH_HIGHLIGHT_STYLES[bracket-level-2]="fg=${CC_HEX_PURPLE}"
ZSH_HIGHLIGHT_STYLES[bracket-level-3]="fg=${CC_HEX_AMBER}"
ZSH_HIGHLIGHT_STYLES[cursor-matchingbracket]='standout'
ZSH_HIGHLIGHT_PATTERNS+=("rm -rf *" "fg=${CC_HEX_RED},bold")

# ── vista previa ──────────────────────────────────────────────────────
claude-palette() {
  local -a nom col hex uso
  nom=(teal verde azul ámbar morado rojo blanco gris)
  col=("$CC_TEAL" "$CC_GREEN" "$CC_BLUE" "$CC_AMBER" "$CC_PURPLE" "$CC_RED" "$CC_WHITE" "$CC_GREY")
  hex=("$CC_HEX_TEAL" "$CC_HEX_GREEN" "$CC_HEX_BLUE" "$CC_HEX_AMBER"
       "$CC_HEX_PURPLE" "$CC_HEX_RED" "$CC_HEX_WHITE" "$CC_HEX_GREY")
  uso=("rutas, ficheros, repos" "identificadores, código, altas" "urls, ramas, enlaces"
       "números, métricas, avisos" "modos y ajustes" "bajas, errores, riesgo"
       "énfasis en prosa" "flechas, separadores, unidades")
  local i
  printf '\e[%sm tema · claude cli\e[0m\n' "$CC_TEAL"
  for i in {1..8}; do
    printf '\e[%sm  ███  %s\e[0m  \e[%sm%-7s\e[0m \e[%sm%s\e[0m\n' \
      "$col[i]" "$hex[i]" "$col[i]" "$nom[i]" "$CC_GREY" "$uso[i]"
  done
  printf '\e[%sm  ANSI 0-15  \e[0m' "$CC_GREY"
  for i in {0..15}; do printf '\e[48;5;%dm  \e[0m' $i; done
  printf '\n'
}
