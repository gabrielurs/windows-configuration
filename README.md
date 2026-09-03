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

Si vienes a retomar esto y no a instalarlo, empieza por **[HANDOFF.md](HANDOFF.md)**:
estado actual, lo que se probó que no se puede —con la prueba al lado— y las trampas que
cuestan una tarde.

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

De una máquina WSL recién hecha al tema entero, en un comando:

```bash
curl -fsSL https://raw.githubusercontent.com/gabrielurs/claude-terminal-theme/main/bootstrap.sh | bash
```

`bootstrap.sh` no necesita git: si no está, se baja el tarball con el mismo curl
que lo ha traído. Deja el repo en `~/.local/share/claude-terminal-theme/src` y llama
a `install.sh`, que detecta lo que falta — git, zsh, python3, oh-my-zsh, Windhawk —
te enseña la lista completa, pide **una** confirmación y lo instala. Los paquetes del
sistema van por `sudo`, así que te pedirá la contraseña; no es desatendido y no te voy
a decir que lo sea.

Si ya tienes el repo:

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
| `--dotfiles` | además, la capa opcional de dotfiles |
| `--no-dock` | salta Windhawk |
| `--no-deps` | no instales nada que falte |
| `--yes` | no preguntes |
| `--dry-run` | enseña cada paso sin escribir nada |
| `--uninstall` | devuelve todo al snapshot original |

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

**Barra de tareas** — de ancho completo, pegada abajo y **siempre visible**: iconos
centrados, búsqueda reducida a icono, sin widgets, sin vista de tareas, nunca combinar
botones.

**Escritorio, Explorador y menús** — «Este equipo» visible, vista Detalles por defecto,
espaciado compacto, extensiones a la vista y ocultos visibles; el menú Inicio con la
sección de recientes que dibuja el diseño; y «Abrir con Code» en el menú contextual de
carpeta y de fondo de carpeta, con la ruta de `Code.exe` resuelta por búsqueda y no
cableada. Todo `HKCU` — ni siquiera el menú contextual necesita elevación, porque va a
`HKCU\Software\Classes` y no a `HKCR`. Todo apuntado en el snapshot antes de tocarlo.

**Forma y color de la barra** (necesita [Windhawk](https://windhawk.net)) — sin tema base,
`controlStyles` propios: fondo `#0A0D0F` de borde a borde, línea superior `#1A2026`,
botón de app con radio 10 y relleno teal al 13% cuando está activo, indicador de app
abierta en teal `#4DD6C1`.

`cornerRadius` y `padding` van a **0** en `palette.json`, y no por descuido: el
`Rectangle` del fondo vive *dentro* del padding del `RootGrid`, así que cualquier padding
lateral deja los extremos sin pintar y se ven como dos huecos en la pantalla. El radio
hace lo mismo en las esquinas. El diseño dibuja esquinas redondeadas; si las prefieres a
la cobertura total, sube `cornerRadius`. El menú Inicio va a juego con
*Windows 11 Start Menu Styler* (`TranslucentStartMenu` + `$CommonBgBrush`), y el reloj pasa
a dos líneas monoespaciadas — hora sobre fecha, con cpu y ram — vía
*Taskbar Clock Customization*.

Dos detalles que cuestan caro si no se saben:

- el botón de Inicio se localiza por `AutomationProperties.AutomationId=StartButton` y
  **no** por `Name=Start`: el `Name` está traducido y en un Windows en español no casa
- con «nunca combinar», los botones llevan etiqueta y su clase pasa de
  `TaskListButtonPanel` a `TaskListLabeledButtonPanel`. Hay que apuntar a las dos, o el
  fondo se queda sin pintar en cuanto se activan las etiquetas

**El Explorador va en un solo tono, y el tono es el de Windows.** La lista, el árbol y la
cabecera de columnas son Win32 y están clavados en `#191919`: no ceden por estilo, ni por
`themeResourceVariables`, ni hay mod que exponga ese color. Como esa mitad no se puede
mover, la única forma de que la ventana sea de un color es bajar el chrome a reunirse con
ella — al revés no se puede.

Medido, el cuerpo tenía seis grises: `#191919` (Win32), `#0A0D0F` (nuestro chrome),
`#141618` (panel de detalles), `#1C1C1C` (barra de estado), `#202020` (franja del título)
y `#333333` (filetes). Quedan dos: `#191919` en todo, y el `#202020` de la franja, que a
siete niveles de diferencia ya no canta — antes eran veintidós.

Los otros dos se quitan de raíz en vez de recolorearse: `ShowStatusBar=0` y ocultar el
panel de detalles, que además es lo que pide la sección 06 del diseño. Se van dos
superficies enteras que no se podían pintar.

El coste es real: el Explorador deja de llevar el negro del tema. Para volver al negro
asumiendo dos tonos, `explorer.surfaces.chrome` a `#0A0D0F`.

**Los botones de la ventana se tapan solos si te descuidas.** Pintar
`Grid#TabContainerGrid` —el contenedor de la franja del título— con un fondo opaco hace
desaparecer minimizar, maximizar y cerrar. No es cosa de Windows ni del mod del borde
(ese solo llama a `DwmSetWindowAttribute` con `DWMWA_BORDER_COLOR`): esos botones se
dibujan **por debajo** del árbol XAML y cualquier capa opaca a ese nivel los oculta.

Medido: con el contenedor pintado, en un recorte de 200×46 px de esa esquina no aparecía
ni un píxel de glifo, solo cuatro colores planos. Al dejar de pintarlo, salen los tres.
Probados cuatro contenedores por encima con colores distintos en una pasada —
`FileExplorerTabControl` y `Grid#RootContainer` no enganchan, `TabContainerGrid > Border`
pinta un filete de 731 px, y `TabView` sí pinta la franja **pero también los tapa**.

Por eso las pestañas se pintan con `TabViewListView#TabListView`, que es solo la lista, y
el resto de la franja se intenta por `themeResourceVariables` — sustituyendo el recurso
del que sale el gris en vez de superponer una capa.

**El Explorador es híbrido, y eso marca el límite.** Medido sobre una captura, no
supuesto: pestañas, barra de comandos y barra de direcciones son XAML y sí toman la
paleta (`#07090A` / `#0A0D0F`). La lista de ficheros, el árbol de la izquierda y la barra
de estado son el shell view Win32 clásico, donde el styler no entra: se quedan en el
`#191919` del tema oscuro del sistema. Cambiar eso pediría parchear `uxtheme`, que no
compensa. Las **columnas** sí son exactamente las del diseño — NOMBRE / MODIFICADO /
TIPO / TAMAÑO en ese orden y con sus anchuras — vía *Explorer Details View Columns*.

**La rama de git en la bandeja.** El reloj sabe pedir texto por HTTP y pintarlo como
`%web1%`, así que la rama no necesita nada exótico: `lib/gitbranch.py` la sirve por
loopback desde WSL y el reloj la lee. Windows llega al `127.0.0.1` de WSL porque
`localhostForwarding` viene en true de fábrica.

Qué rama enseña: la del repo **donde tienes la shell**. El tema zsh apunta la raíz del
repo en `~/.local/state/claude-terminal-theme/repo` en cada prompt, y el servidor lee de
ahí. Se guarda la ruta y no la rama, así un `git checkout` se refleja sin que la shell
tenga que enterarse. Si ese fichero no existe todavía, cae al repo con la mtime más nueva
bajo `~/projects` — más tosco, porque `git status` no siempre reescribe el índice, pero
da algo razonable. El `*` es que hay cambios sin commitear, y el nombre se recorta a 16
caracteres para que una rama larga no ensanche el reloj y empuje la bandeja.

Lo mantiene vivo una unit de systemd de usuario. Sin systemd en la WSL, el instalador
avisa y te deja lanzarlo a mano; si el servicio se cae, `%web1%` sale vacío y el reloj
queda exactamente como antes.

**El botón de Inicio.** El styler solo llega al fondo del botón, no al logo — pero
*Start Button Replacer* cambia la imagen entera por un PNG propio, así que ahí va el
`❯` teal del diseño, generado por `lib/icons.py` con la misma fuente monoespaciada que
el resto de glifos. El fondo —el tinte teal al 10%— lo sigue poniendo el styler de la
barra, no el PNG, que va con alfa.

Ojo con confundirlo: el `✦` ámbar es el icono de **Claude**, no el del botón de Inicio.
Los siete glifos salen del diseño y no de la intuición:

| | glifo | rol |
|---|---|---|
| botón de Inicio | `❯` | teal |
| Terminal / Ubuntu | `$_` | verde |
| Archivos | `▤` | teal |
| VS Code | `◈` | azul |
| Navegador | `◉` | morado |
| Claude | `✦` | ámbar |
| Ajustes | `⚙` | gris |

Ese mod **no aparece en el catálogo** de windhawk.net ni en la pestaña Explore, aunque su
página existe. Se instala pegando el fuente en *Create new mod*. Y ojo con sus valores por
defecto: `pressedImageSource` y `activatedImageSource` apuntan a unos GIF de un gecko
alojados en GitHub, así que hay que escribirlos vacíos explícitamente — el `.reg` borra la
subclave antes de reescribirla y lo que no se ponga vuelve al gecko.

**La ventana activa.** La sección 06 la quiere distinguida por color sin pintarle la
barra de título, y *Windows 11 Accent Window Border* hace justo eso: borde en el acento,
y **exige** `ColorPrevalence=0`, que es lo que el diseño manda dejar. Activa en teal,
inactiva en el gris de `windowsAccent.inactiveBorder`. La diferencia honesta: el diseño
dibuja una línea de 1px *bajo el título* y esto es el borde completo de la ventana.

Ese `inactiveBorder` va separado de `start` a propósito. Compartían valor, y con un teal
apagado en la inactiva **todas** las ventanas acaban con borde teal — justo la señal que
la sección 06 quiere transmitir, perdida.

Y escribir el color no basta: quien lo usa ya lo tiene en memoria. El mod lo recarga con
`WM_DWMCOLORIZATIONCOLORCHANGED` (0x0320) y con nada más — ni `WM_SETTINGCHANGE` con
«ImmersiveColorSet» ni `UpdatePerUserSystemParameters`, ambos probados y ambos inútiles
aquí. Por eso el instalador difunde ese mensaje después de escribir el acento; sin él, el
borde se queda con el color anterior hasta el siguiente inicio de sesión.

**Lo que el diseño pide y no se puede:** los iconos de app en monoespaciada (son los
iconos reales de cada programa; el del acceso directo solo se ve mientras la app está
cerrada) y el indicador con el color de cada app (el styler no sabe qué app es cada
botón, así que van todos en teal). El propio diseño ya avisa de que los iconos por tipo
de fichero del Explorador tampoco son nativos — y de que su lista tipo `ls -la` es dibujo,
no Explorador.

En cambio el diseño se equivoca en tres puntos a favor: daba por hecho que cpu/ram exigían
TrafficMonitor o un script propio —el mod del reloj trae `%cpu%` y `%ram%` de serie—, la
rama de git parecía imposible hasta mirar que el reloj hace peticiones HTTP, y el logo de
Inicio resultó cambiable.

**Y un punto donde el diseño no sobrevive al uso:** pedía «nunca combinar botones», que en
Windows implica una etiqueta pegada a cada icono. Con diez ventanas abiertas son diez
títulos truncados comiéndose la barra entera, así que `combineButtons` va en `always` —
un icono por app. `whenFull` y `never` siguen ahí si los quieres.

## El buscador flotante

Windows no trae un Spotlight, y el suyo —Win+S— **no se deja pintar**: el mod llega al
panel (medido, su fondo es `#07090A`), pero la lupa es un icono **bicolor**, `#0078D3`
azul con verde, así que no es un glifo monocromo al que cambiarle `Glyph` y `Foreground`.
Ahí se acaba lo que el styler puede hacer.

Así que en vez de seguir peleándose con él, el tema pone al lado uno que sí obedece:
**Flow Launcher**, cuyos temas son ficheros XAML sueltos. `lib/flow.py` genera el suyo
desde `palette.json`, igual que el resto del repo genera el `.zsh-theme` o el perfil de
PowerShell — un solo sitio donde cambiar un color.

Sale centrado con **Ctrl+Espacio**, fondo `#07090A`, borde teal como la ventana activa,
la caja de consulta en Cascadia Mono con el cursor en teal, y las rutas de los resultados
también monoespaciadas. Los títulos se quedan en la fuente de sistema, por el mismo motivo
que en el Explorador: legibilidad con muchas filas.

Dos cosas que cuestan si no se saben:

- **Flow reescribe su `Settings.json` al salir.** Hay que pararlo antes de tocarlo o se
  lleva por delante lo que acabas de poner. Mismo patrón que el blob de anclados.
- **El tema se genera contra el `Base.xaml` instalado, no contra una plantilla.** Las
  claves `Base*` cambian entre versiones: la plantilla de su rama dev usa
  `BaseHorizontalThumbStyle` y `BaseHorizontalScrollBarStyle`, que la 2.1.3 no define. Un
  `StaticResource` a una clave inexistente revienta el parseo del tema **entero**, así que
  `lib/flow.py` lee las claves que la versión instalada declara y omite los estilos cuyo
  base falte.
- **Y cuando falla no te enteras desde fuera.** Flow avisa con un diálogo —«Fail to load
  theme, fallback to default»— que **no deja rastro en su log**. Desde el instalador solo
  se ve que `Theme` vuelve solo a `Win11Light` a los pocos segundos. Si eso pasa, el
  síntoma es ese y la causa suele ser una referencia rota.

## ¿Y sin Windhawk?

Casi todo. Por registro puedes tener el acento, el modo oscuro, la transparencia, el
fondo, y la barra centrada, con autohide y sin widgets ni búsqueda. Lo único que Windows
**no** expone por registro es un dock **flotante, redondeado y despegado del borde**: eso
necesita inyección en la UI de explorer, que es lo que hace Windhawk.

Si no lo tienes, `./install.sh` lo detecta y se salta ese paso solo — el resto se aplica
igual. Los dos mods hay que instalarlos desde la interfaz de Windhawk; este repo los
configura, no los instala.

Windhawk guarda sus ajustes en `HKLM`, así que ese paso pide **una** ventana de UAC.

## Portarlo a otra máquina

El objetivo declarado es **WSL + Windows**. En Linux puro o macOS, `--shell` instala
el prompt y los colores, pero `claude-10-colors.zsh` asume coreutils de GNU: en macOS
`ls --color=auto` no existe y habría que ramificar a `LSCOLORS`. No está hecho.

Lo que sí viaja bien:

- **rutas**: nada está cableado. `%USERPROFILE%` se pregunta a `cmd.exe`, el
  `settings.json` de Windows Terminal se busca por glob (empaquetado, preview y
  suelto), y VS Code se prueba en sus tres sabores
- **el snapshot no viaja, a propósito**: vive en `~/.local/share/`, fuera del repo.
  Cada máquina guarda su propio «antes»; llevarte el de otra es justo lo que rompe
  la marcha atrás
- **ningún secreto en el repo**: el `GITHUB_TOKEN` de la capa de dotfiles se deriva
  de `gh auth token` en cada arranque en vez de guardarse

### El único paso manual: los nueve mods

Windhawk compila los mods en local desde su interfaz y **no expone CLI**, así que no hay
forma de instalarlos desde fuera. El instalador pone Windhawk con winget, detecta cuáles
faltan y los lista — pero ponerlos son clics tuyos.

Ese listado no es un volcado de ids, y la razón importa: **la pestaña Explore de Windhawk
busca por nombre, no por id**. Buscar `taskbar-start-button-position` no devuelve nada;
el mod se llama *«Start button always on the left»*. Por eso `windows/mods.json` guarda
las dos cosas, y el instalador imprime el nombre buscable, para qué sirve y la URL
directa. Si añades un mod al código y olvidas su ficha, el instalador **falla en el
sitio** en vez de dejar a la siguiente máquina adivinando.

Uno de los nueve, *Start Button Replacer*, **no aparece en el catálogo** de windhawk.net
ni en Explore, aunque su página existe. Ese va por *Create new mod* pegando el fuente; el
instalador te da la URL cruda. No lo vendorizo en el repo porque es GPL-3.0 y esto es MIT.

Sin los mods, el resto se aplica igual: colores, acento, barra por registro, iconos,
menú contextual y la rama de git. Lo que te falta es la forma y el color.

### Lo que el instalador sí resuelve solo

`bootstrap.sh` va de una WSL recién hecha al tema completo en un comando, sin git
—se baja el tarball con el mismo `curl` que lo trajo— e instala lo que falte: zsh,
oh-my-zsh, los plugins, Windhawk. El servicio de la rama de git se genera desde una
plantilla con la ruta real del repo y se engancha a systemd. Y `--dry-run` te enseña la
lista entera de cambios sin tocar nada, que es la forma sensata de estrenar máquina.

## La capa de dotfiles

`--dotfiles` es opcional y no reescribe tu `.zshrc`: copia los ficheros de
`dotfiles/zshrc.d/` a `~/.config/claude-terminal-theme/zshrc.d/` y añade al final del
`.zshrc` un bloque marcado que los sourcea. Quitar el bloque desactiva la capa entera.

Trae PATH (`~/.local/bin`, bun, opencode), nvm, el SDK de Android, el `GITHUB_TOKEN`
derivado de `gh`, y el prompt anclado abajo con Ctrl+L que limpia también el scrollback.
Todo condicionado a que la herramienta exista, así que en una máquina pelada no da un
solo error: simplemente no hace nada. Detalle en [dotfiles/README.md](dotfiles/README.md).

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
