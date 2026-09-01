# claude-terminal-theme

Un tema derivado de la paleta que usa **Claude Code** en prosa, aplicado de una pasada
a todo lo que ves cuando trabajas: zsh, Windows Terminal, PowerShell, la terminal
integrada de VS Code, el acento de Windows y la barra de tareas — que pasa a ser un
dock flotante al estilo macOS.

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
| `--windows` | solo la parte de Windows |
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

**Barra de tareas** — iconos centrados, autohide, sin widgets, sin vista de tareas, sin
caja de búsqueda. Todo `HKCU`, todo apuntado en el snapshot antes de tocarlo.

**Dock flotante** (opcional, necesita [Windhawk](https://windhawk.net)) — parte del tema
integrado `DockLike` del mod *Windows 11 Taskbar Styler* y lo recolorea: cristal `#0A0D0F`
al 90%, borde `#1A2026`, radio 16, despegado 10px del borde inferior, indicador de app
abierta en teal y botón activo con relleno teal oscuro. El menú Inicio va a juego con
*Windows 11 Start Menu Styler* usando `TranslucentStartMenu` y su `$CommonBgBrush`.

## ¿Y sin Windhawk?

Casi todo. Por registro puedes tener el acento, el modo oscuro, la transparencia, el
fondo, y la barra centrada, con autohide y sin widgets ni búsqueda. Lo único que Windows
**no** expone por registro es un dock **flotante, redondeado y despegado del borde**: eso
necesita inyección en la UI de explorer, que es lo que hace Windhawk.

Si no lo tienes, `./install.sh` lo detecta y se salta ese paso solo — el resto se aplica
igual. Los dos mods hay que instalarlos desde la interfaz de Windhawk; este repo los
configura, no los instala.

Windhawk guarda sus ajustes en `HKLM`, así que ese paso pide **una** ventana de UAC.

## Requisitos

- zsh ≥ 5.7 y [oh-my-zsh](https://ohmyz.sh/) — los hex en el prompt necesitan 5.7
- un terminal con color de 24 bits
- `python3` (solo para el instalador)
- la parte de Windows necesita WSL con `/mnt/c` montado e interop activo
- el dock flotante necesita Windhawk con los mods *Windows 11 Taskbar Styler* y
  *Windows 11 Start Menu Styler* instalados

Sin WSL, `./install.sh --shell` funciona igual en Linux o macOS.

## Deshacer

```bash
./install.sh --uninstall --dry-run   # qué devolvería, sin tocar nada
./install.sh --uninstall
```

Esto no borra a ojo: restaura un **snapshot** del estado original.

La primera vez que el instalador va a tocar algo, apunta cómo estaba —
el contenido íntegro de cada fichero, o la marca «no existía» si lo creamos nosotros;
el tipo y el dato de cada valor de registro, o «no existía»; y una exportación completa
de las claves de Windhawk, donde restaurar valor a valor no basta. Ese primer apunte
manda: reinstalar mil veces no lo pisa, así que `--uninstall` siempre devuelve la máquina
a como estaba **antes de conocer este repo**, no a la penúltima instalación.

Vive en `~/.local/share/claude-terminal-theme/snapshot/` — bórralo y pierdes la marcha
atrás. Lo de `HKLM` se junta en un solo `.reg` y pide una ventana de UAC.

Además, cada fichero que se pisa deja un `.bak-claude-<timestamp>` al lado, por si
prefieres mirarlo a mano.

## Origen

La paleta viene del tema `Terminal` de [claude-code-themes](https://github.com/gabriel-diagram/claude-code-themes),
que es el que usa la propia CLI. Este repo la saca de la CLI y la lleva al resto del escritorio.

## Licencia

MIT.
