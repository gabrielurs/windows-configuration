# lib/deps.sh — detecta e instala lo que falte. Se sourcea desde install.sh.
#
# Filosofía: enseñar la lista completa, pedir UNA confirmación, y tirar.
# Nada de ir preguntando cosa por cosa ni de instalar a escondidas.

DEPS_MISSING=()      # descripciones para enseñar
DEPS_PKGS=()         # paquetes del gestor del sistema
DEPS_ACTIONS=()      # funciones a ejecutar después

_pm() {
  for pm in apt-get dnf pacman zypper apk; do
    command -v $pm >/dev/null && { echo $pm; return; }
  done
}

_pm_install() { # _pm_install <paquete>...
  local pm; pm="$(_pm)"
  case "$pm" in
    apt-get) sudo apt-get update -qq && sudo apt-get install -y "$@" ;;
    dnf)     sudo dnf install -y "$@" ;;
    pacman)  sudo pacman -Sy --noconfirm "$@" ;;
    zypper)  sudo zypper install -y "$@" ;;
    apk)     sudo apk add "$@" ;;
    *)       return 1 ;;
  esac
}

_omz_install() {
  step "instalando oh-my-zsh"
  RUNZSH=no CHSH=no KEEP_ZSHRC=yes sh -c \
    "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
}

_windhawk_install() {
  step "instalando Windhawk con winget (puede pedir UAC)"
  winget.exe install --id RamenSoftware.Windhawk --source winget \
    --accept-package-agreements --accept-source-agreements 2>&1 | tr -d '\r' | tail -3
}

_chsh_zsh() {
  step "poniendo zsh como shell por defecto"
  chsh -s "$(command -v zsh)" || warn "chsh falló; hazlo a mano: chsh -s $(command -v zsh)"
}

# ── detección ─────────────────────────────────────────────────────────
deps_scan() {
  DEPS_MISSING=(); DEPS_PKGS=(); DEPS_ACTIONS=()

  command -v git >/dev/null     || { DEPS_MISSING+=("git — para clonar los plugins de zsh"); DEPS_PKGS+=(git); }
  command -v python3 >/dev/null || { DEPS_MISSING+=("python3 — lo usa el instalador"); DEPS_PKGS+=(python3); }
  command -v zsh >/dev/null     || { DEPS_MISSING+=("zsh — la shell del tema"); DEPS_PKGS+=(zsh); }

  [[ -d "${ZSH:-$HOME/.oh-my-zsh}" ]] || {
    DEPS_MISSING+=("oh-my-zsh — el tema es un tema suyo")
    DEPS_ACTIONS+=(_omz_install)
  }

  if command -v zsh >/dev/null && [[ "${SHELL##*/}" != "zsh" ]]; then
    DEPS_MISSING+=("zsh como shell por defecto (ahora: ${SHELL##*/})")
    DEPS_ACTIONS+=(_chsh_zsh)
  fi

  # Windows: solo si estamos en WSL y el usuario quiere el dock
  if [[ -d /mnt/c && $WANT_DOCK -eq 1 ]]; then
    if [[ ! -d "/mnt/c/Program Files/Windhawk" ]] && command -v winget.exe >/dev/null; then
      DEPS_MISSING+=("Windhawk — hace falta para el dock flotante")
      DEPS_ACTIONS+=(_windhawk_install)
    fi
  fi
}

# ── instalación ───────────────────────────────────────────────────────
deps_install() {
  deps_scan
  if [[ ${#DEPS_MISSING[@]} -eq 0 ]]; then
    say "dependencias: todo en su sitio"
    return 0
  fi

  say "falta esto:"
  local d
  for d in "${DEPS_MISSING[@]}"; do step "$d"; done
  if [[ ${#DEPS_PKGS[@]} -gt 0 ]]; then
    local pm; pm="$(_pm)"
    [[ -z "$pm" ]] && { warn "no reconozco el gestor de paquetes; instálalos a mano"; return 1; }
    printf '  %svia %s, que pedirá tu contraseña de sudo%s\n' "$GREY" "$pm" "$OFF"
  fi

  if [[ $ASSUME_YES -eq 0 ]]; then
    printf '\n  %s¿instalo?%s [s/N] ' "$AMB" "$OFF"
    local ans; read -r ans </dev/tty || ans=n
    [[ "$ans" =~ ^[sSyY]$ ]] || { warn "no instalo nada; continúo con lo que haya"; return 1; }
  fi
  echo

  [[ ${#DEPS_PKGS[@]} -gt 0 ]] && { step "instalando: ${DEPS_PKGS[*]}"; _pm_install "${DEPS_PKGS[@]}" || warn "el gestor de paquetes falló"; }
  local fn
  for fn in "${DEPS_ACTIONS[@]}"; do "$fn"; done
  echo
}
