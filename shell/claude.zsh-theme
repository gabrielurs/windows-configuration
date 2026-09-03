# claude.zsh-theme — prompt de una línea con la paleta "Claude CLI".
#
#   ~/proyectos/algo on main + ~ ?  ❯ comando          ✗1  4.2s
#   └ ruta teal      └ rama azul    └ teal, rojo si falló  └ código + duración
#
# Depende de claude-00-palette.zsh (CC_HEX_*). Requiere zsh >= 5.7 y truecolor.

# ── git ───────────────────────────────────────────────────────────────
ZSH_THEME_GIT_PROMPT_PREFIX="%F{$CC_HEX_GREY} on %F{$CC_HEX_BLUE}"
ZSH_THEME_GIT_PROMPT_SUFFIX="%f"
ZSH_THEME_GIT_PROMPT_DIRTY=""
ZSH_THEME_GIT_PROMPT_CLEAN=""

ZSH_THEME_GIT_PROMPT_ADDED="%F{$CC_HEX_GREEN} +"
ZSH_THEME_GIT_PROMPT_MODIFIED="%F{$CC_HEX_AMBER} ~"
ZSH_THEME_GIT_PROMPT_DELETED="%F{$CC_HEX_RED} -"
ZSH_THEME_GIT_PROMPT_RENAMED="%F{$CC_HEX_PURPLE} »"
ZSH_THEME_GIT_PROMPT_UNMERGED="%F{$CC_HEX_RED} ="
ZSH_THEME_GIT_PROMPT_UNTRACKED="%F{$CC_HEX_GREY} ?"
ZSH_THEME_GIT_PROMPT_STASHED="%F{$CC_HEX_PURPLE} \$"
ZSH_THEME_GIT_PROMPT_AHEAD="%F{$CC_HEX_GREEN} ↑"
ZSH_THEME_GIT_PROMPT_BEHIND="%F{$CC_HEX_AMBER} ↓"
ZSH_THEME_GIT_PROMPT_DIVERGED="%F{$CC_HEX_RED} ↕"

# ── cronómetro del último comando (solo a partir de 2s) ───────────────
zmodload zsh/datetime 2>/dev/null
_claude_timer_start() { _claude_timer=$EPOCHREALTIME }
_claude_timer_stop() {
  _claude_elapsed=""
  [[ -z $_claude_timer ]] && return
  local d=$(( EPOCHREALTIME - _claude_timer ))
  unset _claude_timer
  (( d < 2 )) && return
  if   (( d < 60 ));   then _claude_elapsed=$(printf '%.1fs' $d)
  elif (( d < 3600 )); then _claude_elapsed=$(printf '%dm%02ds' $((d/60)) $((d%60)))
  else                      _claude_elapsed=$(printf '%dh%02dm' $((d/3600)) $((d%3600/60)))
  fi
}
autoload -Uz add-zsh-hook
add-zsh-hook preexec _claude_timer_start
add-zsh-hook precmd  _claude_timer_stop

# ── el repo que ve la barra de tareas de Windows ──────────────────────
# `lib/gitbranch.py` sirve este fichero por loopback y el reloj de la barra
# pinta su rama. Se apunta la RUTA, no la rama: así un `git checkout` se refleja
# sin que la shell tenga que enterarse.
#
# El fork de git solo ocurre al cambiar de directorio; el resto de prompts es un
# write de cuarenta bytes. Si no hay Windows delante, esto es un fichero que
# nadie lee y ya está.
_claude_repo_file="${XDG_STATE_HOME:-$HOME/.local/state}/claude-terminal-theme/repo"
_claude_repo_track() {
  if [[ $PWD != $_claude_repo_pwd ]]; then
    _claude_repo_pwd=$PWD
    _claude_repo=$(command git rev-parse --show-toplevel 2>/dev/null) || _claude_repo=""
  fi
  [[ -d ${_claude_repo_file:h} ]] || mkdir -p -- "${_claude_repo_file:h}" 2>/dev/null || return
  print -r -- "$_claude_repo" >| "$_claude_repo_file" 2>/dev/null
}
add-zsh-hook precmd _claude_repo_track

# ── contexto: venv, ssh, root ─────────────────────────────────────────
_claude_context() {
  local out=""
  [[ -n $VIRTUAL_ENV ]] && out+="%F{$CC_HEX_PURPLE}(${VIRTUAL_ENV:t})%f "
  [[ -n $CONDA_DEFAULT_ENV ]] && out+="%F{$CC_HEX_PURPLE}(${CONDA_DEFAULT_ENV})%f "
  [[ -n $SSH_CONNECTION ]] && out+="%F{$CC_HEX_AMBER}%n%F{$CC_HEX_GREY}@%F{$CC_HEX_AMBER}%m%f "
  (( EUID == 0 )) && out+="%F{$CC_HEX_RED}root%f "
  print -rn -- "$out"
}

# ── prompt ────────────────────────────────────────────────────────────
setopt PROMPT_SUBST

# %(5~|…) → a partir de 5 niveles muestra  ~/…/tres/ultimos/tramos
CLAUDE_CWD="%(5~|%-1~/%F{$CC_HEX_GREY}…%F{$CC_HEX_TEAL}/%3~|%~)"

# La tira de atajos, si claude-40-keys.zsh está puesto. Es una VARIABLE y no un
# $(…) a propósito: la sustitución de comandos se come el salto de línea final,
# que es justo lo que separa la tira del prompt, y encima forkearía en cada
# redibujado. Si la capa 40 no está, el parámetro no existe, expande a vacío y
# este prompt es exactamente el de antes.
PROMPT='${_claude_keys_bar}$(_claude_context)%F{'"$CC_HEX_TEAL"'}'"$CLAUDE_CWD"'%f$(git_prompt_info)$(git_prompt_status)%f %(?.%F{'"$CC_HEX_TEAL"'}.%F{'"$CC_HEX_RED"'})❯%f '
RPROMPT='%(?..%F{'"$CC_HEX_RED"'}✗%?%f )%F{'"$CC_HEX_AMBER"'}${_claude_elapsed}%f'
