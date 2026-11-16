# claude-05-tmux.zsh — cada pestaña de Windows Terminal entra sola en tmux.
#
# Va en el 05 a propósito: después de la paleta (00), que trae el interruptor, y
# ANTES del resto de capas, que no hace falta cargar en una shell que va a ceder
# el sitio a tmux un instante después.
#
# Una sesión por pestaña, y muere con ella (`destroy-unattached`): cerrar la
# pestaña acaba con lo que corría, igual que sin tmux, y no quedan sesiones
# sueltas comiendo memoria en WSL. Decidido así el 2026-11-16; el coste conocido
# es que un equipo de echo lanzado con `orq up` desde la pestaña muere con ella.
#
# Dónde NO arranca, y cada guarda tiene su porqué:
#   · fuera de Windows Terminal ($WT_SESSION): ni VS Code ni ssh ni una consola
#   · ya dentro de tmux ($TMUX): se anidaría sin fin
#   · bajo Claude Code ($CLAUDECODE): sus shells son de usar y tirar
#   · shells no interactivas: scripts, `zsh -c`
#
# En caliente: `claude-tmux off` y la siguiente pestaña abre zsh a secas.

typeset -g CC_TMUX_STATE="${XDG_STATE_HOME:-$HOME/.local/state}/claude-terminal-theme/tmux"

claude-tmux() {
  case ${1:-status} in
    on|off)
      mkdir -p "${CC_TMUX_STATE:h}" && print -r -- "$1" >| "$CC_TMUX_STATE"
      print "· tmux al abrir pestaña: $1 (desde la siguiente)" ;;
    status)
      print "· tmux al abrir pestaña: $(_claude_tmux_wanted && print on || print off)${TMUX:+, y ahora mismo estás dentro}" ;;
    *) print -u2 "uso: claude-tmux [on|off|status]"; return 2 ;;
  esac
}

# El fichero de estado manda sobre la paleta; sin fichero, lo que diga la paleta.
_claude_tmux_wanted() {
  local st=""
  [[ -r $CC_TMUX_STATE ]] && st=${"$(<$CC_TMUX_STATE)"//[[:space:]]/}
  case $st in
    on)  return 0 ;;
    off) return 1 ;;
    *)   (( ${CC_TMUX_AUTO:-0} )) ;;
  esac
}

if [[ -o interactive && -n $WT_SESSION && -z $TMUX && -z $CLAUDECODE ]] \
   && (( $+commands[tmux] )) && _claude_tmux_wanted; then
  # `&& exit` y no `exec`: si tmux no llega a arrancar —un tmux.conf roto, el
  # servidor colgado— devuelve error y te quedas en esta shell, que sigue
  # cargando el resto de capas. Con exec, la pestaña se cerraría en tu cara.
  # Con nombre y no el número que pone tmux: «4» como nombre de sesión se
  # confunde con el índice de ventana 4 en cualquier `-t` (medido: `new-window
  # -t 4` creó la ventana 4, no una ventana en la sesión 4).
  tmux new-session -s "wt-$$" \; set-option destroy-unattached on && exit
  print -u2 "· tmux no arrancó (código $?); sigo en zsh. \`claude-tmux off\` lo desactiva."
fi
