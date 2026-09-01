# Capa de dotfiles

Opcional. El tema funciona sin esto; esto es *mi* configuración de shell, la que
quiero que viaje conmigo a cualquier máquina.

Se aplica con `./install.sh --dotfiles` y **no reescribe tu `.zshrc`**: copia
estos ficheros a `~/.config/claude-terminal-theme/zshrc.d/` y añade un bloque
marcado al final del `.zshrc` que los sourcea en orden:

```zsh
# >>> claude-terminal-theme dotfiles >>>
for _f in ~/.config/claude-terminal-theme/zshrc.d/*.zsh(N); do source $_f; done
unset _f
# <<< claude-terminal-theme dotfiles <<<
```

Quitar el bloque desactiva la capa entera sin tocar nada más, y `--uninstall`
lo hace por ti.

| fichero | qué trae |
|---|---|
| `10-path.zsh` | `~/.local/bin`, bun, opencode. `typeset -U` evita duplicados |
| `20-nvm.zsh` | nvm, si está |
| `30-android.zsh` | SDK de Android y JDK, solo si los directorios existen |
| `40-github-token.zsh` | `GITHUB_TOKEN` derivado de `gh auth token` |
| `50-prompt-bottom.zsh` | prompt anclado abajo y Ctrl+L que limpia el scrollback |

Todo está condicionado a que la herramienta exista, así que en una máquina pelada
no da un solo error: simplemente no hace nada.

**Ningún secreto vive aquí.** El token de GitHub se deriva de `gh` en cada
arranque en vez de guardarse.
