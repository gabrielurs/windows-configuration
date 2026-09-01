# GITHUB_TOKEN derivado de gh, para los MCP y las herramientas que lo esperan.
# Se deriva en vez de guardarse: así no hay ningún secreto en el repo ni en el
# .zshrc, y caduca cuando caduca la sesión de gh.
if [[ -z $GITHUB_TOKEN ]] && command -v gh >/dev/null 2>&1; then
  _ctt_tok="$(gh auth token 2>/dev/null)"
  [[ -n $_ctt_tok ]] && export GITHUB_TOKEN="$_ctt_tok"
  unset _ctt_tok
fi
