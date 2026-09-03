#!/usr/bin/env bash
# install.sh — instala el tema "Claude CLI" en zsh y, si hay WSL, en Windows.
#
#   ./install.sh                todo lo que detecte
#   ./install.sh --shell        solo zsh
#   ./install.sh --windows      solo la parte de Windows
#   ./install.sh --dotfiles     además, mi capa de dotfiles (ver dotfiles/README.md)
#   ./install.sh --no-dock      salta Windhawk (sin dock flotante)
#   ./install.sh --no-deps      no instales dependencias que falten
#   ./install.sh --yes          no preguntes nada
#   ./install.sh --dry-run      enseña qué haría y no toca nada
#   ./install.sh --uninstall    devuelve todo al estado del snapshot original
#
# Idempotente: relanzarlo deja el mismo resultado.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAMP="$(date +%Y%m%d%H%M%S)"
ZSH_DIR="${ZSH:-$HOME/.oh-my-zsh}"
CUSTOM="${ZSH_CUSTOM:-$ZSH_DIR/custom}"
ZSHRC="${ZDOTDIR:-$HOME}/.zshrc"
DOTDIR="$HOME/.config/claude-terminal-theme/zshrc.d"
MARK_BEGIN="# >>> claude-terminal-theme dotfiles >>>"
MARK_END="# <<< claude-terminal-theme dotfiles <<<"

TEAL=$'\e[38;2;77;214;193m'; GREY=$'\e[38;2;107;118;131m'
RED=$'\e[38;2;242;119;122m';  AMB=$'\e[38;2;232;196;106m'; OFF=$'\e[0m'
say()  { printf '%s·%s %s\n' "$TEAL" "$OFF" "$*"; }
step() { printf '  %s%s%s\n' "$GREY" "$*" "$OFF"; }
warn() { printf '  %s! %s%s\n' "$AMB" "$*" "$OFF"; }
die()  { printf '%s✗ %s%s\n' "$RED" "$*" "$OFF" >&2; exit 1; }

DO_SHELL=0; DO_WIN=0; DRY=0; UNINSTALL=0
DO_DOTFILES=0; WANT_DOCK=1; DO_DEPS=1; ASSUME_YES=0
EXPLICIT=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --shell)     DO_SHELL=1; EXPLICIT=1 ;;
    --windows)   DO_WIN=1;   EXPLICIT=1 ;;
    --all)       DO_SHELL=1; DO_WIN=1; EXPLICIT=1 ;;
    --dotfiles)  DO_DOTFILES=1 ;;
    --no-dock)   WANT_DOCK=0 ;;
    --no-deps)   DO_DEPS=0 ;;
    --yes|-y)    ASSUME_YES=1 ;;
    --dry-run)   DRY=1 ;;
    --uninstall) UNINSTALL=1 ;;
    -h|--help)   awk 'NR>1 && /^#/ {sub(/^# ?/,""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
    *)           die "opción desconocida: $1" ;;
  esac
  shift
done
[[ $EXPLICIT -eq 0 ]] && { DO_SHELL=1; DO_WIN=1; }
export WANT_DOCK ASSUME_YES

run() { if [[ $DRY -eq 1 ]]; then step "[dry] $*"; else "$@"; fi; }
backup() {
  [[ -f "$1" ]] || return 0
  step "backup → $(basename "$1").bak-claude-$STAMP"
  [[ $DRY -eq 1 ]] || cp -p "$1" "$1.bak-claude-$STAMP"
}
snap_files() { [[ $DRY -eq 1 ]] || python3 "$ROOT/lib/snap.py" "$@"; }

# shellcheck source=lib/deps.sh
source "$ROOT/lib/deps.sh"

# ── shell ─────────────────────────────────────────────────────────────
install_shell() {
  command -v zsh >/dev/null || die "sigue sin haber zsh; instálalo y repite"
  [[ -d "$ZSH_DIR" ]] || die "sigue sin haber oh-my-zsh en $ZSH_DIR"
  local ver; ver="$(zsh -c 'echo $ZSH_VERSION')"
  local maj=${ver%%.*} min; min=$(echo "$ver" | cut -d. -f2)
  (( maj > 5 || (maj == 5 && min >= 7) )) || warn "zsh $ver: los hex del prompt piden zsh >= 5.7"

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
  snap_files "$CUSTOM/claude-00-palette.zsh" "$CUSTOM/claude-10-colors.zsh" \
             "$CUSTOM/claude-20-shell.zsh" "$CUSTOM/claude-30-tools.zsh" \
             "$CUSTOM/themes/claude.zsh-theme" "$ZSHRC"
  step "claude-00-palette.zsh (generado desde palette.json)"
  [[ $DRY -eq 1 ]] || python3 "$ROOT/lib/render.py" palette.zsh > "$CUSTOM/claude-00-palette.zsh"
  # El número del nombre es el orden de carga: oh-my-zsh sourcea $ZSH_CUSTOM/*.zsh
  # alfabéticamente, así que 30 ve lo que definieron 00, 10 y 20.
  local layer
  for layer in claude-10-colors claude-20-shell claude-30-tools; do
    step "$layer.zsh"
    run cp "$ROOT/shell/$layer.zsh" "$CUSTOM/$layer.zsh"
  done
  step "claude.zsh-theme"
  run cp "$ROOT/shell/claude.zsh-theme" "$CUSTOM/themes/claude.zsh-theme"
  [[ -f "$CUSTOM/claude-colors.zsh" ]] && { step "retiro el claude-colors.zsh viejo"; run rm -f "$CUSTOM/claude-colors.zsh"; }

  say ".zshrc"
  backup "$ZSHRC"
  if [[ $DRY -eq 0 ]]; then
    ZSHRC="$ZSHRC" python3 "$ROOT/lib/patch_zshrc.py"
  else
    step "[dry] ZSH_THEME=claude + plugins de resaltado + COLORTERM"
  fi
}

# ── capa opcional de dotfiles ─────────────────────────────────────────
install_dotfiles() {
  say "capa de dotfiles"
  snap_files "$ZSHRC"
  run mkdir -p "$DOTDIR"
  local f
  for f in "$ROOT"/dotfiles/zshrc.d/*.zsh; do
    step "$(basename "$f")"
    snap_files "$DOTDIR/$(basename "$f")"
    run cp "$f" "$DOTDIR/$(basename "$f")"
  done
  if grep -qF "$MARK_BEGIN" "$ZSHRC" 2>/dev/null; then
    step "el bloque del .zshrc ya estaba"
  else
    step "añadiendo el bloque al .zshrc"
    if [[ $DRY -eq 0 ]]; then
      {
        printf '\n%s\n' "$MARK_BEGIN"
        printf 'for _f in %s/*.zsh(N); do source $_f; done\nunset _f\n' "${DOTDIR/#$HOME/\$HOME}"
        printf '%s\n' "$MARK_END"
      } >> "$ZSHRC"
    fi
  fi
}

# ── la rama de git para la barra de tareas ────────────────────────────
# Vive en WSL —los repos están aquí— y el reloj de Windows la lee por loopback.
# Sin systemd no hay dónde colgarlo: se avisa y se sigue, que el resto del tema
# no depende de esto.
install_gitbranch() {
  local unit_dir="$HOME/.config/systemd/user"
  local unit="$unit_dir/claude-gitbranch.service"

  say "rama de git en la barra"
  if ! command -v systemctl >/dev/null 2>&1 || [[ $(ps -p 1 -o comm= 2>/dev/null) != systemd ]]; then
    warn "sin systemd en esta WSL: lánzalo tú con  python3 $ROOT/lib/gitbranch.py &"
    warn "(o pon systemd=true en /etc/wsl.conf y reinicia con wsl --shutdown)"
    return 0
  fi

  run mkdir -p "$unit_dir"
  snap_files "$unit"
  if [[ $DRY -eq 0 ]]; then
    sed "s|@ROOT@|$ROOT|g" "$ROOT/systemd/claude-gitbranch.service.tmpl" > "$unit"
    systemctl --user daemon-reload
    systemctl --user enable --now claude-gitbranch.service >/dev/null 2>&1
    if systemctl --user is-active --quiet claude-gitbranch.service; then
      step "servicio activo en 127.0.0.1:$(python3 -c 'import json;print(json.load(open("'"$ROOT"'/palette.json"))["windowsDesktop"]["gitBranch"]["port"])')"
    else
      warn "el servicio no arrancó: systemctl --user status claude-gitbranch"
    fi
  else
    step "[dry] unit en $unit + enable --now"
  fi
}

# ── main ──────────────────────────────────────────────────────────────
printf '%stema Claude CLI%s  %s%s%s\n\n' "$TEAL" "$OFF" "$GREY" \
  "$([[ $UNINSTALL -eq 1 ]] && echo desinstalar || echo instalar)$([[ $DRY -eq 1 ]] && echo ' (dry-run)')" "$OFF"

if [[ $UNINSTALL -eq 1 ]]; then
  args=(); [[ $DRY -eq 1 ]] && args+=(--dry-run)
  python3 "$ROOT/lib/do_uninstall.py" "${args[@]}"
  echo
  warn "los plugins clonados se quedan en $CUSTOM/plugins (bórralos si quieres)"
  exit 0
fi

if [[ $DO_DEPS -eq 1 && $DRY -eq 0 ]]; then
  deps_install || true
elif [[ $DO_DEPS -eq 1 ]]; then
  deps_scan
  if [[ ${#DEPS_MISSING[@]} -gt 0 ]]; then
    say "falta esto (se instalaría):"
    for d in "${DEPS_MISSING[@]}"; do step "$d"; done
    echo
  fi
fi

if [[ $DO_SHELL -eq 1 ]]; then
  install_shell
  [[ $DO_DOTFILES -eq 1 ]] && { echo; install_dotfiles; }
  echo
fi

if [[ $DO_WIN -eq 1 ]]; then
  if [[ -d /mnt/c ]]; then
    args=(); [[ $DRY -eq 1 ]] && args+=(--dry-run)
    [[ $WANT_DOCK -eq 0 ]] && args+=(--skip windhawk)
    python3 "$ROOT/lib/apply_windows.py" "${args[@]}"
    [[ $WANT_DOCK -eq 1 ]] && { echo; install_gitbranch; }
  else
    warn "no veo /mnt/c: esto no es WSL, salto la parte de Windows"
  fi
  echo
fi

[[ $DRY -eq 0 && $DO_SHELL -eq 1 ]] && \
  printf '%sabre una shell nueva o lanza:%s exec zsh\n' "$GREY" "$OFF"
exit 0
