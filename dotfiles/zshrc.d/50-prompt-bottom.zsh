# Prompt anclado abajo, para pantallas verticales: al arrancar la shell y al
# limpiar, el cursor baja al final en vez de quedarse arriba del todo.
# Ctrl+L limpia también el scrollback (\e[3J), no solo la pantalla visible.
if [[ -o interactive ]]; then
  _ctt_pin_bottom() {
    local rows=${LINES:-$(tput lines 2>/dev/null || echo 24)}
    printf '\e[%d;1H' "$rows"
  }
  _ctt_clear_bottom() {
    local rows=${LINES:-$(tput lines 2>/dev/null || echo 24)}
    printf '\e[2J\e[3J\e[%d;1H' "$rows"
    zle .reset-prompt
  }
  zle -N _ctt_clear_bottom
  bindkey '^L' _ctt_clear_bottom
  _ctt_pin_bottom
fi
