# Traspaso

Estado del tema a 3 de septiembre de 2026. Qué funciona, qué se probó que **no** puede
funcionar, y las trampas que cuestan una tarde si no se saben.

```
repo    ~/projects/claude-terminal-theme      rama    main
commits 27 en total, 13 de la última sesión
remoto  github.com:gabrielurs/windows-configuration  (ssh github.com-iesebre)
```

## Estado, medido no supuesto

| | |
|---|---|
| ida y vuelta | **7/7** testigos tras desinstalar y reinstalar de verdad |
| auto-test | **63/63**, con el chuletario contrastado contra `bindkey` |
| snapshot | 84 entradas — 14 ficheros, 60 valores, 10 claves completas |
| mods de Windhawk | 10 configurados, 178 ajustes |
| rama de git | servicio activo en `127.0.0.1:8756` |
| buscador | Flow Launcher, tema `ClaudeCLI`, `Ctrl+Space` |
| acento | `#4DD6C1` con `ColorPrevalence=0` |
| atajos | modo vim en zsh y AutoHotkey v2 en `Alt+Space`, banda medida en pantalla |

## Hecho, por superficie

| superficie | qué lleva |
|---|---|
| barra | 50 px, iconos a 24, esquinas superiores a 14, un icono por app sin etiqueta, Inicio a la izquierda con el chevron teal |
| reloj | dos líneas con segundos, día abreviado, cpu/ram y la rama de git del repo donde tienes la shell |
| Explorador | un solo tono `#191919`; panel de detalles y barra de estado eliminados, no recoloreados |
| ventanas | borde teal en la activa, gris en las inactivas, sin pintar la barra de título |
| Inicio y notificaciones | opacos — filtraban el fondo de pantalla |
| buscador | flotante, centrado, con la paleta generada desde `palette.json` |
| atajos | vim en la línea de comandos con objetos de texto y `surround`; `Alt+Space` abre un modo de ventanas con banda which-key sobre la barra e icono de bandeja que cambia con el modo |

## Lo que no se puede, y cómo se descartó

Esta sección existe para que nadie repita el trabajo. Cada punto lleva la prueba.

### El árbol y la lista del Explorador en la paleta

El diseño v2 afirma que el fondo del árbol se alcanza. **No en la build 26200.**

```
6 selectores sondeados a la vez, cada uno con un color distinto:
  NavigationView · RootSplitView · PaneRoot
  PaneContentGrid · SplitView>PaneRoot · ContentGrid
  → ninguno enganchó

clases hijas de la ventana del Explorador:
  DirectUIHWND ×2 · SHELLDLL_DefView · DUIViewWndClassName   ← Win32
  DesktopChildSiteBridge ×2                                  ← las únicas islas XAML
```

### La franja del título a la derecha de las pestañas

No es un fallo, es una disyuntiva: todo lo que la pinta tapa también los botones de
minimizar, maximizar y cerrar, porque se dibujan **por debajo** del árbol XAML.

```
por estilo    TabView                 pinta 27.047 px … y 0 píxeles de glifo
              TabContainerGrid        igual, los tapa
              FileExplorerTabControl · Grid#RootContainer   no enganchan
por recurso   SolidBackgroundFillColorBase · su Brush
              LayerOnMicaBaseAltFillColorDefault            sin efecto
```

Se eligió **botones visibles**. La franja queda a 7 niveles de diferencia del resto; antes
del tono único eran 22, y entonces sí cantaba.

### El prompt `❯` en la lupa de Win+S

El mod **sí** llega al panel — su fondo mide `#07090A`, 31.388 muestras. Pero la lupa es
**bicolor**, `#0078D3` azul con verde: no es un `FontIcon` monocromo al que cambiarle
`Glyph` y `Foreground`.

Resuelto por otra vía: el buscador flotante hace lo que este no dejaba.

### El subrayado del color de cada app

El styler no sabe qué aplicación es cada botón de la barra, así que el indicador va teal
para todas. Lo piden las dos versiones del diseño; no hay forma.

## Trampas que costaron tiempo

### Explorer reescribe lo que le toques mientras vive

El blob `Favorites` de los anclados se vuelca al cerrarse. **Matar explorer ANTES de
escribir**, nunca después. Lo mismo con Flow Launcher y su `Settings.json`, y por eso el
desinstalador para los dos antes de restaurar.

Aprendido rompiendo los anclados del usuario y teniendo que recomponerlos.

### El tema de Flow se genera contra el `Base.xaml` instalado

Las claves `Base*` cambian entre versiones: la plantilla de la rama dev usa
`BaseHorizontalThumbStyle` y `BaseHorizontalScrollBarStyle`, que la 2.1.3 no define, y un
`StaticResource` roto tumba el tema **entero**.

Y cuando falla **no te enteras desde fuera**: Flow saca un diálogo en pantalla que *no deja
rastro en su log*. Desde el instalador solo se ve que `Theme` vuelve solo a `Win11Light` a
los pocos segundos. Si pasa eso, el síntoma es ese y la causa suele ser una referencia rota.

### Escribir el acento no lo aplica

Quien lo usa ya lo tiene en memoria. Solo lo recarga `WM_DWMCOLORIZATIONCOLORCHANGED`
(0x0320). Probados y descartados `WM_SETTINGCHANGE` con `ImmersiveColorSet` y
`UpdatePerUserSystemParameters`.

### AutoHotkey: dos trampas que no dan error

**`Trim()` recorta espacios y tabuladores, NO saltos de línea.** El interruptor de la banda lo
escribe la shell con `print`, que deja un `\n`. El script leía «on\n», nunca era igual a «on»,
y la banda no aparecía **nunca**: el modo funcionando y sin explicarse jamás, que es justo lo
contrario de para lo que existe. Sin excepción, sin diálogo, sin nada. Hay que pasarle los
caracteres a mano: `Trim(x, " \`t\`r\`n")`.

**La autoejecución termina en la PRIMERA definición de atajo.** Todo lo que hay por debajo de
`!Space::` son funciones que alguien tiene que llamar. Un `OnExit()` suelto al final del fichero
—que es donde lo puse— no se registra nunca y no se queja. El auto-test lo comprueba ahora
por posición.

Y la herramienta que hace posible depurar esto desde WSL: **`/ErrorStdOut`**. Sin él, un error
abre un diálogo en el escritorio de Windows y desde aquí solo se ve un proceso que no responde.

```bash
AutoHotkey64.exe /ErrorStdOut script.ahk     # el error sale por stdout
```

Ojo al leerlo: escribe en la página de códigos del sistema, no en UTF-8. Con `text=True` en
Python el propio decodeo revienta y **tapa el error que querías ver**.

### fzf se queda con `^R` también en `vicmd`

Lo ata él, en la línea 115 de su `key-bindings.zsh`, que la capa 30 sourcea. O sea que no
basta con **no** atarlo en la capa 40: hay que quitárselo con un `bindkey -M vicmd '^r' redo`
explícito. Si no, la tira anuncia «deshacer / rehacer» y `^R` abre el buscador difuso.

Esto es la razón de que el auto-test compare contra un **widget esperado** y no solo contra
«¿está atado?». La tecla respondía; hacía otra cosa. Un chuletario que miente es peor que no
tener chuletario.

### Lo que un banco de pruebas con pty NO puede tocar

Salió repasando el funcionamiento en terminal, y conviene saberlo antes de perder una tarde
persiguiendo un fantasma: bajo el pty de los tests **el pty no es el terminal de control de
zsh**, así que las señales del terminal no le llegan.

```
Ctrl+C  no aborta la línea   ← tampoco en la configuración anterior a este repo
WINCH   no dispara el trap   ← la tira sigue con el ancho viejo, y no se puede
                               distinguir «el trap no sirve» de «la señal no llegó»
fzf     no llega a pintarse  ← 19 bytes, idénticos CON y SIN la capa 40
```

Lo importante de esos tres: **se comparó contra la configuración sin la capa nueva y da
exactamente lo mismo**. No son regresiones; son el límite del banco. La comparación es la que
convierte «no funciona» en «no se puede medir», y hay que hacerla antes de tocar nada.

Un aviso concreto de ahí: se escribió un `TRAPINT` para limpiar la tira al abortar y pareció
romper Ctrl+C. **No lo rompía** — Ctrl+C ya no funcionaba en el banco de antes. Se quitó
igualmente, pero por el motivo correcto: no se puede probar, y un TRAPINT equivocado se traga
la interrupción. Si alguien lo retoma, con las manos en un terminal de verdad.

### El modo pendiente de zsh no se puede pintar

Al pulsar un operador (`c`, `d`, `y`) zsh lee la siguiente tecla **dentro del widget**, sin
volver al bucle: no dispara `zle-keymap-select` ni `zle-line-pre-redraw`, así que no hay dónde
repintar. La tira se quedaba en NORMAL mientras el chuletario tenía un modo entero para eso.

Comprobado conduciendo una shell de verdad y mirando la pantalla. `showIn` ya no lo incluye y
el modo se llama «OBJETOS»: es la referencia de `claude-keys`, no una tira.

### Las teclas sintéticas no son «físicas» para AutoHotkey

Y eso marca el límite de lo que se puede probar desde aquí. `GetKeyState("Space", "P")` responde
«arriba» para una pulsación inyectada con `keybd_event`, así que **el gesto de mantener
`Alt+Space` para recuperar el menú de ventana no es verificable por sonda**: ni se puede
demostrar que va, ni que no va. Con una mano de verdad debería ir.

Lo que sí se midió y se arregló: sin el prefijo `$` en el atajo, AutoHotkey lo registra por la
vía rápida y **no instala el hook de teclado**, con lo que el estado físico no se rastrea de
ninguna manera y `KeyWait` vuelve al instante. Ahora lleva `$`, y el auto-test comprueba que
sigue ahí.

Por lo mismo existe la tecla `m` del mapa raíz: hace lo mismo, se ve en la banda y **sí** se
verifica —comprobado que cierra la banda y abre el `#32768` del sistema—.

### El modo visual de zsh no cambia `$KEYMAP`

Sigue diciendo `vicmd` y usa el keymap `visual` como una capa por encima; `zle-keymap-select`
ni se entera. Lo que hay que mirar es **`$REGION_ACTIVE`**, y en `zle-line-pre-redraw`, que es
el único gancho que corre al activarse la región. Con `reset-prompt` ahí dentro hay que
comparar el modo anterior o se llama a sí mismo sin parar.

Lo mismo de fondo: `visual` y `viopp` son capas finas sobre `vicmd`. Una tecla que no esté en
ellas se resuelve abajo, y por eso `bindkey -M viopp w` dice «undefined-key» mientras `dw`
funciona perfectamente. El auto-test tiene que preguntar a los dos mapas.

### El id de un mod no sirve para buscarlo

Windhawk busca por **nombre**. `taskbar-start-button-position` no devuelve nada; el mod se
llama «Start button always on the left». Por eso existe `windows/mods.json`, y el
instalador para en seco si añades un mod al código sin su ficha.

## Pendiente y sin verificar

### Sección 08 — aplicado pero nadie lo ha visto

La previsualización de la barra y el Alt+Tab. Los tres targets están en el registro y salen
del catálogo del mod, pero solo aparecen con interacción real y `keybd_event` no las abre.
**Pasar el ratón por un icono de la barra y probar Alt+Tab.**

### Los iconos de eza, apagados a propósito

No es que fallen: `Cascadia Code` no tiene glifos en la zona de uso privado
(`U+E000`–`U+F8FF`) y con `--icons` sale un `?` por fichero. El interruptor vive en
`palette.json` → `font.nerdGlyphs`, hoy en `false`. Para encenderlos hace falta instalar
**Cascadia Code NF** (de las releases de Microsoft; no está en winget) y poner `face` y
`nerdGlyphs` acordes.

### Android Studio se queda con su icono

De los tres anclados de esta máquina —Android Studio, File Explorer, Google Chrome— el
primero no está en `icons.APPS` y el instalador lo dice y sigue:

```
[dry] Android Studio: sin glifo asignado en icons.APPS, lo dejo
```

**No es un fallo: el diseño especifica siete glifos y ese no es uno.** Añadirlo obliga a
inventarse glifo y rol, que es justo lo que este repo lleva evitando. Si algún día se
quiere, la decisión es de diseño y la línea va en `lib/icons.py`, en `APPS`.

### Los atajos de ventanas: probados por sonda, no a mano

La banda, su posición y sus colores se midieron **en captura de pantalla**: `x=530 y=986
w=860 h=34` sobre un área de trabajo de 1920×1030, o sea centrada y pegada justo encima de la
barra; fondo `#07090A` y borde `#1A2026`, los de la paleta. El icono de bandeja y el submapa
`w` también se verificaron por sonda.

Y la ruta del atajo entera, con teclas inyectadas: `Alt+Space` abre la banda (860 px), `w` pasa
al submapa (780 px), `Esc` vuelve al raíz, `d` abre el de escritorios y `Esc Esc` sale. Incluido
el caso de teclear con Alt todavía pulsado, que antes se perdía.

Lo que **no** se ha probado con las manos: `h j k l` moviendo el foco entre ventanas reales,
`H J K L` repartiendo mitades, y el salto a un escritorio virtual concreto. La lógica está
escrita y el script carga limpio, pero eso no es lo mismo que haberlo usado. **Pruébalo un
rato antes de fiarte.**

El salto al escritorio N lee el registro (`VirtualDesktops\CurrentVirtualDesktop` contra
`VirtualDesktopIDs`, 16 bytes por GUID) porque no hay API pública: la `IVirtualDesktopManager`
que la tiene cambia de IID en cada build de Windows. Devolvió 4 correctamente en esta máquina.
Si algún día devuelve 0, la banda lo dice y no hace nada — anterior y siguiente siguen yendo,
que esos son atajos del sistema.

### La tira y el scrollback

Dos fallos que solo aparecen usando la shell, no leyendo el código, y que están arreglados:

- Ejecutar una orden desde NORMAL dejaba **las tres filas de la tira clavadas en el
  scrollback**, para siempre. Ahora `zle-line-finish` la borra y repinta antes de que la línea
  se acepte.
- Tras ejecutar, el prompt siguiente **seguía en NORMAL**: zsh conserva el keymap entre
  líneas. `zle-line-init` hace ahora `zle -K viins`. En una shell, lo que quieres al ver un
  prompt nuevo es escribir.

Queda uno sin arreglar y a propósito: abortar con **Ctrl+C** desde NORMAL sí deja la tira en el
scrollback, porque `zle-line-finish` no corre con un SIGINT. Ver la sección del pty.

### Tests: los hay para el shell, no para Windows

`./install.sh --self-test` comprueba 63 invariantes del shell y del render, bajo un pty de
verdad. Sale con código 1 si algo falla.

De los atajos cubre lo que se puede cubrir desde aquí: que cada tecla anunciada en el
chuletario está atada de verdad —se le pregunta a `bindkey`—, que la tira aparece y calla en
los modos que toca, y que AutoHotkey **carga** el script generado sin errores. Lo que no cubre
es que los atajos de ventana hagan lo correcto; para eso hacen falta ventanas.

Lo que **sigue** sin cobertura es todo el lado Windows: los selectores XAML de Windhawk, la
barra, el Explorador. Eso se verificó midiendo píxeles a mano sobre capturas y no viaja al
repo — quien cambie un selector sigue sin forma automática de saber si lo rompió.

### Fondo de escritorio y bloqueo — descartados a propósito

Secciones 09 y 10 del diseño. El usuario prefiere el fondo que tiene. La retícula de 25 px
sobre `#07090a` con dos halos está especificada si algún día se quiere.

## Para retomarlo

> **El repo se llama `windows-configuration`, no `claude-terminal-theme`.** Ese sigue
> siendo el nombre del tema y el de las rutas locales —`~/.config/claude-terminal-theme/`,
> el snapshot, los iconos en `%LOCALAPPDATA%`—, que **no** se renombraron a propósito: el
> snapshot ya instalado vive en la ruta vieja y moverla rompe el `--uninstall` de las
> máquinas que ya tienen el tema puesto. Solo cambiaron las URL de GitHub.
>
> El remoto usa el alias `github.com-iesebre` del `~/.ssh/config`, que es el que lleva la
> clave correcta. Con `git@github.com:` a secas coge la clave por defecto y falla.

```bash
# máquina nueva, de cero
curl -fsSL https://raw.githubusercontent.com/gabrielurs/windows-configuration/main/bootstrap.sh | bash

# ver qué haría sin tocar nada — la forma sensata de estrenar máquina
./install.sh --dry-run

# solo una parte — esto salta todo menos los mods de Windhawk
python3 lib/apply_windows.py --skip wt,vscode,ps,accent,taskbar,menu,icons,launcher

# volver al estado anterior a conocer este repo
./install.sh --uninstall
```

El snapshot vive en `~/.local/share/claude-terminal-theme/`, **fuera del repo y a
propósito**: cada máquina guarda su propio «antes», y llevarte el de otra es justo lo que
rompe la marcha atrás.

AutoHotkey v2 se instala con winget y el instalador lo ofrece; el script se copia a
`%LOCALAPPDATA%\claude-terminal-theme\` junto a sus dos iconos y el fichero del interruptor,
y arranca solo desde la clave `Run`. `--uninstall` lo para antes de borrar nada, por lo mismo
que con Flow y con explorer.

Los mods de Windhawk son el único paso manual — Windhawk los compila en local desde su
interfaz y no expone CLI. El instalador detecta cuáles faltan y los lista con su nombre
buscable y su URL.

## Un detalle que no está en el código

**El acento no es del todo nuestro.** Windows lo recalcula según el fondo de pantalla, así
que tras un `--uninstall` puede no coincidir con lo que guardó el snapshot. Salió en la
prueba de ida y vuelta: la restauración escribió el `#D0000C` que guardó por la mañana, y
Windows lo cambió después porque el fondo ya era otro. No es un fallo de la restauración.
