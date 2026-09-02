#!/usr/bin/env python3
"""Configuración de los mods de Windhawk, derivada de palette.json.

Windhawk guarda los ajustes de cada mod en HKLM, así que escribir aquí exige
elevación: se genera un .reg y se importa con UAC.

Los dos mods tienen que estar YA instalados desde la interfaz de Windhawk. Este
módulo no instala mods, solo los configura; si no están, avisa y no toca nada.

Base elegida, según el diseño «Tema Windows Claude CLI»:
  · barra  → SIN tema base (theme=""), todo en controlStyles propios: ancho
             completo, pegada abajo, esquinas redondeadas solo arriba. No es el
             dock flotante de antes; el diseño pide barra siempre visible.
  · inicio → tema integrado «TranslucentStartMenu», que expone $CommonBgBrush
             justamente para esto
  · reloj  → taskbar-clock-customization, dos líneas (hora sobre fecha) y las
             métricas de cpu/ram, que el mod trae de serie

Ojo con los selectores: el botón de Inicio se localiza por
`AutomationProperties.AutomationId=StartButton` y NO por `Name=Start`, porque el
Name está traducido y en un Windows en español no casaría nunca.
"""
from __future__ import annotations
import json, pathlib, subprocess, time

MANIFEST = pathlib.Path(__file__).resolve().parent.parent / "windows/mods.json"

TASKBAR_MOD = "windows-11-taskbar-styler"
CLOCK_MOD = "taskbar-clock-customization"
EXPLORER_MOD = "windows-11-file-explorer-styler"
COLUMNS_MOD = "explorer-force-details-columns"
NOTIF_MOD = "windows-11-notification-center-styler"
START_MOD = "windows-11-start-menu-styler"
STARTPOS_MOD = "taskbar-start-button-position"
STARTICON_MOD = "start-button-replacer"
BORDER_MOD = "win11-accent-border"
MODS_KEY = r"HKLM\SOFTWARE\Windhawk\Engine\Mods"
MODS_HIVE = r"HKEY_LOCAL_MACHINE\SOFTWARE\Windhawk\Engine\Mods"


def catalog() -> dict[str, dict]:
    """{id: entrada} de windows/mods.json."""
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {m["id"]: m for m in data["mods"]}


def missing_report(ids) -> list[str]:
    """Qué decirle a alguien que acaba de clonar esto en otra máquina.

    El id NO sirve para buscar: la pestaña Explore de Windhawk busca por nombre,
    y «taskbar-start-button-position» no devuelve nada. Así que se imprime el
    nombre —lo único que encuentra— y la URL, que sí lleva el id.
    """
    cat = catalog()
    out = []
    for i in ids:
        m = cat.get(i)
        if not m:
            out.append(f"  {i}  (sin ficha en windows/mods.json)")
            continue
        out.append(f"  «{m['name']}» — {m['que']}")
        if m.get("catalog", True):
            out.append(f"      https://windhawk.net/mods/{i}")
        else:
            out.append("      no sale en el catálogo ni en Explore: "
                       "Windhawk → Create new mod → pega este fuente")
            out.append(f"      {m['source']}")
    return out


def argb(hex_: str, alpha: str = "FF") -> str:
    """#RRGGBB → #AARRGGBB, que es el formato de color de XAML."""
    return "#" + alpha.upper() + hex_.lstrip("#").upper()


def installed(mod: str) -> bool:
    r = subprocess.run(["reg.exe", "query", f"{MODS_KEY}\\{mod}"],
                       capture_output=True, cwd="/mnt/c")
    return r.returncode == 0


def enabled(mod: str) -> bool | None:
    r = subprocess.run(["reg.exe", "query", f"{MODS_KEY}\\{mod}", "/v", "Disabled"],
                       capture_output=True, cwd="/mnt/c")
    if r.returncode != 0:
        return None
    return "0x0" in r.stdout.decode("cp850", "replace")


# ── barra de tareas ───────────────────────────────────────────────────
def taskbar_settings(pal: dict) -> dict[str, object]:
    s, ro = pal["surfaces"], pal["roles"]
    g = pal["windowsDesktop"]["taskbar"]
    bg = argb(s["bgAlt"])                 # opaca: el diseño no pide cristal
    edge = argb(s["border"])
    teal = ro["teal"]["hex"]
    r = g["cornerRadius"]

    styles = [
        # el fondo de la barra. Se redondea el Rectangle, no el Grid: al estar
        # pegada al borde inferior, redondear los cuatro lados se ve como
        # redondear solo los de arriba, que es lo que pide el diseño.
        ("Taskbar.TaskbarFrame > Grid#RootGrid > Taskbar.TaskbarBackground > Grid > Rectangle#BackgroundFill", [
            f'Fill:=<SolidColorBrush Color="{bg}" />',
            f"RadiusX={r}", f"RadiusY={r}",
        ]),
        ("Rectangle#BackgroundStroke", [
            f'Fill:=<SolidColorBrush Color="{edge}" />',
        ]),
        ("Taskbar.TaskbarFrame > Grid#RootGrid", [
            f"Padding={g['padding']}",
        ]),
        # Inicio: cuadrado teal tenue. AutomationId y no Name, porque el Name
        # está traducido y en un Windows en español no casaría.
        ("Taskbar.ExperienceToggleButton#LaunchListButton[AutomationProperties.AutomationId=StartButton] > Taskbar.TaskListButtonPanel > Border", [
            f"CornerRadius={g['buttonRadius']}",
            f'Background:=<SolidColorBrush Color="{argb(teal, g["startAlpha"])}" />',
        ]),
        # El botón de cada app. Van los DOS nombres de clase a propósito: con
        # «nunca combinar» los botones llevan etiqueta y la clase pasa de
        # TaskListButtonPanel a TaskListLabeledButtonPanel. Apuntar solo a la
        # primera deja el fondo sin pintar en cuanto se activan las etiquetas.
        *[(f"Taskbar.{cls}@CommonStates > Border#BackgroundElement", [
            f"CornerRadius={g['buttonRadius']}",
            "Background@InactiveNormal=Transparent",
            f'Background@ActiveNormal:=<SolidColorBrush Color="{argb(teal, g["activeAlpha"])}" />',
            f'Background@ActivePointerOver:=<SolidColorBrush Color="{argb(teal, "33")}" />',
            f'Background@InactivePointerOver:=<SolidColorBrush Color="{argb("#FFFFFF", "1F")}" />',
          ]) for cls in ("TaskListButtonPanel", "TaskListLabeledButtonPanel")],
        # el indicador de app abierta. El diseño lo quiere del color de cada app;
        # el styler no sabe qué app es cada botón, así que va teal para todas.
        ("Taskbar.TaskListLabeledButtonPanel@RunningIndicatorStates > Rectangle#RunningIndicator", [
            f'Fill@ActiveRunningIndicator:=<SolidColorBrush Color="{argb(teal)}" />',
            f'Fill@InactiveRunningIndicator:=<SolidColorBrush Color="{argb(pal["windowsAccent"]["start"], "99")}" />',
            "RadiusX=2", "RadiusY=2", f"Height={g['indicatorHeight']}",
        ]),
        # reloj arriba en blanco, fecha abajo en gris
        ("TextBlock#TimeInnerTextBlock", [
            f'Foreground:=<SolidColorBrush Color="{argb(s["fg"])}" />',
            f'FontFamily={pal["windowsDesktop"]["clock"]["fontFamily"]}']),
        ("TextBlock#DateInnerTextBlock", [
            f'Foreground:=<SolidColorBrush Color="{argb(ro["grey"]["hex"])}" />',
            f'FontFamily={pal["windowsDesktop"]["clock"]["fontFamily"]}']),
    ]

    out: dict[str, object] = {
        "theme": "",                  # sin tema base: la barra la definimos entera
        "clickThroughTaskbar": 0,     # eso era del dock; con barra completa, no
        "xamlDiagnosticsHandling": "alert",
        "styleConstants[0]": "",
        "themeResourceVariables[0]": "",
    }
    for i, (target, rules) in enumerate(styles):
        out[f"controlStyles[{i}].target"] = target
        for j, rule in enumerate(rules):
            out[f"controlStyles[{i}].styles[{j}]"] = rule
    return out


def clock_settings(pal: dict) -> dict[str, object]:
    """Reloj de dos líneas con cpu/ram y la rama de git, como en el diseño.

    El mod trae %cpu% y %ram% de serie: el diseño daba por hecho que hacían
    falta TrafficMonitor o un script, y no es el caso.

    La rama sí necesita ayuda: el mod sabe pedir texto por HTTP y pintarlo como
    %web1%, así que `lib/gitbranch.py` la sirve por loopback desde WSL. Si el
    servicio no está levantado, %web1% sale vacío y el resto del reloj sigue
    igual — nada se rompe.
    """
    c = pal["windowsDesktop"]["clock"]
    g = pal["windowsDesktop"].get("gitBranch", {})
    return {
        "ShowSeconds": 0,
        "TimeFormat": c["timeFormat"],
        "DateFormat": c["dateFormat"],
        "DateLocale": "",
        "WeekdayFormat": "dddd",
        "TopLine": c["topLine"],
        "BottomLine": c["bottomLine"],
        "MiddleLine": "",
        "TooltipLine": "",
        "TooltipLineMode": "append",
        "MaxWidth": 0,
        "TextSpacing": 0,
        # con símbolo, como el diseño; el padding evita que el ancho baile al
        # pasar de 9% a 100%
        "DataCollection.PercentageFormat": "spacePaddingAndSymbol",
        "DataCollection.UpdateInterval": 2,
        # la rama: texto plano, sin recorte por marcadores, tal cual llega
        "WebContentsItems[0].Url": f"http://127.0.0.1:{g.get('port', 8756)}/",
        "WebContentsItems[0].BlockStart": "",
        "WebContentsItems[0].Start": "",
        "WebContentsItems[0].End": "",
        "WebContentsItems[0].ContentMode": "",
        "WebContentsItems[0].SearchReplace[0].Search": "",
        "WebContentsItems[0].SearchReplace[0].Replace": "",
        # tope corto a propósito: una rama tipo fix/loquesea-y-lo-otro
        # ensancharía el reloj y empujaría la bandeja
        "WebContentsItems[0].MaxLength": int(g.get("maxLength", 16)),
        "WebContentsUpdateInterval": int(g.get("updateMinutes", 1)),
    }


# ── menú Inicio ───────────────────────────────────────────────────────
def start_settings(pal: dict) -> dict[str, object]:
    s = pal["surfaces"]
    return {
        "theme": "TranslucentStartMenu",
        "disableNewStartMenuLayout": "",
        # el tema define $CommonBgBrush con un tinte gris; lo llevamos al fondo
        # del terminal manteniendo el desenfoque
        "styleConstants[0]": f'CommonBgBrush=<WindhawkBlur BlurAmount="24" TintColor="{argb(s["bg"], "B3")}"/>',
        "controlStyles[0].target": "Border#AcrylicBorder",
        "controlStyles[0].styles[0]": f'BorderBrush:=<SolidColorBrush Color="{argb(s["border"])}" />',
        "controlStyles[0].styles[1]": "BorderThickness=1",
        "controlStyles[0].styles[2]": "CornerRadius=16",
        "themeResourceVariables[0]": "",
        "webContentStyles[0].target": "",
        "webContentStyles[0].styles[0]": "",
        "webContentCustomJs": "",
    }


# ── posición del botón Inicio ─────────────────────────────────────────
def startpos_settings(pal: dict) -> dict[str, object]:
    """Inicio a la izquierda con las apps centradas, que es la disposición del
    diseño y lo único que Windows no sabe hacer solo: su `TaskbarAl` es todo a
    la izquierda o todo al centro, sin término medio.

    El mod se llama «Start button always on the left» en Windhawk; el id que
    lleva la URL, `taskbar-start-button-position`, no aparece en el buscador.
    """
    t = pal["windowsDesktop"]["taskbar"]
    return {
        # búsqueda y vista de tareas se van con Inicio: si no, la lupa queda
        # flotando al principio del grupo de apps y se ve como un descuadre
        "otherSystemButtonsOnTheLeft": 1 if t.get("systemButtonsLeft", True) else 0,
        "startMenuOnTheLeft": 1,
        "searchMenuPositionInAllCases": 0,
    }


# ── icono del botón Inicio ────────────────────────────────────────────
def starticon_settings(pal: dict) -> dict[str, object]:
    """El asterisco de Claude en el botón de Inicio.

    Las CUATRO rutas de imagen se escriben aunque tres vayan vacías. El mod
    trae por defecto unos GIF de un gecko alojados en GitHub para los estados
    pressed y activated; como el .reg borra la subclave antes de reescribirla,
    lo que no se ponga vuelve a ese default y aparece el bicho al pulsar
    Inicio. Vacías significa «usa la normal», que es lo que queremos.
    """
    sb = pal["windowsDesktop"].get("startButton", {})
    src = r"%LOCALAPPDATA%\claude-terminal-theme\icons\start-claude.png"
    return {
        "images.imageSource": src,
        "images.hoverImageSource": "",
        "images.pressedImageSource": "",
        "images.activatedImageSource": "",
        "images.iconSize": int(sb.get("iconSize", 24)),
        # sin rotación: el botón de Inicio de un tema sobrio no da tumbos
        "hoverEffects.hoverScale": 110,
        "hoverEffects.hoverRotation": 0,
        "hoverEffects.hoverOpacity": 100,
        "pressedEffects.pressedScale": 94,
        "pressedEffects.pressedRotation": 0,
        "pressedEffects.pressedOpacity": 100,
        # si la imagen no carga, que se vea: es un fallo de instalación, no ruido
        "showImageLoadFailureWarnings": 1,
    }


# ── borde de la ventana activa ────────────────────────────────────────
def border_settings(pal: dict) -> dict[str, object]:
    r"""La ventana activa se distingue por el borde en el acento, no por
    pintarle la barra de título — que es lo que pide la sección 06 del diseño.

    El mod EXIGE que «Mostrar el color de acento en barras de título y bordes»
    esté apagado, o sea `ColorPrevalence=0`. Coincide con lo que el diseño manda
    dejar y con lo que ya escribe apply_accent, así que no hay nada que tocar.

    Los colores no son ajustes del mod: el activo es siempre el acento
    (`AccentColor`) y el inactivo sale de `AccentColorInactive`, ambos en
    HKCU\...\DWM y ambos ya escritos desde la paleta.
    """
    return {
        # solo para apps que se dibujan la ventana a mano; encenderlo sin
        # necesidad les mete el borde donde no toca
        "SpecialWindows": 0,
    }


# ── Explorador de archivos ────────────────────────────────────────────
def explorer_settings(pal: dict) -> dict[str, object]:
    """El Explorador en la paleta. Sin tema base: los targets salen del propio
    fuente del mod, no de suposiciones.

    Alcance real, medido sobre una captura: el Explorador de Windows 11 es
    híbrido. Pestañas, barra de comandos y barra de direcciones son XAML y sí se
    pintan. La lista de ficheros, el árbol de la izquierda y la barra de estado
    son el shell view Win32 de toda la vida, y ahí el styler no entra: se quedan
    con el gris oscuro del tema del sistema (#191919). Cambiar eso exigiría
    parchear uxtheme, que no compensa.

    Por eso el Explorador NO usa `surfaces` sino sus propios grises. Con el
    #07090A del resto del tema, el escalón hasta el #191919 de Windows es de
    dieciséis niveles y la ventana parece rota por la mitad. Los de
    `explorer.surfaces` suben el chrome hasta rozarlo: la separación entre
    barras y contenido la lleva la línea del borde, no un salto de luminancia.
    """
    es = pal["windowsDesktop"]["explorer"].get("surfaces", {})
    s = pal["surfaces"]
    chrome = argb(es.get("chrome", s["bgAlt"]))   # barras: comandos y direcciones
    canvas = argb(es.get("tabs", s["bg"]))        # tira de pestañas y lienzo XAML
    field = argb(es.get("input", s["bg"]))        # pastilla de direcciones y búsqueda
    # el panel de navegación no está: es Win32, no hay target XAML al que apuntar
    edge = argb(es.get("border", s["border"]))

    styles = [
        # barra de comandos, con la línea inferior que separa del contenido
        ("FileExplorerExtensions.CommandBarControl_Wave1 > Grid, Grid#CommandBarControlRootGrid", [
            f'Background:=<SolidColorBrush Color="{chrome}" />',
            "BorderThickness=0,0,0,1",
            f'BorderBrush:=<SolidColorBrush Color="{edge}" />']),
        ("CommandBar#FileExplorerCommandBar", ["Background=Transparent"]),
        ("Border#BottomBorderLine", [f'Background:=<SolidColorBrush Color="{edge}" />']),
        # fila de la barra de direcciones
        ("FileExplorerExtensions.NavigationBarControl > Grid#NavigationBarControlGrid", [
            f'Background:=<SolidColorBrush Color="{chrome}" />']),
        ("Grid#FileExplorerAddressBarGrid", [
            f'Background:=<SolidColorBrush Color="{field}" />',
            "CornerRadius=6", "BorderThickness=1",
            f'BorderBrush:=<SolidColorBrush Color="{edge}" />']),
        # el nodo real de la pastilla; sin este, el fondo se queda a medias
        ("FileExplorerExtensions.AddressBarControl > Grid#PART_LayoutRoot > Grid#NormalModeGrid", [
            f'Background:=<SolidColorBrush Color="{field}" />',
            "CornerRadius=6", "BorderThickness=1",
            f'BorderBrush:=<SolidColorBrush Color="{edge}" />']),
        # caja de búsqueda
        ("AutoSuggestBox#FileExplorerSearchBox > Grid#LayoutRoot > TextBox > Grid@CommonStates > Border#BorderElement", [
            f'Background:=<SolidColorBrush Color="{field}" />',
            f'BorderBrush:=<SolidColorBrush Color="{edge}" />',
            "CornerRadius=6"]),
        # pestañas
        ("Grid#TabContainerGrid", [f'Background:=<SolidColorBrush Color="{canvas}" />']),
        ("TabViewItem > Grid#LayoutRoot > Canvas > Microsoft.UI.Xaml.Shapes.Path#SelectedBackgroundPath", [
            f'Fill:=<SolidColorBrush Color="{chrome}" />']),
        # el lienzo
        ("Grid#DetailsViewControlRootGrid", [f'Background:=<SolidColorBrush Color="{canvas}" />']),
        ("Grid#HomeViewRootGrid", [f'Background:=<SolidColorBrush Color="{canvas}" />']),
        ("FileExplorerExtensions.GalleryViewControl#GalleryViewControl > Grid", [
            f'Background:=<SolidColorBrush Color="{canvas}" />']),
        # menús y tooltips a juego
        ("MenuFlyoutPresenter > Border", [
            f'Background:=<SolidColorBrush Color="{chrome}" />',
            f'BorderBrush:=<SolidColorBrush Color="{edge}" />']),
        ("ToolTip", [f'Background:=<SolidColorBrush Color="{chrome}" />']),
    ]
    out: dict[str, object] = {
        "theme": "",
        "backgroundTranslucentEffect": "",
        "styleConstants[0]": "",
        "themeResourceVariables[0]": "",
    }
    for i, (target, rules) in enumerate(styles):
        out[f"controlStyles[{i}].target"] = target
        for j, rule in enumerate(rules):
            out[f"controlStyles[{i}].styles[{j}]"] = rule
    return out


def columns_settings(pal: dict) -> dict[str, object]:
    """Las cuatro columnas del diseño, en su orden y con sus anchuras."""
    out: dict[str, object] = {}
    for i, col in enumerate(pal["windowsDesktop"]["explorer"]["columns"]):
        out[f"columns[{i}].property"] = col["property"]
        out[f"columns[{i}].force_width"] = 1
        out[f"columns[{i}].width"] = col["width"]
    out["sort_property"] = ""
    out["sort_descending"] = 0
    out["exclude_virtual"] = 1     # la papelera y «Este equipo» mantienen las suyas
    return out


def notification_settings(pal: dict) -> dict[str, object]:
    """Centro de notificaciones. TranslucentShell expone $CommonBgBrush igual
    que el menú Inicio, así que basta con recolorearlo."""
    s = pal["surfaces"]
    return {
        "theme": "TranslucentShell",
        "styleConstants[0]": f'CommonBgBrush=<WindhawkBlur BlurAmount="24" TintColor="{argb(s["bg"], "B3")}"/>',
        "styleConstants[1]": "thumbnailImageSize=300",
        "controlStyles[0].target": "MenuFlyoutPresenter > Border",
        "controlStyles[0].styles[0]": f'BorderBrush:=<SolidColorBrush Color="{argb(s["border"])}" />',
        "themeResourceVariables[0]": "",
    }


# ── generación del .reg ───────────────────────────────────────────────
def _esc(v: str) -> str:
    return v.replace("\\", "\\\\").replace('"', '\\"')


def reg_file(blocks: dict[str, dict[str, object]],
             mod_values: dict[str, dict[str, int]] | None = None,
             wipe: bool = True) -> str:
    """blocks: {mod: settings}. Borra la subclave Settings antes de reescribirla,
    para que no queden índices sueltos de una configuración anterior.

    mod_values: valores en la clave del mod, no en Settings — «Disabled», por
    ejemplo, para activar un mod que estaba apagado."""
    mod_values = mod_values or {}
    out = ["Windows Registry Editor Version 5.00", ""]
    now = int(time.time())
    for mod, settings in blocks.items():
        key = f"{MODS_HIVE}\\{mod}\\Settings"
        if wipe:
            out += [f"[-{key}]", ""]
        out.append(f"[{key}]")
        for name, val in settings.items():
            if isinstance(val, int):
                out.append(f'"{_esc(name)}"=dword:{val:08x}')
            else:
                out.append(f'"{_esc(name)}"="{_esc(str(val))}"')
        out += ["", f"[{MODS_HIVE}\\{mod}]",
                f'"SettingsChangeTime"=dword:{now:08x}']
        for name, val in mod_values.get(mod, {}).items():
            out.append(f'"{_esc(name)}"=dword:{val:08x}')
        out.append("")
    return "\r\n".join(out) + "\r\n"


def write_reg(path: pathlib.Path, content: str):
    # los .reg se leen mejor en UTF-16LE con BOM
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-16")


def import_elevated(win_path: str) -> tuple[bool, str]:
    """Importa el .reg con UAC. Devuelve (ok, mensaje)."""
    ps = (f"$p = Start-Process reg.exe -ArgumentList 'import',\"{win_path}\" "
          f"-Verb RunAs -Wait -PassThru; exit $p.ExitCode")
    r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps],
                       capture_output=True, cwd="/mnt/c")
    err = r.stderr.decode("cp850", "replace").strip()
    if r.returncode == 0:
        return True, "importado"
    if "cancel" in err.lower() or "canceló" in err.lower() or r.returncode == 1:
        return False, "UAC cancelado o import fallido: " + (err or "sin detalle")
    return False, err or f"reg import devolvió {r.returncode}"


def restart_explorer():
    subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                    "Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue"],
                   capture_output=True, cwd="/mnt/c")
