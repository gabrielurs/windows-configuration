#!/usr/bin/env bash
# install.sh — instala el tema "Claude CLI" en zsh y, si hay WSL, en Windows.
#
#   ./install.sh              todo lo que detecte
#   ./install.sh --shell      solo zsh
#   ./install.sh --windows    solo Windows Terminal / VS Code / PowerShell / acento
#   ./install.sh --dry-run    enseña qué haría y no toca nada
#   ./install.sh --uninstall  deshace lo que instaló
#
# Idempotente: relanzarlo deja el mismo resultado.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAMP="$(date +%Y%m%d%H%M%S)"
ZSH_DIR="${ZSH:-$HOME/.oh-my-zsh}"
CUSTOM="${ZSH_CUSTOM:-$ZSH_DIR/custom}"
ZSHRC="${ZDOTDIR:-$HOME}/.zshrc"

DO_SHELL=0; DO_WIN=0; DRY=0; UNINSTALL=0
[[ $# -eq 0 ]] && { DO_SHELL=1; DO_WIN=1; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --shell)     DO_SHELL=1 ;;
    --windows)   DO_WIN=1 ;;
    --all)       DO_SHELL=1; DO_WIN=1 ;;
    --dry-run)   DRY=1; [[ $DO_SHELL -eq 0 && $DO_WIN -eq 0 ]] && { DO_SHELL=1; DO_WIN=1; } ;;
    --uninstall) UNINSTALL=1; [[ $DO_SHELL -eq 0 && $DO_WIN -eq 0 ]] && { DO_SHELL=1; DO_WIN=1; } ;;
    -h|--help)   sed -n '2,12p' "$0" | sed 's/^# \?//'; exit 0 ;;
    *)           echo "opción desconocida: $1" >&2; exit 2 ;;
  esac
  shift
done

TEAL=$'\e[38;2;77;214;193m'; GREY=$'\e[38;2;107;118;131m'
RED=$'\e[38;2;242;119;122m';  AMB=$'\e[38;2;232;196;106m'; OFF=$'\e[0m'
say()  { printf '%s·%s %s\n' "$TEAL" "$OFF" "$*"; }
step() { printf '  %s%s%s\n' "$GREY" "$*" "$OFF"; }
warn() { printf '  %s! %s%s\n' "$AMB" "$*" "$OFF"; }
die()  { printf '%s✗ %s%s\n' "$RED" "$*" "$OFF" >&2; exit 1; }
run()  { if [[ $DRY -eq 1 ]]; then step "[dry] $*"; else "$@"; fi; }

backup() { # backup <fichero>
  [[ -f "$1" ]] || return 0
  step "backup → $(basename "$1").bak-claude-$STAMP"
  [[ $DRY -eq 1 ]] || cp -p "$1" "$1.bak-claude-$STAMP"
}

# ── shell ─────────────────────────────────────────────────────────────
install_shell() {
  command -v zsh >/dev/null || die "no hay zsh instalado"
  local ver; ver="$(zsh -c 'echo $ZSH_VERSION')"
  [[ "${ver%%.*}" -gt 5 || ( "${ver%%.*}" -eq 5 && "${ver#*.}" != "${ver}" && "$(echo "$ver" | cut -d. -f2)" -ge 7 ) ]] \
    || warn "zsh $ver: los colores hex en el prompt necesitan zsh >= 5.7"
  [[ -d "$ZSH_DIR" ]] || die "no encuentro oh-my-zsh en $ZSH_DIR"

  say "plugins de resaltado"
  local p
  for p in zsh-syntax-highlighting zsh-autosuggestions; do
    if [[ -d "$CUSTOM/plugins/$p" ]]; then
      step "$p ya está, actualizando"
      run git -C "$CUSTOM/plugins/$p" pull --quiet --ff-only || warn "no pude actualizar $p"
    else
      step "clonando $p"
      run git clone --depth=1 --quiet "https://github.com/zsh-users/$p.git" "$CUSTOM/plugins/$p"
    fi
  done

  say "ficheros del tema"
  run mkdir -p "$CUSTOM/themes"
  step "claude-00-palette.zsh (generado desde palette.json)"
  if [[ $DRY -eq 0 ]]; then
    python3 "$ROOT/lib/render.py" palette.zsh > "$CUSTOM/claude-00-palette.zsh"
  fi
  step "claude-10-colors.zsh"
  run cp "$ROOT/shell/claude-10-colors.zsh" "$CUSTOM/claude-10-colors.zsh"
  step "claude.zsh-theme"
  run cp "$ROOT/shell/claude.zsh-theme" "$CUSTOM/themes/claude.zsh-theme"
  # restos de instalaciones antiguas
  [[ -f "$CUSTOM/claude-colors.zsh" ]] && { step "retiro el claude-colors.zsh viejo"; run rm -f "$CUSTOM/claude-colors.zsh"; }

  say ".zshrc"
  backup "$ZSHRC"
  if [[ $DRY -eq 0 ]]; then
    ZSHRC="$ZSHRC" python3 "$ROOT/lib/patch_zshrc.py"
  else
    step "[dry] ZSH_THEME=claude + plugins zsh-autosuggestions/zsh-syntax-highlighting"
  fi
}

uninstall_shell() {
  say "retirando ficheros del tema"
  local f
  for f in "$CUSTOM/claude-00-palette.zsh" "$CUSTOM/claude-10-colors.zsh" \
           "$CUSTOM/claude-colors.zsh" "$CUSTOM/themes/claude.zsh-theme"; do
    [[ -e "$f" ]] && { step "rm $(basename "$f")"; run rm -f "$f"; }
  done
  warn "el .zshrc no se toca: revisa ZSH_THEME y plugins, o restaura un .bak-claude-*"
  warn "los plugins clonados se quedan en $CUSTOM/plugins (bórralos a mano si quieres)"
}

# ── main ──────────────────────────────────────────────────────────────
printf '%stema Claude CLI%s  %s%s%s\n\n' "$TEAL" "$OFF" "$GREY" \
  "$([[ $UNINSTALL -eq 1 ]] && echo desinstalar || echo instalar)$([[ $DRY -eq 1 ]] && echo ' (dry-run)')" "$OFF"

if [[ $DO_SHELL -eq 1 ]]; then
  if [[ $UNINSTALL -eq 1 ]]; then uninstall_shell; else install_shell; fi
  echo
fi

if [[ $DO_WIN -eq 1 ]]; then
  if [[ -d /mnt/c ]]; then
    args=()
    [[ $DRY -eq 1 ]] && args+=(--dry-run)
    [[ $UNINSTALL -eq 1 ]] && args+=(--uninstall)
    python3 "$ROOT/lib/apply_windows.py" "${args[@]}"
  else
    warn "no veo /mnt/c: salto la parte de Windows"
  fi
  echo
fi

if [[ $UNINSTALL -eq 0 && $DRY -eq 0 && $DO_SHELL -eq 1 ]]; then
  printf '%sabre una shell nueva o lanza:%s exec zsh\n' "$GREY" "$OFF"
fi
