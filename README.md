# claude-terminal-theme

Un tema de terminal derivado de la paleta que usa **Claude Code** en prosa, aplicado
de una pasada a todo lo que ves cuando trabajas: zsh, Windows Terminal, PowerShell,
la terminal integrada de VS Code y el color de acento de Windows.

No es un tema más: la paleta asigna **un color por tipo de dato**, siempre el mismo.
Una ruta es teal en el prompt, en `ls`, en `grep -n`, en el resaltado de la línea de
comandos y en un `man`. El color deja de ser decoración y pasa a ser información.

```
~/projects/claude-terminal-theme on main + ~ ?  ❯ git commit -m "algo"        4.2s
└─ teal: ruta                    └─ azul: rama    └─ verde: comando
                                                     └─ morado: flag  └─ ámbar: string
```

## La paleta

| color | | rol |
|---|---|---|
| `#4DD6C1` | teal | rutas, ficheros, tablas, repos |
| `#57E389` | verde | identificadores, código inline, altas |
| `#6FB6FF` | azul | urls, ramas, enlaces |
| `#E8C46A` | ámbar | números, dinero, métricas, avisos |
| `#B07CF0` | morado | modos y ajustes del propio CLI |
| `#F2777A` | rojo | bajas, errores, riesgo |
| `#ECEFF4` | blanco | énfasis en prosa |
| `#6B7683` | gris | flechas, separadores, unidades |

Fondo `#07090A`, texto `#C9D1D9`. Todo sale de [`palette.json`](palette.json), que es
la única fuente de verdad: cambia un hex ahí, relanza `./install.sh` y se propaga a
las cinco superficies.

## Instalar

```bash
git clone git@github.com-iesebre:gabrielurs/claude-terminal-theme.git
cd claude-terminal-theme
./install.sh --dry-run    # mira primero qué va a tocar
./install.sh              # y hazlo
exec zsh
```

| flag | qué hace |
|---|---|
| *(nada)* | shell + Windows, lo que detecte |
| `--shell` | solo zsh |
| `--windows` | solo Windows Terminal, VS Code, PowerShell y acento |
| `--dry-run` | enseña cada paso sin escribir nada |
| `--uninstall` | retira los ficheros del tema |

Es idempotente: relanzarlo deja el mismo resultado. Antes de tocar cualquier fichero
que ya existía guarda una copia `.bak-claude-<timestamp>` al lado, y exporta las claves
de registro a `%USERPROFILE%\claude-theme-backup\`.

## Qué toca exactamente

**zsh** (`~/.oh-my-zsh/custom/`)
- `claude-00-palette.zsh` — generado desde `palette.json`, define `CC_TEAL`, `CC_HEX_TEAL`…
- `claude-10-colors.zsh` — `LS_COLORS`, `GREP_COLORS`, `LESS_TERMCAP_*`, colores del
  completado y los estilos de los dos plugins de resaltado. Trae `claude-palette`.
- `themes/claude.zsh-theme` — prompt de una línea: ruta teal (truncada a 3 tramos a
  partir de 5 niveles), rama azul, estado git por colores, `❯` que se pone rojo si el
  comando anterior falló, y a la derecha el código de salida y la duración si pasó de 2s.
- En `.zshrc`: `ZSH_THEME`, los plugins `zsh-autosuggestions` y `zsh-syntax-highlighting`
  (este último siempre el último de la lista, lo exige él), y `COLORTERM=truecolor`.

**Windows Terminal** — esquema `Claude CLI` con los 16 ANSI, tema de ventana (la fila
de pestañas deja de ser gris del sistema) y un bloque `profiles.defaults` que iguala
todos los perfiles: Cascadia Code, padding, cursor bloque, sin acrílico, `intenseTextStyle`
en `bright` para que la negrita use los tonos claros de la paleta.

**PowerShell** — crea `Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`
con el mismo prompt `❯` y los colores de PSReadLine. Se genera desde una plantilla con
placeholders, así que también sigue a `palette.json`.

**VS Code** — 27 claves en `workbench.colorCustomizations` para que la terminal integrada
sea idéntica a la de fuera.

**Acento de Windows** — `AccentPalette` (rampa de 8 tonos), `AccentColorMenu`,
`StartColorMenu` y los valores de DWM. Deja `ColorPrevalence` como estuviera: el acento
sale en resaltados, foco y menú Inicio, pero no pinta las barras de título salvo que lo
pidas tú.

## Requisitos

- zsh ≥ 5.7 y [oh-my-zsh](https://ohmyz.sh/) — los hex en el prompt necesitan 5.7
- un terminal con color de 24 bits
- `python3` (solo para el instalador)
- la parte de Windows necesita WSL con `/mnt/c` montado e interop activo

Sin WSL, `./install.sh --shell` funciona igual en Linux o macOS.

## Deshacer

```bash
./install.sh --uninstall
```

Retira los ficheros del tema pero **no** revierte el `.zshrc` ni el acento de Windows,
a propósito: para eso están los backups. El `.zshrc` original está en
`~/.zshrc.bak-claude-*` y las claves de registro en `%USERPROFILE%\claude-theme-backup\`
(doble clic en el `.reg` y restaura).

## Origen

La paleta viene del tema `Terminal` de [claude-code-themes](https://github.com/gabriel-diagram/claude-code-themes),
que es el que usa la propia CLI. Este repo la saca de la CLI y la lleva al resto del escritorio.

## Licencia

MIT.
