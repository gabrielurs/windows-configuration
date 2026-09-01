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
import pathlib, subprocess, time

TASKBAR_MOD = "windows-11-taskbar-styler"
CLOCK_MOD = "taskbar-clock-customization"
START_MOD = "windows-11-start-menu-styler"
MODS_KEY = r"HKLM\SOFTWARE\Windhawk\Engine\Mods"
MODS_HIVE = r"HKEY_LOCAL_MACHINE\SOFTWARE\Windhawk\Engine\Mods"


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
    """Reloj de dos líneas con cpu/ram, como en el diseño.

    El mod trae %cpu% y %ram% de serie: el diseño daba por hecho que hacían
    falta TrafficMonitor o un script, y no es el caso.
    """
    c = pal["windowsDesktop"]["clock"]
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
