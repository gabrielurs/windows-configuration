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
| auto-test | **75/75**, con el chuletario contrastado contra `bindkey` |
| navegación | fzf-tab en Tab, `cdpath` + `~p`, Alt+↑ ← →, listado al entrar, ruta relativa al repo — 15 de septiembre |
| fuente | Cascadia Code NF por usuario; un proceso nuevo la ve (medido con GDI+) |
| snapshot | 84 entradas — 14 ficheros, 60 valores, 10 claves completas |
| mods de Windhawk | 12 configurados, 194 ajustes (16 de noviembre: + bandeja y volumen) |
| rama de git | servicio activo en `127.0.0.1:8756` |
| buscador | Flow Launcher, tema `ClaudeCLI`, `Ctrl+Space` |
| acento | `#4DD6C1` con `ColorPrevalence=0` |
| atajos | modo vim en zsh y AutoHotkey v2 en `Alt+Space`, banda medida en pantalla |

## Hecho, por superficie

| superficie | qué lleva |
|---|---|
| barra | 50 px, iconos a 24, recta (a 14 dejaba cuñas del fondo arriba), un icono por app sin etiqueta, Inicio a la izquierda con el chevron teal; sin lupa; bandeja sin red ni volumen y volumen con la rueda (dos mods que se instalan a mano) |
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

### La barra: los selectores con estado del README del mod no casan (build 26200.9974)

`Taskbar.TaskListLabeledButtonPanel@CommonStates > Border#BackgroundElement` y
`…@RunningIndicatorStates > Rectangle#RunningIndicator` son literalmente los ejemplos del
README de Taskbar Styler 1.8, y aquí **no pintaban nada**: indicadores en el gris de
Windows (`#868686`), botón activo en la tarjeta blanca de serie (`#F9F9F9`), el tinte de
Inicio a 0 píxeles. Nadie lo había mirado en claro. Cuatro sondas de colores chillones, el
2026-11-16:

```
✓ Rectangle#RunningIndicator                                   (a secas)
✓ Taskbar.TaskListButton > * > Rectangle#RunningIndicator
✓ Taskbar.TaskListButton > * > Border#BackgroundElement
✓ …#LaunchListButton[AutomationProperties.AutomationId=StartButton] > * > Border#BackgroundElement
✗ Taskbar.TaskListLabeledButtonPanel > …   ✗ Taskbar.TaskListButtonPanel > …   (directo o con > * >)
✗ Taskbar.TaskListButton@CommonStates > * > …     ✗ …StartButton] > TaskListButtonPanel > Border
```

Un `Background` sin estado sí pinta, pero igual en reposo, hover y activo. La salida fue no
pelear con los estados: **sobrescribir los pinceles que usa la plantilla** con
`themeResourceVariables`. Los nombres salen de `resources.pri` de
`MicrosoftWindows.Client.Core` (`strings -el`), y cuál pinta qué, de otra sonda:

| recurso | pinta |
|---|---|
| `RunningIndicatorBrush` | indicador de app abierta |
| `RunningIndicatorActiveBrush` | indicador de la activa |
| `ShellTaskbarItemFillColorSecondaryBrush` | fondo del botón activo (también con hover) |
| `ShellTaskbarItemFillColorAltSecondaryBrush` | hover sobre uno inactivo |
| `ShellTaskbarItemFillColorTertiaryBrush` | pulsado, activo o no |
| `RequestingAttentionBrush` · `…HoverBrush` · `…PressedBrush` | fondo del aviso: reposo, hover, pulsado |
| `RunningIndicatorRequestingAttentionBrush` | indicador del aviso |

`Primary` no sale en ningún estado; no se toca. El aviso y la pulsación se midieron con una
ventana de prueba propia (WinForms, `FlashWindowEx`) para no tocar las del usuario: en ámbar
al 15/20 % salen exactos (`#E2DED0`, `#DCD6C3`). El color final de la pulsación normal no se
llegó a ver: con clics sintéticos el estado no siempre se dispara. **Los recursos solo
se aplican al reiniciar explorer**, no en caliente como los `controlStyles`. UI Automation
no sirve para sacar clases: da la del *automation peer* (`ToggleButton`,
`TaskListButtonAutomationPeer`), no la XAML.

### Integración con Windows Terminal: medido en pty, sin ver en pantalla

16 de noviembre. Conduciendo un zsh interactivo con `WT_SESSION` puesto, el prompt emite lo
esperado: `133;A`/`133;B` alrededor del prompt, `133;C` al lanzar, `133;D;0` y `133;D;1`
según el código, `133;D` a secas tras un Intro en vacío, y `9;9;\\wsl.localhost\Ubuntu\…`
solo al cambiar de carpeta (también con Alt+↑, que no acepta línea). Con `TMUX` o sin
`WT_SESSION`, nada.

**Visto en una ventana de verdad** (16 de noviembre, ventana propia `sonda-claude`, teclas
con `SendKeys` solo si esa ventana tenía el foco, capturas con `PrintWindow`):

- `Ctrl+Mayús+O` + `Ctrl+C` copia la salida del último comando (`MARCA-UNO`).
- `Ctrl+↑` salta **una** vez por prompt —el `A B A B` del doble pintado no duplica marcas—
  y `Ctrl+↓` vuelve.
- Duplicar panel NO heredaba la carpeta: el perfil que trae WSL (fragmento
  `Fragments\Microsoft.WSL\{guid}.json`) arranca con `wsl.exe --distribution-id … --cd ~`,
  y ese `--cd ~` manda sobre el cwd. `apply_wt` lo sobrescribe sin él y con
  `startingDirectory: "~"`. Después: pestaña nueva en `/home/it`, panel duplicado tras
  `cd /usr/share` en `/usr/share`.
- tmux al abrir: la pestaña entra sola (sesión nueva, `attached=1`,
  `destroy-unattached=on`, cliente con RGB). Dentro, conducido con `tmux send-keys`: prompt en
  color de 24 bits, `✗1`, cronómetro, Alt+↑, la tira al pulsar Esc, fzf-tab con su vista
  previa, Ctrl+R, eza con iconos, y la barra del cursor en INSERT (en captura).

Trampas de la sonda, para no repetirlas: un `{ESC}` deja zsh en NORMAL y lo siguiente que
se teclea son órdenes de vim; `-p` con el guid del perfil **oculto** `{2c4de342…}` abre
`cmd`, no Ubuntu; y cerrar ventanas **por título** es peligroso —el título cambia a
«Ubuntu» al enfocar otro panel, y así se llama cualquier ventana del usuario—: por `hwnd`.

**Trampa del auto-test:** `clean_pty` quitaba los OSC de un solo dígito. Con las marcas
(OSC 133) dentro, la sonda leía `]133;C` como datos y daba 32 fallos que no eran de la
shell. Si el auto-test se hunde entero tras tocar el prompt, mirar primero el limpiador.

**El cursor por modo ya existía** (`_claude_keys_cursor`, DECSCUSR 6 en INSERT y 2 en
NORMAL; comprobado en pty). Dentro de tmux no pasaba —el terminfo de `xterm-256color` no
trae `Ss`/`Se`—; el `tmux.conf` generado lo arregla con un `terminal-overrides`.

Sin tocar: `defaultProfile` apunta al perfil Ubuntu **oculto** (`{2c4de342…}`, origen
`Windows.Terminal.Wsl`); el visible es `{c6ccfc00…}` (origen `Microsoft.WSL`). Funciona,
pero el que se abre al arrancar no es el que sale en el menú.

### Auditoría de lo que quedaba fuera del tema (16 de noviembre)

Paneles del sistema, medidos abriéndolos un instante y contando colores sin guardar la
imagen: ajustes rápidos `#F3F3F3` 88 %, avisos y calendario 96 %, Inicio/búsqueda 87 %,
Ejecutar en blanco y `#F3F3F3`. Brave, Edge y Thunderbird siguen al sistema.

Lo que sí estaba fuera, y se arregló:

- **VS Code.** El repo daba por hecho un workbench oscuro (Abyss) y le pintaba terminal y
  panel en `#07090A`; el usuario lo tiene en «Visual Studio Light». Ahora hay `vscodeMode`.
  Iban además dos colores escritos a mano para oscuro (`#0F1F24`, y la rampa honda del
  acento en las coincidencias de búsqueda). Comprobado en `settings.json`, **no en
  pantalla**: no se capturó VS Code por si tenía abierto un proyecto de cliente.
- **Consola clásica (conhost).** `HKCU\Console`: tabla de 16 colores en el orden de
  Windows —azul en el 1, rojo en el 4—, `DefaultBackground`/`DefaultForeground` y fuente.
  Visto en captura con `conhost.exe powershell`: fondo `#F3F3F3`, colores de la paleta. Las
  subclaves de PowerShell, que traían su azul de siempre, heredan el fondo nuevo.

Sin tocar: la app Configuración (hay mod, `windows-11-settings-styler`), el primer perfil
de Chrome (tema de extensión propio) y el segundo monitor —el escritorio mide 3000×1920—,
cuya barra no se ha mirado y donde no sale la tira de AutoHotkey.

### La barra a 36 px: lo que costó

16 de noviembre, medido sobre capturas del rectángulo de `Shell_TrayWnd`:

- A 36 px con el icono a 20, los botones de aplicación quedan centrados solos, pero **la
  bandeja entera sale 7 px alta**: flecha, iconos y reloj. Con dos líneas, la de arriba se
  cortaba contra el borde.
- `Margin` sobre `Grid#SystemTrayFrameGrid` **no movió nada**. Lo que funcionó:
  `RenderTransform:=<TranslateTransform Y="7" />` sobre `SystemTray.SystemTrayFrame`. Tinta
  del reloj tras el cambio: filas 13 a 22 de 36.
- El reloj en una línea: `BottomLine` vacío y `TextBlock#DateInnerTextBlock` con
  `Visibility=Collapsed`.
- cpu · ram · rama a la izquierda: el mod del reloj no puede pintar fuera del reloj. Es un
  `Gui` de AutoHotkey (`ClaudeStats`) con `WS_EX_NOACTIVATE | WS_EX_TRANSPARENT`, recolocado
  y devuelto a «siempre encima» cada 2 s —la barra se le pone delante cada vez que se
  activa—, y escondido con una ventana a pantalla completa. Con `stats.allMonitors` hay
  uno por barra (`Shell_TrayWnd` y cada `Shell_SecondaryTrayWnd`), creado al ver la barra y
  destruido cuando desaparece; visto en captura en las dos pantallas (2026-11-16). El
  escondido es por pantalla. Sin probar: pantalla completa de verdad, y enchufar o quitar
  un monitor con el script en marcha.

**Aviso de comando largo (2026-11-17).** `bellStyle: taskbar` solo dejaba la campana en la
pestaña; el icono no parpadeaba. La barra SÍ sabe pintar el parpadeo (probado con
`FlashWindowEx` sobre una ventana propia: fondo tostado y raya ocre). Ahora la shell deja
`%LOCALAPPDATA%\claude-terminal-theme\notify` («tiempo<tab>comando») y `ReadNotify()` en
`claude-keys.ahk` saca un `TrayTip` y llama a `FlashWindowEx` sobre las ventanas de Windows
Terminal, solo si el terminal no está en primer plano. Visto: la nota se escribe y se
consume, y el `TrayTip` sale. Sin ver: el camino entero con el terminal en segundo plano.

**Reinicios del shell, lo medido el 2026-11-17.** El evento 1002 de Winlogon sale también
cada vez que algo mata explorer a propósito: el 16 hubo dieciséis, trece de ellos por la
mañana. De los tres de la tarde no hay evento 1000 ni 1001: explorer no cayó con fallo, salió
o lo terminaron. Ningún mod instalado llama a `TerminateProcess` sobre explorer (el de la
barra solo ofrece reiniciarlo con un diálogo). Hipótesis, sin probar: la recarga de un mod de
la barra al cambiarle los ajustes hace salir a explorer.

**`explorer.exe /factory,{75dff2b7-…} -Embedding` huérfanos.** Cada ventana del Explorador
abierta con `explorer.exe <ruta>` deja uno, de ~125 MB, que no se va al cerrarla. Había
nueve sin ventana; cerrados con `Stop-Process` sin tocar el shell (el que no lleva
`/factory`).

**Los reinicios del shell al importar no son sistemáticos.** Tres importaciones seguidas de
«El shell se detuvo inesperadamente» (12:54, 14:21, 14:27) y luego tres sin él (14:33,
14:34, 14:35). Las tres primeras cambiaban el mod nuevo, el contenedor del Explorador y el
alto de la barra; las otras, solo estilos. Hipótesis, sin comprobar: lo provoca cambiar
algo estructural, no el import en sí. Quedan además seis `explorer.exe` de las 9:48 sin
ventana, a ~125 MB cada uno.

### La cabecera de las ventanas: qué se pudo bajar y qué no

16 de noviembre, medido con `PrintWindow` sobre ventanas propias:

```
Explorador        136 → 87 px hasta la lista   sin barra de comandos (tema NoCommandBar del mod)
ventana clásica    39 → 35 px no cliente        iCaptionHeight 22 → 18 (SPI_SETNONCLIENTMETRICS)
Windows Terminal   40 px de pestañas, fijos     o nada, con Alt+F11
```

`explorerFrameContainerHeight` es un AJUSTE del styler, no solo un campo de sus temas: sin
ponerlo a 87 queda el hueco de la barra. El borde (`iPaddedBorderWidth`) no se tocó: es la
zona de agarre para redimensionar. Chrome, VS Code, Slack o Configuración pintan su propia
cabecera y no hay ajuste global que les llegue.

**Ojo:** un minuto después de importar el cambio del Explorador con una ventana suya
abierta, el registro de eventos apuntó «El shell se detuvo inesperadamente y se reinició»
(14:21:34) y esa ventana desapareció. El explorer de las 9:48 siguió vivo, una ventana
nueva abrió bien y no se repitió en las pruebas siguientes; no se sabe si fue el cambio en
caliente o la ventana de prueba. Si se repite al aplicar, aplicar sin ventanas abiertas.

### La franja de pestañas: título y ancho, no alto

16 de noviembre. De 7 pestañas del usuario, 4 se llamaban «Ubuntu»: el fragmento de WSL
trae `suppressApplicationTitle: true`. Con `false`, `tabWidthMode: titleLength` y, en tmux,
`set-titles` con `#{?#{==:#{pane_title},#{host}},#W,#T}`, la pestaña enseña (visto en
captura y leído con `tmux display`): `~`, `claude-terminal-theme`,
`claude-terminal-theme · lib`, `share`, `sleep 30`, `✳ Claude Code`.

Dos detalles: oh-my-zsh dentro de tmux pone el NOMBRE DE VENTANA (`\ek…`), no el título
del panel, y por eso la cadena cae a `#W` cuando `#T` sigue siendo el nombre del equipo; y
`_claude_repo_track` va ahora el primero de los precmd, o el título iba un prompt por
detrás de la carpeta.

El alto no se puede tocar: la fila mide 40 px y no hay ajuste. `Alt+F11`
(`toggleFocusMode`) la quita entera: medido, de 30 a 32 filas en la misma ventana.

### Claude Code dentro de tmux baja a 256 colores, y se nota en la statusline

Lo vio el usuario: «el fondo de claude (con el pet) en tmux no se ve bien». Medido con
`tmux capture-pane -e`: dentro de tmux Claude Code mandaba `48;5;255` y `38;5;30` en vez
de `48;2;243;243;243` y `38;2;3;122;108`. El gris 255 es `#EEEEEE`, y la banda de la
statusline salía como una franja más oscura sobre el `#F3F3F3` (73.450 píxeles en la
captura); los roles, en su vecino más cercano de la paleta de 256.

No es tmux, es Claude Code: en su binario (2.1.325) está
`if(env.CLAUDE_CODE_TMUX_TRUECOLOR)return; if(env.TMUX&&level>2)level=2`. El `tmux.conf`
generado pone `set-environment -g CLAUDE_CODE_TMUX_TRUECOLOR 1` junto a la línea que
garantiza el RGB. Después: `#F3F3F3` en toda la banda. Solo vale para paneles NUEVOS: una
sesión de Claude ya abierta dentro de tmux sigue en 256 hasta relanzarla en otro panel.

Trampa de la sonda: UI Automation a veces no devuelve una ventana de Windows Terminal
recién creada (`FindAll` daba 3 de 5). `EnumWindows` sí; las capturas van ya por `hwnd`.

### Segunda tanda del terminal (16 de noviembre): qué se vio y qué no

Visto en captura de una ventana propia: btop, vim y man con la paleta; lazygit también,
con los títulos de panel subidos de `border` a `ghost` porque en `#E5E5E5` no se leían.
Conducido con `tmux send-keys -K` —que pasa por las tablas de teclas, no directo al
panel—: `Ctrl+B %` y `Ctrl+B c` abren en la carpeta del panel, y en modo copia `v … y` deja
la selección en el búfer. El timbre, en pty: uno con el umbral superado, ninguno por debajo.

`Win+º` baja el desplegable (ventana nueva de 1936×519 pegada arriba, con Ubuntu y tmux
dentro). **Sin confirmar:** que la segunda pulsación lo esconda —`IsWindowVisible` seguía
en true dos segundos después, que puede ser la animación o el modo de ocultar— y que el
icono parpadee de verdad en la barra con el timbre.

`defaultProfile` apuntaba al Ubuntu que el fragmento de WSL oculta (`updates` + `hidden`):
un perfil sin comando, o sea `cmd.exe`. Se vio abriendo una pestaña sin `-p`. `apply_wt`
lo redirige al perfil del fragmento.

### tmux al abrir pestaña: probado en pty, no en una pestaña de verdad

16 de noviembre, `shell/claude-05-tmux.zsh`. Conduciendo un zsh interactivo: con
`WT_SESSION` entra en tmux con `destroy-unattached on`, y al salir la shell de fuera termina
y la sesión desaparece; bajo `CLAUDECODE`, fuera de Windows Terminal o con el interruptor en
`off`, no arranca; y si tmux falla (probado sin tty: «open terminal failed») la shell sigue
con todas las capas y lo dice. Arranque medido: 0,43 s frente a 0,36 s.

Decidido por el usuario: la sesión muere con la pestaña. Consecuencia sabida: `orq up`
desde una pestaña así cae en su rama «ya estoy en tmux» y el equipo de echo muere al
cerrarla, en vez de sobrevivir en `orq-<carpeta>`.

**Trampa:** el `tmux.conf` solo se lee al arrancar el SERVIDOR. Con uno ya vivo, una
sesión nueva sale con la configuración vieja —se vio: `mouse off`, historial 2.000— hasta
un `tmux source-file` o hasta que muera el servidor. Y `history-limit` solo vale para
paneles nuevos.

### El puntero: «Negro» no es negro moderno, y solo Configuración genera los cursores

Medido el 16 de noviembre dibujando los cursores del sistema (`LoadCursor` + `DrawIconEx`):

```
Blanco         aero_*.cur / .ani, 136 KB          el de serie
Negro          *_r.cur, 8 KB, esquema «Windows Black»   los de Windows 95; Hand queda vacío
Personalizado  %LOCALAPPDATA%\Microsoft\Windows\Cursors\*_eoa.cur, 136 KB, CursorType=6
```

Solo «Personalizado» da un puntero oscuro con la forma moderna, y los `*_eoa.cur` los
genera la página de Configuración: no hay API ni valor que lo dispare (la búsqueda tampoco
dio una vía documentada). `lib/pointer.py` la conduce con UI Automation —patrones, no
teclas—: pasa por «Blanco», escribe `CursorColor` (COLORREF, BGR) y elige «Personalizado»;
elegir lo ya elegido no regenera. La vuelta atrás es `SPI_SETCURSORS` con el flag **2**:
con 3 devuelve FALSE sin código de error. Coste del estilo: «ocupado» es un reloj de arena
fijo —un .cur no se anima— y «prohibido» pierde el rojo.

### El tema con nombre no puede ser el «actual» sin aplicarlo

`Claude Light.theme` sale en la galería, pero «Tema actual» sigue en «Personalizado»:
apuntar `CurrentTheme` a la copia no aguanta, Configuración lo devuelve a `Custom.theme`
al abrir la página de Temas (medido). Aplicarlo de verdad reescribe fondo y colores; no
se hace.

### Inicio abre Flow: para probarlo, tiempos de mano, no de máquina

Win sola, Win+S y el clic en el botón de Inicio abren Flow (`claude-keys.ahk`, sección
«Inicio abre Flow»). El Inicio de Windows sigue en Mayús+clic y Ctrl+Esc. Medido el 16 de
noviembre, viendo qué proceso queda en primer plano: Win → Flow, Win+S → Flow, Win+B →
la barra (las combinaciones siguen), clic → Flow, Mayús+clic → `SearchHost`, Ctrl+Esc →
`SearchHost`.

**La trampa:** con `keybd_event` bajando y subiendo Win en el mismo instante, Inicio se
abría igual. El `vkE8` que lo enmascara lo manda el hilo del script, y llega cuando Win ya
está suelta. Con 90 ms entre bajar y subir —una mano— va. Antes de dar por roto un atajo
de esta sección, mirar los tiempos de la prueba. Y otra: el `FileAppend` a fichero de un
script lanzado con `Start-Process` no dejaba rastro; con `/ErrorStdOut` y `"*"` sí.

### Tipografía del terminal: lo que no era lo que parecía

- `font.cellHeight` **por defecto no es 1.0**: es la altura natural de la fuente, que en
  Cascadia es 1.162 em (17 px a 11 pt), y el schema de Windows Terminal dice que «suele
  quedar muy cerca de 1.2». Poner 1.2 apenas cambia 1 px. Va en 1.3: 19 px.
- La cursiva caligráfica (`ss01`) solo la trae `CascadiaCodeNFItalic.ttf` —mirado con
  fontTools—, así que `features: {ss01: 1}` no toca el texto recto.
- `bat` no pinta cursivas si no se le pide (`--italic-text=always`), y solo admite por
  entorno `BAT_THEME`, `BAT_STYLE`, `BAT_PAGER` y `BAT_PAGING`: el flag va en el alias y en
  las vistas previas de fzf. `delta` usa el tema de bat pero ignora su cursiva.
- delta no lee una caché de bat aislada con `BAT_CACHE_PATH`: para probar un tema nuevo con
  delta hay que instalarlo de verdad (`bat cache --build`).

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

### PowerShell por stdin no ejecuta un here-string, y no lo dice

`powershell.exe -Command -` con el script en stdin lee **línea a línea**: un `@' … '@` de
varias líneas se rompe y no sale **nada**, ni por stdout ni por stderr. Así el paso de la fuente
daba por no instalada una fuente que sí lo estaba. La vía buena es `-EncodedCommand` con el
script en UTF-16LE y base64 (`_powershell()` en `apply_windows.py`). Su stderr trae un CLIXML de
progreso —«Preparando módulos para el primer uso»— que no es un error.

Y la verificación va en **otro proceso**: preguntarle al mismo que acaba de hacer
`AddFontResource` solo demuestra que ese proceso la tiene cargada.

### AUTO_CD sí mira cdpath — en la shell de verdad

Probado primero con `zsh -f -c '… eval alpha'`: no saltaba, y se llegó a escribir en la capa 20
como «comprobado». Conduciendo un zsh interactivo por pty, `vertex` a secas desde `/tmp` lleva a
`~/projects/vertex`. Mismo aprendizaje que el `emulate -L zsh` de la sonda: **una shell que no
es la interactiva no mide la interactiva**.

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

### Explorador, notificaciones y Flow en claro — medidos el 16 de noviembre

Explorador (PrintWindow de una ventana propia en `C:\Windows\Web\Wallpaper`): cromo
`#F3F3F3`, cajas y lista `#FFFFFF`, líneas `#E5E5E5`, panel de navegación en el blanco del
lienzo Win32. La franja de pestañas sale `#E8E8E8` en PrintWindow; en pantalla no se pudo
medir limpia (otras ventanas encima). Centro de notificaciones: fondo `#F3F3F3`, tarjetas
`#F6F6F6`, texto `#1B1B1B`, ni rastro del oscuro. Flow: caja `#F3F3F3`, selección `#C8DDDB`.

### Hover y pulsado de la barra: la sonda sintética no los dispara

Segundo intento, 16 de noviembre, con ventana de prueba propia: `SetCursorPos` sobre su
botón y captura a 1,6 s → ni un píxel distinto del reposo (`#F3F3F3`), y tampoco aparece
la previsualización. Con `mouse_event` de botón abajo, el icono desaparece del hueco
(parece el arrastre para reordenar) y no se ve fondo de pulsado. No distingue «no pinta»
de «la sonda no llega»: **pasar el ratón y hacer clic con la mano**. Lo esperado por
cálculo sobre `#F3F3F3`: hover `#E5E5E5`, activo `#D4E3E2`, pulsado `#C3DBD8`.

### Sección 08 — aplicado pero nadie lo ha visto

La previsualización de la barra y el Alt+Tab. Los tres targets están en el registro y salen
del catálogo del mod, pero solo aparecen con interacción real y `keybd_event` no las abre.
**Pasar el ratón por un icono de la barra y probar Alt+Tab.**

### Los iconos y Alt+flechas, sin ver en Windows Terminal

Encendidos desde el 15 de septiembre: el paso `font` de `apply_windows.py` instala **Cascadia
Code NF** por usuario y `nerdGlyphs` va en `true`. Medido: los TTF y los valores de `HKCU`
están, y un proceso **nuevo** lista la familia. Lo que **no** se ha visto es la pantalla de
Windows Terminal reiniciado con la fuente puesta. **Cerrar WT, abrirlo y hacer un `ls`.**

Alt+↑ ← → se probaron conduciendo un zsh interactivo por pty: los tres widgets mueven el
directorio a través de ZLE. Lo que no se ha probado es que Windows Terminal deje pasar la
tecla: de serie la ata a mover el foco entre paneles, y con un solo panel **debería** llegar
a la shell. **Pulsarlas en una pestaña sin partir.**

fzf-tab se comprueba atado y cargado, pero su ventana no: bajo el pty de los tests fzf no
llega a pintarse (ver la sección del pty). **Un `cd ~/projects/<Tab>` a mano.**

### Los glifos de los anclados, apagados

Desde el 16 de noviembre `pinnedIcons` va en `stock`. Los glifos solo llegaban a los
anclados de `icons.APPS`: Android Studio no está, y lo que se abre sin anclar —Brave,
Slack, Thunderbird, Terminal— pone el suyo. La barra quedaba **siempre** mitad glifo, mitad
icono de color (medido: 2 y 4), y el usuario eligió todos de serie. `glyphs` sigue en el
código por si se quiere volver.

**Trampa: quitar un glifo no se ve en una app abierta y agrupada con su anclado.** El
Chrome anclado siguió morado con el `.lnk` ya devuelto a `chrome.exe,0` tras
`ie4uinit -show`, tras `ie4uinit -ClearIconCache` y tras reiniciar explorer dos veces. La
ventana daba su logo de siempre (`WM_GETICON`) y el blob `Favorites` no guarda rutas de
icono. Lo que lo arregló: borrar `%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache_*.db`
**con explorer parado** — `-ClearIconCache` no los toca mientras explorer los tiene
abiertos (`iconcache_256.db` seguía con la hora de antes).

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

### Fondo de escritorio y bloqueo

Secciones 09 y 10 del diseño. En oscuro siguen descartadas: el usuario prefería su fondo, y
la retícula de 25 px sobre `#07090a` con dos halos está especificada si algún día se quiere.

En claro sí (16 de noviembre, elegido por el usuario): `ThemeD\img33.jpg`, el mismo Bloom en
verde salvia, en escritorio y bloqueo. Va por `SystemParametersInfo` y por
`LockScreen.SetImageFileAsync`. La imagen de bloqueo de antes está en el snapshot como
`lockscreen-original.png` — era un PNG aunque el original fuera `.jpg`: la API da una copia
recodificada, y por eso tampoco hay forma barata de saber si ya está puesta y se escribe
siempre.

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
python3 lib/apply_windows.py --skip font,wt,vscode,ps,accent,taskbar,wallpaper,pointer,menu,launcher,keys,icons,theme

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

Los mods de Windhawk ya no son un paso manual (16 de noviembre): `lib/mods.py` los baja
compilados de `mods.windhawk.net`, comprueba su huella contra `windows/mods.json` y los
instala con un UAC. La vía sale de leer `installMod` en
`UI\resources\app\extensions\windhawk\dist\extension.js`: Windhawk solo compila en local
si se le pide. Probado quitando `explorer-force-details-columns` y dejando que el
instalador lo repusiera: DLL nueva, huella igual a la ficha, cargada en explorer.

Sin probar: una máquina donde Windhawk no se haya abierto nunca (las bibliotecas
`libc++.whl`, `libunwind.whl` y `windhawk-mod-shim.dll` las copia su interfaz al arrancar;
el script las pone si faltan, pero aquí ya estaban), y los trece mods de golpe.

## Un detalle que no está en el código

**El acento no es del todo nuestro.** Windows lo recalcula según el fondo de pantalla, así
que tras un `--uninstall` puede no coincidir con lo que guardó el snapshot. Salió en la
prueba de ida y vuelta: la restauración escribió el `#D0000C` que guardó por la mañana, y
Windows lo cambió después porque el fondo ya era otro. No es un fallo de la restauración.
