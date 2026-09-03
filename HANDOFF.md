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
| snapshot | 84 entradas — 14 ficheros, 60 valores, 10 claves completas |
| mods de Windhawk | 10 configurados, 178 ajustes |
| rama de git | servicio activo en `127.0.0.1:8756` |
| buscador | Flow Launcher, tema `ClaudeCLI`, `Ctrl+Space` |
| acento | `#4DD6C1` con `ColorPrevalence=0` |

## Hecho, por superficie

| superficie | qué lleva |
|---|---|
| barra | 50 px, iconos a 24, esquinas superiores a 14, un icono por app sin etiqueta, Inicio a la izquierda con el chevron teal |
| reloj | dos líneas con segundos, día abreviado, cpu/ram y la rama de git del repo donde tienes la shell |
| Explorador | un solo tono `#191919`; panel de detalles y barra de estado eliminados, no recoloreados |
| ventanas | borde teal en la activa, gris en las inactivas, sin pintar la barra de título |
| Inicio y notificaciones | opacos — filtraban el fondo de pantalla |
| buscador | flotante, centrado, con la paleta generada desde `palette.json` |

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

### No hay tests

Todo se verificó midiendo píxeles a mano sobre capturas. Eso no viaja al repo: quien cambie
un selector no tiene forma automática de saber si lo rompió.

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

Los mods de Windhawk son el único paso manual — Windhawk los compila en local desde su
interfaz y no expone CLI. El instalador detecta cuáles faltan y los lista con su nombre
buscable y su URL.

## Un detalle que no está en el código

**El acento no es del todo nuestro.** Windows lo recalcula según el fondo de pantalla, así
que tras un `--uninstall` puede no coincidir con lo que guardó el snapshot. Salió en la
prueba de ida y vuelta: la restauración escribió el `#D0000C` que guardó por la mañana, y
Windows lo cambió después porque el fondo ya era otro. No es un fallo de la restauración.
