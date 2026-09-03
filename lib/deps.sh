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

_lazygit_install() {
  # No está en el apt de Ubuntu 24.04, así que se baja el binario de su release.
  # Si esto falla no pasa nada grave: es la única herramienta del lote que no
  # tiene paquete, y el resto del tema no la usa para nada.
  step "lazygit desde su release de GitHub"
  local ver url tmp
  ver="$(curl -fsSL https://api.github.com/repos/jesseduffield/lazygit/releases/latest \
        | grep -Po '"tag_name": *"v\K[^"]*')" || { warn "no pude preguntar la versión de lazygit"; return 1; }
  [[ -n "$ver" ]] || { warn "la API de GitHub no devolvió versión de lazygit"; return 1; }
  url="https://github.com/jesseduffield/lazygit/releases/download/v${ver}/lazygit_${ver}_Linux_x86_64.tar.gz"
  tmp="$(mktemp -d)"
  if curl -fsSL "$url" | tar -xz -C "$tmp" lazygit 2>/dev/null; then
    install -Dm755 "$tmp/lazygit" "$HOME/.local/bin/lazygit" && step "lazygit $ver en ~/.local/bin"
  else
    warn "no pude bajar lazygit $ver; sáltatelo"
  fi
  rm -rf "$tmp"
}

_flow_install() {
  step "instalando Flow Launcher con winget (el buscador flotante)"
  winget.exe install --id Flow-Launcher.Flow-Launcher --source winget \
    --accept-package-agreements --accept-source-agreements --silent 2>&1 | tr -d '\r' | tail -3
}

_chsh_zsh() {
  step "poniendo zsh como shell por defecto"
  chsh -s "$(command -v zsh)" || warn "chsh falló; hazlo a mano: chsh -s $(command -v zsh)"
}

_win_home() {
  # %USERPROFILE% visto desde WSL, sin cablear el nombre de usuario
  local w
  w=$(cmd.exe /c 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r')
  [[ -n $w ]] && wslpath -u "$w" 2>/dev/null
}

# ── detección ─────────────────────────────────────────────────────────
deps_scan() {
  DEPS_MISSING=(); DEPS_PKGS=(); DEPS_ACTIONS=()

  command -v git >/dev/null     || { DEPS_MISSING+=("git — para clonar los plugins de zsh"); DEPS_PKGS+=(git); }
  command -v python3 >/dev/null || { DEPS_MISSING+=("python3 — lo usa el instalador"); DEPS_PKGS+=(python3); }
  command -v zsh >/dev/null     || { DEPS_MISSING+=("zsh — la shell del tema"); DEPS_PKGS+=(zsh); }
  command -v fc-list >/dev/null || { DEPS_MISSING+=("fontconfig — para elegir una fuente con los glifos"); DEPS_PKGS+=(fontconfig); }
  python3 -c "import PIL" 2>/dev/null || {
    DEPS_MISSING+=("python3-pil — genera los iconos de los anclados")
    DEPS_PKGS+=(python3-pil fonts-dejavu-core); }

  # ── herramientas del terminal ───────────────────────────────────────
  # Opcionales de verdad: shell/claude-30-tools.zsh envuelve cada integración
  # en un `command -v`, así que en una máquina sin ellas el shell va igual. Se
  # instalan porque una máquina nueva las quiere, no porque el tema dependa de
  # ellas. Con CTT_TOOLS=0 no se tocan.
  #
  # «binario:paquete:para qué» — el binario y el paquete NO siempre coinciden:
  # en Debian y Ubuntu bat se invoca batcat y fd se invoca fdfind, porque los
  # nombres cortos ya estaban cogidos por otros paquetes.
  if [[ "${CTT_TOOLS:-1}" == 1 ]]; then
    local spec bin pkg why
    for spec in \
      "fzf:fzf:el Ctrl+R difuso, el Ctrl+T y el menú de completado" \
      "eza:eza:ls con iconos y estado de git por fichero" \
      "batcat:bat:cat con sintaxis, y la vista previa del Ctrl+T" \
      "fdfind:fd-find:find usable, y lo que alimenta a fzf" \
      "zoxide:zoxide:el cd que aprende a dónde vas" \
      "delta:git-delta:diffs de git legibles, con la paleta" \
      "gh:gh:el CLI de GitHub" \
      "btop:btop:monitor del sistema" \
      "duf:duf:df que se entiende" \
      "http:httpie:cliente HTTP para probar APIs" \
      "tldr:tldr:el ejemplo que quieres en vez del man entero"
    do
      bin="${spec%%:*}"; why="${spec##*:}"
      pkg="${spec#*:}"; pkg="${pkg%%:*}"      # bash no anida expansiones como zsh
      command -v "$bin" >/dev/null || {
        DEPS_MISSING+=("$pkg — $why"); DEPS_PKGS+=("$pkg"); }
    done
    command -v lazygit >/dev/null || {
      DEPS_MISSING+=("lazygit — git en TUI (no está en apt, va de su release)")
      DEPS_ACTIONS+=(_lazygit_install); }
  fi

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
    # El buscador flotante. Windows no trae equivalente y su Win+S no se deja
    # pintar, así que el tema pone al lado uno que sí acepta paleta propia.
    if [[ ! -d "$(_win_home)/AppData/Local/FlowLauncher" ]] && command -v winget.exe >/dev/null; then
      DEPS_MISSING+=("Flow Launcher — el buscador flotante de Ctrl+Espacio")
      DEPS_ACTIONS+=(_flow_install)
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
    # Se pregunta por /dev/tty y no por stdin porque en `curl … | bash` stdin ES
    # el propio script. Pero /dev/tty no siempre se puede ABRIR —una sesión sin
    # terminal de control—, y ojo: `[[ -r /dev/tty ]]` dice que sí igualmente,
    # porque el nodo existe aunque open(2) devuelva ENXIO. Hay que intentarlo.
    local ans=n
    if { : </dev/tty; } 2>/dev/null; then
      printf '\n  %s¿instalo?%s [s/N] ' "$AMB" "$OFF"
      read -r ans </dev/tty || ans=n
    elif [[ -t 0 ]]; then
      printf '\n  %s¿instalo?%s [s/N] ' "$AMB" "$OFF"
      read -r ans || ans=n
    else
      warn "no hay terminal donde preguntar; relanza con --yes para que instale"
      return 1
    fi
    [[ "$ans" =~ ^[sSyY]$ ]] || { warn "no instalo nada; continúo con lo que haya"; return 1; }
  fi
  echo

  [[ ${#DEPS_PKGS[@]} -gt 0 ]] && { step "instalando: ${DEPS_PKGS[*]}"; _pm_install "${DEPS_PKGS[@]}" || warn "el gestor de paquetes falló"; }
  local fn
  for fn in "${DEPS_ACTIONS[@]}"; do "$fn"; done
  echo
}
