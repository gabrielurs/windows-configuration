# claude-20-shell.zsh — historial, completado y teclas.
#
# Carga después de claude-00-palette.zsh y claude-10-colors.zsh: oh-my-zsh
# sourcea $ZSH_CUSTOM/*.zsh por orden alfabético, así que aquí ya existen
# CC_HEX_TEAL y compañía.
#
# Nada de esto pinta: el color lo pone la capa 10. Esto es cómo se COMPORTA.

# ── historial ─────────────────────────────────────────────────────────
HISTFILE="${HISTFILE:-$HOME/.zsh_history}"
HISTSIZE=100000       # en memoria
SAVEHIST=100000       # en disco — sin esto zsh guarda por defecto ridículamente poco

setopt EXTENDED_HISTORY       # guarda cuándo se lanzó y cuánto tardó
setopt SHARE_HISTORY          # las pestañas se ven entre ellas al vuelo
setopt HIST_IGNORE_DUPS       # no repite el comando inmediatamente anterior
setopt HIST_IGNORE_ALL_DUPS   # y borra el duplicado viejo cuando se repite
setopt HIST_EXPIRE_DUPS_FIRST # si hay que tirar líneas, primero las repetidas
setopt HIST_FIND_NO_DUPS      # al buscar, no ofrece la misma línea dos veces
setopt HIST_SAVE_NO_DUPS
setopt HIST_REDUCE_BLANKS
setopt HIST_IGNORE_SPACE      # una línea que empieza por espacio no se guarda
setopt HIST_VERIFY            # !! y !$ se expanden y te dejan mirarlos antes de correr

# SHARE_HISTORY implica INC_APPEND_HISTORY, no hace falta ponerlo.
# El precio: la flecha arriba puede traerte algo escrito en OTRA pestaña. A
# cambio, cierras una terminal y no pierdes nada. Si molesta: unsetopt SHARE_HISTORY.

# ── navegación por directorios ────────────────────────────────────────
setopt AUTO_CD                # «proyectos» sin más ya es un cd
setopt AUTO_PUSHD             # cada cd apila; «cd -<Tab>» enseña por dónde has pasado
setopt PUSHD_IGNORE_DUPS
setopt PUSHD_SILENT           # apilar no imprime la pila entera
DIRSTACKSIZE=20

setopt EXTENDED_GLOB          # ^, ~ y (#i) en los globs
setopt INTERACTIVE_COMMENTS   # un # en la línea es un comentario, no un error
setopt NO_BEEP
unsetopt FLOW_CONTROL         # libera Ctrl+S y Ctrl+Q, que no los usa nadie para XOFF

# ── completado ────────────────────────────────────────────────────────
zmodload -i zsh/complist      # lo pide «menu select»

setopt AUTO_MENU              # el segundo Tab abre el menú navegable
setopt ALWAYS_TO_END          # al completar, el cursor va al final
setopt COMPLETE_IN_WORD       # completa en medio de una palabra, no solo al final
setopt NO_LIST_BEEP

# Ojo: «menu select» y los formatos de descriptions/corrections/warnings los pone
# ya la capa 10, y con un patrón de cinco tramos (:completion:*:*:*:*:descriptions)
# que es MÁS específico que un :completion:*:descriptions. En zstyle gana el más
# específico, así que repetirlos aquí sería código muerto. Y el gris que usa allí
# es el correcto: en esta paleta las etiquetas y separadores son grises, el ámbar
# es para números y métricas.

# Insensible a mayúsculas, y además completa por trozos:
#   dow<Tab>   → Downloads
#   f.j<Tab>   → fichero.json
#   c-t<Tab>   → claude-terminal-theme
zstyle ':completion:*' matcher-list \
  'm:{a-zA-Z}={A-Za-z}' \
  'r:|[._-]=* r:|=*' \
  'l:|=* r:|=*'

# Cada tipo de candidato bajo su epígrafe, en vez de un tapiz plano.
zstyle ':completion:*' group-name ''
zstyle ':completion:*' verbose yes
# messages sí es nuestro: la capa 10 no lo define.
zstyle ':completion:*:messages' format "%F{$CC_HEX_BLUE}-- %d --%f"

# La caché evita que el primer Tab sobre apt o systemctl tarde un segundo.
zstyle ':completion:*' use-cache on
zstyle ':completion:*' cache-path "${XDG_CACHE_HOME:-$HOME/.cache}/zsh/zcompcache"

# kill <Tab> enseña TUS procesos, con el pid en ámbar como el resto de números.
zstyle ':completion:*:*:kill:*:processes' \
  command 'ps -u "$USER" -o pid,%cpu,tty,cputime,comm -w'
zstyle ':completion:*:*:kill:*:processes' list-colors \
  "=(#b) #([0-9]#)*=0=${CC_AMBER}"

# Dentro del menú
bindkey -M menuselect '^[[Z' reverse-menu-complete   # Shift+Tab retrocede
bindkey -M menuselect '^[' send-break                # Esc cierra sin elegir

# ── teclas ────────────────────────────────────────────────────────────
bindkey -e                                  # emacs; es lo que espera todo el mundo

bindkey '^[[H'    beginning-of-line         # Inicio
bindkey '^[[F'    end-of-line               # Fin
bindkey '^[[3~'   delete-char               # Supr
bindkey '^[[1;5C' forward-word              # Ctrl+→
bindkey '^[[1;5D' backward-word             # Ctrl+←
bindkey '^[[3;5~' kill-word                 # Ctrl+Supr

# Ojo: en Windows Terminal, Ctrl+Retroceso manda ^H y el Retroceso normal ^?.
# Por eso esto no se come el borrado de toda la vida.
bindkey '^H' backward-kill-word

# Sin la barra, Ctrl+W borra UN segmento de ruta en vez de la ruta entera.
WORDCHARS='*?_-.[]~&;!#$%^(){}<>'
