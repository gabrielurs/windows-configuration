#!/usr/bin/env bash
# bootstrap.sh — de una máquina WSL recién hecha al tema completo, en un comando:
#
#   curl -fsSL https://raw.githubusercontent.com/gabrielurs/windows-configuration/main/bootstrap.sh | bash
#
# Y con argumentos para install.sh:
#
#   curl -fsSL .../bootstrap.sh | bash -s -- --shell --yes
#
# No necesita git: si no está, se baja el tarball con el mismo curl que te ha
# traído este script. Todo lo demás lo resuelve install.sh --deps.
set -euo pipefail

OWNER="${CTT_OWNER:-gabrielurs}"
REPO="${CTT_REPO:-windows-configuration}"
BRANCH="${CTT_BRANCH:-main}"
DIR="${CTT_DIR:-$HOME/.local/share/claude-terminal-theme/src}"

TEAL=$'\e[38;2;77;214;193m'; GREY=$'\e[38;2;107;118;131m'
RED=$'\e[38;2;242;119;122m'; OFF=$'\e[0m'
say() { printf '%s·%s %s\n' "$TEAL" "$OFF" "$*"; }
die() { printf '%s✗ %s%s\n' "$RED" "$*" "$OFF" >&2; exit 1; }

printf '%stema Claude CLI%s %sbootstrap%s\n\n' "$TEAL" "$OFF" "$GREY" "$OFF"

[[ $EUID -eq 0 ]] && die "no lo lances como root: instala para tu usuario"
command -v curl >/dev/null || die "hace falta curl (y si lees esto, ya lo tienes... ejecuta el script a mano)"

# ── traer el repo ─────────────────────────────────────────────────────
if [[ -d "$DIR/.git" ]]; then
  say "ya está clonado en $DIR, actualizando"
  git -C "$DIR" pull --ff-only --quiet || say "no pude actualizar, sigo con lo que hay"
elif command -v git >/dev/null; then
  say "clonando en $DIR"
  mkdir -p "$(dirname "$DIR")"
  rm -rf "$DIR"
  git clone --depth=1 --branch "$BRANCH" --quiet \
    "https://github.com/$OWNER/$REPO.git" "$DIR"
else
  say "sin git: me bajo el tarball"
  mkdir -p "$DIR"
  curl -fsSL "https://github.com/$OWNER/$REPO/archive/refs/heads/$BRANCH.tar.gz" \
    | tar -xz -C "$DIR" --strip-components=1 \
    || die "no pude descargar el repo (¿es privado? entonces clónalo con tus claves)"
fi

chmod +x "$DIR/install.sh" 2>/dev/null || true
say "lanzando el instalador"
echo
exec "$DIR/install.sh" "$@"
