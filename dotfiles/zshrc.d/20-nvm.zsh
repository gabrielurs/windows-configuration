# nvm. Cargarlo entero cuesta ~200ms de arranque; se hace igualmente porque sin
# esto `node` no existe. Si te molesta, comenta la línea y usa `nvm use` a mano.
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
[[ -s "$NVM_DIR/nvm.sh" ]] && source "$NVM_DIR/nvm.sh"
[[ -s "$NVM_DIR/bash_completion" ]] && source "$NVM_DIR/bash_completion"
