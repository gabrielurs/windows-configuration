# PATH. `typeset -gU` deduplica, así que da igual que el .zshrc de la máquina ya
# tenga alguna de estas líneas: no se acumulan. El -g es necesario para que siga
# siendo global aunque esto se sourcee desde dentro de una función.
typeset -gU path PATH

[[ -d $HOME/.local/bin ]] && path=($HOME/.local/bin $path)

# bun
export BUN_INSTALL="${BUN_INSTALL:-$HOME/.bun}"
[[ -d $BUN_INSTALL/bin ]] && path=($BUN_INSTALL/bin $path)
[[ -s "$BUN_INSTALL/_bun" ]] && source "$BUN_INSTALL/_bun"

# opencode
[[ -d $HOME/.opencode/bin ]] && path=($HOME/.opencode/bin $path)

export PATH
