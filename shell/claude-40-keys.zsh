# claude-40-keys.zsh — atajos de vim en la línea de comandos, y la tira que
# los enseña mientras se aprenden.
#
# Carga después de claude-35-keymap.zsh (generado desde palette.json), que trae
# el chuletario y los ajustes. Aquí solo se ATA: este fichero no contiene ni un
# texto de ayuda ni un color.
#
# Tres cosas, en orden de lo que cuesta:
#
#   · la forma del cursor      bloque en NORMAL, barra en INSERT. Cuesta cero
#                              columnas, así que va SIEMPRE, también con la
#                              tira apagada.
#   · la tira sobre el prompt  which-key: aparece al entrar en NORMAL y se
#                              calla en INSERT. Interruptor: `claude-keys off`.
#   · `claude-keys`            la tabla entera, shell y Windows.
#
# La trampa que ordena todo este fichero: la capa 20 hizo `bindkey -e` y ató
# Inicio, Fin, Ctrl+→ y compañía al keymap `main`, que entonces era `emacs`. En
# cuanto aquí se hace `bindkey -v`, `main` pasa a ser `viins` y TODO aquello
# deja de existir en el mapa activo — no se borra, se queda huérfano en un
# keymap que ya nadie usa. Por eso la sección «lo que la capa 20 daba por hecho»
# no es redundante: sin ella, poner el modo vim rompe las teclas de siempre.

[[ -o interactive ]] || return 0

# ── el interruptor ────────────────────────────────────────────────────
# palette.json pone el valor de fábrica; el fichero de estado, si existe, manda.
# Así `claude-keys off` sobrevive a abrir una pestaña nueva sin reinstalar nada.
typeset -g CC_KEYS_ON=0
_claude_keys_load() {
  local want=${CC_KEYS_HINTS:-off}
  [[ -r $CC_KEYS_STATE ]] && want="$(<$CC_KEYS_STATE)"
  [[ $want == on ]] && CC_KEYS_ON=1 || CC_KEYS_ON=0
}
_claude_keys_load

# El gemelo en Windows: lo sondea claude-keys.ahk para que un solo interruptor
# apague las dos superficies. Se busca por glob y no con `cmd.exe /c echo
# %LOCALAPPDATA%` porque eso son 200 ms de interop por llamada; el directorio lo
# crea lib/keys.py al instalar, así que a estas alturas ya está.
_claude_keys_winstate() {
  if [[ -z ${_claude_keys_winfile+x} ]]; then
    local -a hit=( /mnt/c/Users/*/AppData/Local/claude-terminal-theme(/Nom) )
    _claude_keys_winfile="${hit[1]:+${hit[1]}/hints}"
  fi
  print -rn -- "$_claude_keys_winfile"
}

# ── el modo actual ────────────────────────────────────────────────────
# Se guarda en una variable en vez de preguntarlo al pintar: `zle-keymap-select`
# corre en cada cambio de modo y el prompt se pinta en cada tecla.
typeset -g _claude_keys_mode=insert

# REGION_ACTIVE va PRIMERO y no es un detalle: al entrar en modo visual zsh no
# cambia $KEYMAP —sigue diciendo vicmd— y usa el keymap `visual` como una capa
# por encima. Preguntando solo por KEYMAP, la tira anunciaba NORMAL mientras
# estabas seleccionando, y las ayudas de VISUAL no se veían nunca. Se cazó
# midiendo la pantalla, no leyendo la documentación.
_claude_keys_setmode() {
  if (( ${REGION_ACTIVE:-0} )); then
    _claude_keys_mode=visual
    return
  fi
  case ${KEYMAP:-main} in
    vicmd)  _claude_keys_mode=normal ;;
    viopp)  _claude_keys_mode=viopp ;;
    visual) _claude_keys_mode=visual ;;
    *)      if [[ $ZLE_STATE == *overwrite* ]]; then
              _claude_keys_mode=replace
            else
              _claude_keys_mode=insert
            fi ;;
  esac
}

# DECSCUSR. Windows Terminal y VS Code lo entienden; una terminal que no, lo
# ignora en silencio — no imprime basura.
_claude_keys_cursor() {
  local shape
  case $1 in
    normal)  shape=$CC_KEYS_CURSOR_NORMAL ;;
    replace) shape=$CC_KEYS_CURSOR_REPLACE ;;
    *)       shape=$CC_KEYS_CURSOR_INSERT ;;
  esac
  print -n -- "\e[${shape} q"
}

# ── la tira ───────────────────────────────────────────────────────────
# Deja en `_claude_keys_bar` las líneas del chuletario del modo actual, ya rotas
# al ancho del terminal y con salto de línea al final: el prompt de verdad
# empieza en la fila siguiente y se queda EXACTAMENTE como estaba.
#
# Va a una VARIABLE y no a un `$(…)` dentro del PROMPT por dos razones, y las
# dos importan:
#
#   · `$(…)` se come los saltos de línea finales — es lo que hace la sustitución
#     de comandos— y el salto es justo lo que separa la tira del prompt.
#   · el PROMPT se reevalúa en cada redibujado, o sea en cada tecla. Un fork por
#     pulsación para pintar texto que solo cambia al cambiar de modo es tirar
#     el tiempo del usuario.
#
# En INSERT queda vacía, y por eso mientras escribes no hay tira. Eso es
# `showIn` en palette.json, no una casualidad.
typeset -g _claude_keys_bar=""

_claude_keys_render() {
  _claude_keys_bar=""
  (( CC_KEYS_ON )) || return 0
  local mode=$_claude_keys_mode
  (( ${CC_KEYS_SHOWIN[(Ie)$mode]} )) || return 0

  local var="CC_KEYS_SHELL_${(U)mode}"
  local -a pairs=( "${(@P)var}" )
  (( $#pairs >= 2 )) || return 0
  local bv="${var}_BADGE" rv="${var}_ROLE"
  local badge="${(P)bv}" role="${(P)rv}"

  # El hueco de la insignia: la primera línea la lleva, las siguientes se
  # alinean debajo del primer atajo.
  local -i pad=$(( ${#badge} + 3 ))
  local -i width=${COLUMNS:-100}
  local -i room=$(( width - pad - 1 ))
  (( room < 20 )) && room=$(( width - 1 ))

  local -i i col=0
  local plain out="" line=""
  for (( i = 1; i <= $#pairs; i += 2 )); do
    plain="${pairs[i]} ${pairs[i+1]}"
    if (( col && col + ${#plain} + 3 > room )); then
      out+="${line}"$'\n'
      line=""; col=0
    fi
    (( col )) && { line+="   "; col+=3 }
    # El %% no es paranoia: la salida de esta función vuelve a pasar por la
    # expansión de prompt, así que un % suelto en una descripción se comería el
    # carácter siguiente.
    line+="%F{$CC_HEX_GREEN}${pairs[i]//\%/%%}%f %F{$CC_HEX_GREY}${pairs[i+1]//\%/%%}%f"
    col+=${#plain}
  done
  out+="$line"

  local -a lines=( "${(f)out}" )

  # El tope. En un terminal estrecho la lista entera se comía seis filas, y una
  # ayuda que tapa un cuarto de la pantalla cada vez que pulsas Esc deja de
  # ayudar. Lo que no cabe se resume en un « … » que remite a `claude-keys`.
  local -i max=${CC_KEYS_MAXLINES:-3}
  local cola=""
  if (( max > 0 && $#lines > max )); then
    lines=( "${lines[@]:0:$max}" )
    cola="   %F{$CC_HEX_GHOST}…%f"
  fi

  local blank="${(l:$pad:: :)}"
  _claude_keys_bar="%F{$role}${(r:$pad:: :)badge}%f${lines[1]}"
  local l
  for l in "${lines[@]:1}"; do _claude_keys_bar+=$'\n'"${blank}${l}"; done
  _claude_keys_bar+="${cola}"$'\n'
}

# ── ganchos de ZLE ────────────────────────────────────────────────────
_claude_keys_line_init() {
  _claude_keys_setmode
  _claude_keys_render
  _claude_keys_cursor $_claude_keys_mode
}
_claude_keys_line_finish() {
  # Sin esto, la forma de NORMAL se le queda al programa que lances a
  # continuación: aceptas la línea en modo comando y `vim` arranca con el cursor
  # del tema en vez del suyo.
  _claude_keys_cursor insert
}
_claude_keys_keymap_select() {
  _claude_keys_setmode
  _claude_keys_render
  _claude_keys_cursor $_claude_keys_mode
  (( CC_KEYS_ON )) && zle reset-prompt
}
# El modo visual no avisa por `zle-keymap-select`, así que hace falta mirar en
# cada redibujado si la región se ha activado. Solo se repinta cuando el modo
# CAMBIA: sin esa comparación, un reset-prompt dentro de pre-redraw se llama a
# sí mismo sin parar.
_claude_keys_pre_redraw() {
  local prev=$_claude_keys_mode
  _claude_keys_setmode
  [[ $prev == $_claude_keys_mode ]] && return
  _claude_keys_render
  _claude_keys_cursor $_claude_keys_mode
  (( CC_KEYS_ON )) && zle reset-prompt
}

# `add-zle-hook-widget` y NO `zle -N zle-line-init`. oh-my-zsh carga los plugins
# ANTES que esta capa, y zsh-syntax-highlighting y zsh-autosuggestions cuelgan
# de estos mismos ganchos: un `zle -N` los pisaría y el resaltado dejaría de
# funcionar sin decir por qué. El chaineo solo existe desde zsh 5.3; por debajo
# se cae al modo directo, que es lo que había.
if autoload -Uz +X add-zle-hook-widget 2>/dev/null; then
  zle -N _claude_keys_line_init
  zle -N _claude_keys_line_finish
  zle -N _claude_keys_keymap_select
  zle -N _claude_keys_pre_redraw
  add-zle-hook-widget line-init     _claude_keys_line_init
  add-zle-hook-widget line-finish   _claude_keys_line_finish
  add-zle-hook-widget keymap-select _claude_keys_keymap_select
  add-zle-hook-widget line-pre-redraw _claude_keys_pre_redraw
else
  zle -N zle-line-init     _claude_keys_line_init
  zle -N zle-line-finish   _claude_keys_line_finish
  zle -N zle-keymap-select _claude_keys_keymap_select
fi

# ── modo vim ──────────────────────────────────────────────────────────
bindkey -v
# Centésimas de segundo. El defecto de zsh es 40, o sea que Esc tarda 0,4 s en
# cambiar de modo y parece que el shell se ha colgado.
KEYTIMEOUT=${CC_KEYS_TIMEOUT:-15}

[[ -n $CC_KEYS_ESCAPE ]] && bindkey -M viins "$CC_KEYS_ESCAPE" vi-cmd-mode

# ── lo que la capa 20 daba por hecho ──────────────────────────────────
# Todo esto estaba atado a `main` cuando `main` era emacs. Ahora `main` es
# `viins`, así que hay que repetirlo AQUÍ o las teclas de toda la vida dejan de
# responder en cuanto se enciende el modo vim.
bindkey -M viins '^[[H'    beginning-of-line       # Inicio
bindkey -M viins '^[[F'    end-of-line             # Fin
bindkey -M viins '^[[3~'   delete-char             # Supr
bindkey -M viins '^[[1;5C' forward-word            # Ctrl+→
bindkey -M viins '^[[1;5D' backward-word           # Ctrl+←
bindkey -M viins '^[[3;5~' kill-word               # Ctrl+Supr
bindkey -M viins '^H'      backward-kill-word      # Ctrl+Retroceso en WT
bindkey -M vicmd '^[[H'    beginning-of-line
bindkey -M vicmd '^[[F'    end-of-line

# En vi el retroceso NO cruza el punto donde entraste en INSERT: `vi-backward-
# delete-char` se planta ahí y parece que la tecla se ha roto. Es fiel a vi y es
# insufrible en una shell, donde la línea que editas no la has escrito tú entera.
bindkey -M viins '^?' backward-delete-char

# Las comodidades de emacs dentro de INSERT. No estorban a nada: en vi estas
# combinaciones no significan nada, y son las que tienen los dedos aprendidas.
bindkey -M viins '^a' beginning-of-line
bindkey -M viins '^e' end-of-line
bindkey -M viins '^k' kill-line
bindkey -M viins '^u' backward-kill-line
bindkey -M viins '^w' backward-kill-word
bindkey -M viins '^y' yank

# ── historial con prefijo ─────────────────────────────────────────────
# `up-line-or-beginning-search` hace las dos cosas que quieres de j/k y de las
# flechas: si el buffer tiene varias líneas se mueve entre ellas, y si no, busca
# en el historial lo que ya has tecleado. El `up-line-or-history` de serie
# ignora el prefijo y te pasea por todo el historial.
autoload -Uz up-line-or-beginning-search down-line-or-beginning-search
zle -N up-line-or-beginning-search
zle -N down-line-or-beginning-search
bindkey -M viins '^[[A' up-line-or-beginning-search
bindkey -M viins '^[[B' down-line-or-beginning-search
bindkey -M vicmd '^[[A' up-line-or-beginning-search
bindkey -M vicmd '^[[B' down-line-or-beginning-search
bindkey -M vicmd 'k'    up-line-or-beginning-search
bindkey -M vicmd 'j'    down-line-or-beginning-search

# ── objetos de texto: ciw, di", ca( ──────────────────────────────────
# Es lo que hace que valga la pena el modo vim en una shell: `ci"` para cambiar
# lo de dentro de las comillas de un `git commit -m "…"` sin contar caracteres.
#
# `+X` fuerza la carga ahora en vez de al primer uso: si la versión de zsh no
# trae estas funciones (< 5.0.8), quiero enterarme aquí y saltar el bloque, no
# que reviente la primera vez que alguien escriba `ci"`.
if autoload -Uz +X select-quoted select-bracketed 2>/dev/null; then
  zle -N select-quoted
  zle -N select-bracketed
  () {
    local km q
    for km in viopp visual; do
      for q in "'" '"' '`'; do
        bindkey -M $km "a$q" select-quoted
        bindkey -M $km "i$q" select-quoted
      done
      for q in '(' ')' '[' ']' '{' '}' '<' '>' b B; do
        bindkey -M $km "a$q" select-bracketed
        bindkey -M $km "i$q" select-bracketed
      done
    done
  }
fi

# ── rodear: cs" ' ds" ys ─────────────────────────────────────────────
if autoload -Uz +X surround 2>/dev/null; then
  zle -N delete-surround surround
  zle -N add-surround    surround
  zle -N change-surround surround
  bindkey -M vicmd 'cs' change-surround
  bindkey -M vicmd 'ds' delete-surround
  bindkey -M vicmd 'ys' add-surround
  bindkey -M visual 'S' add-surround
fi

# ── la línea entera en $EDITOR ────────────────────────────────────────
# Para el pipeline de seis tramos que ya no cabe en la cabeza.
#
# En Ctrl+X Ctrl+E y NO en `v`, que es lo que hace media internet. `v` en vi es
# entrar en modo visual, y atarlo al editor deja el modo visual INALCANZABLE:
# el chuletario anunciaba un VISUAL al que no había forma de llegar. Ctrl+X
# Ctrl+E además es la combinación de bash de toda la vida y funciona en los dos
# modos.
if autoload -Uz +X edit-command-line 2>/dev/null; then
  zle -N edit-command-line
  bindkey -M viins '^x^e' edit-command-line
  bindkey -M vicmd '^x^e' edit-command-line
fi

# ── fzf ───────────────────────────────────────────────────────────────
# La capa 30 carga fzf ANTES de que aquí se haga `bindkey -v`. Las versiones
# recientes atan sus widgets a emacs, vicmd Y viins, así que sobreviven al
# cambio; las viejas solo a emacs, y entonces Ctrl+R se habría perdido sin decir
# nada. Se vuelve a atar solo si el widget existe de verdad.
#
# Y en viins Y SOLO en viins. Atarlo también en `vicmd` fue un error: ahí `^r`
# es `redo` —la pareja de `u`— y el chuletario anunciaba «deshacer / rehacer»
# mientras la tecla abría el buscador. El auto-test no podía verlo, porque `^r`
# SÍ estaba atado; solo que a otra cosa. En NORMAL se busca con `/`, que es lo
# que dice la propia tira.
(( ${+widgets[fzf-history-widget]} )) && bindkey -M viins '^r' fzf-history-widget

# Y en NORMAL, `^r` se le QUITA a fzf para devolvérselo a `redo`, la pareja de
# `u`. No basta con no atarlo aquí: fzf lo ata él mismo en vicmd (línea 115 de
# su key-bindings.zsh), así que hay que recuperarlo a la fuerza. En NORMAL se
# busca con `/`, que es lo que dice la tira.
bindkey -M vicmd '^r' redo
(( ${+widgets[fzf-file-widget]} ))    && bindkey -M viins '^t' fzf-file-widget
(( ${+widgets[fzf-cd-widget]} ))      && bindkey -M viins '\ec' fzf-cd-widget

# En el menú de completado, la capa 20 ya puso Shift+Tab y Esc. Aquí solo se
# añade moverse con hjkl, que es lo que la mano espera después de todo esto.
bindkey -M menuselect 'h' vi-backward-char
bindkey -M menuselect 'j' vi-down-line-or-history
bindkey -M menuselect 'k' vi-up-line-or-history
bindkey -M menuselect 'l' vi-forward-char

# ── claude-keys: el interruptor y la chuleta ──────────────────────────
_claude_keys_write() {
  local want=$1 dir
  CC_KEYS_ON=$([[ $want == on ]] && print 1 || print 0)
  dir=${CC_KEYS_STATE:h}
  [[ -d $dir ]] || mkdir -p -- "$dir" 2>/dev/null
  print -r -- "$want" >| "$CC_KEYS_STATE" 2>/dev/null
  # El gemelo de Windows. Si no hay /mnt/c esto no hace nada y no se queja: una
  # WSL sin Windows delante, o un Linux a secas, es un caso válido.
  local win="$(_claude_keys_winstate)"
  [[ -n $win && -d ${win:h} ]] && print -r -- "$want" >| "$win" 2>/dev/null
  return 0
}

_claude_keys_card() {
  local -a surfaces=(shell windows)
  local surface mode var bv rv badge role
  local -i i

  printf '\e[%sm atajos · claude cli\e[0m   \e[%sm%s\e[0m\n' \
    "$CC_TEAL" "$CC_GREY" "tira $([[ $CC_KEYS_ON == 1 ]] && print on || print off)"

  for surface in $surfaces; do
    local -a modes=( "${(@P)${:-CC_KEYS_${(U)surface}_MODES}}" )
    local title="zsh"
    [[ $surface == windows ]] && title="windows · ${CC_KEYS_HOTKEY}"
    printf '\n \e[%sm%s\e[0m\n' "$CC_WHITE" "$title"

    for mode in $modes; do
      var="CC_KEYS_${(U)surface}_${(U)mode}"
      bv="${var}_BADGE"; rv="${var}_ROLE"
      badge="${(P)bv}"; role="${(P)rv}"
      local -a pairs=( "${(@P)var}" )
      (( $#pairs >= 2 )) || continue
      printf '   \e[38;2;%d;%d;%dm%s\e[0m\n' \
        $(( 16#${role[2,3]} )) $(( 16#${role[4,5]} )) $(( 16#${role[6,7]} )) "$badge"
      for (( i = 1; i <= $#pairs; i += 2 )); do
        printf '     \e[%sm%-12s\e[0m \e[%sm%s\e[0m\n' \
          "$CC_GREEN" "${pairs[i]}" "$CC_GREY" "${pairs[i+1]}"
      done
    done
  done
  printf '\n \e[%sm claude-keys off\e[0m \e[%sm apaga la tira y el OSD de Windows\e[0m\n' \
    "$CC_AMBER" "$CC_GREY"
}

claude-keys() {
  case ${1:-card} in
    on|off)
      _claude_keys_write "$1"
      printf '\e[%sm·\e[0m tira %s\n' "$CC_TEAL" "$1" ;;
    toggle)
      (( CC_KEYS_ON )) && claude-keys off || claude-keys on ;;
    status)
      printf '\e[%sm·\e[0m tira %s, modo %s, %s\n' "$CC_TEAL" \
        "$([[ $CC_KEYS_ON == 1 ]] && print on || print off)" \
        "$_claude_keys_mode" "$CC_KEYS_STATE" ;;
    card)
      _claude_keys_card ;;
    *)
      print -u2 "uso: claude-keys [card|on|off|toggle|status]"; return 2 ;;
  esac
}

# Ctrl+G para encender y apagar sin soltar el teclado. En vi no significa nada,
# y su `list-expand` de zsh lo cubre Tab de sobra.
_claude_keys_toggle_widget() {
  (( CC_KEYS_ON )) && _claude_keys_write off || _claude_keys_write on
  _claude_keys_render
  zle reset-prompt
}
zle -N _claude_keys_toggle_widget
bindkey -M viins '^g' _claude_keys_toggle_widget
bindkey -M vicmd '^g' _claude_keys_toggle_widget
