#!/usr/bin/env python3
"""Configuración de los mods de Windhawk, derivada de palette.json.

Windhawk guarda los ajustes de cada mod en HKLM, así que escribir aquí exige
elevación: se genera un .reg y se importa con UAC.

Los dos mods tienen que estar YA instalados desde la interfaz de Windhawk. Este
módulo no instala mods, solo los configura; si no están, avisa y no toca nada.

Base elegida:
  · barra  → tema integrado «DockLike» (dock centrado y despegado) + overrides
             de color, radio y margen para llevarlo a la paleta
  · inicio → tema integrado «TranslucentStartMenu», que expone $CommonBgBrush
             justamente para esto
"""
from __future__ import annotations
import pathlib, subprocess, time

TASKBAR_MOD = "windows-11-taskbar-styler"
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
    dock = argb(s["bgAlt"], "E6")          # el cristal del dock, 90% opaco
    edge = argb(s["border"])
    teal = ro["teal"]["hex"]
    deep = pal["windowsAccent"]["start"]   # teal oscuro, para los rellenos

    styles = [
        # el dock: despegado del borde, redondo por los cuatro lados
        ("Taskbar.TaskbarFrame > Grid#RootGrid", [
            f'Background:=<SolidColorBrush Color="{dock}" />',
            f'BorderBrush:=<SolidColorBrush Color="{edge}" />',
            "BorderThickness=1",
            "CornerRadius=16",
            "Margin=0,4,0,10",
            "Padding=8,0,8,0",
        ]),
        # la bandeja del sistema, como isla aparte con el mismo cristal
        ("Grid#SystemTrayFrameGrid", [
            f'Background:=<SolidColorBrush Color="{dock}" />',
            f'BorderBrush:=<SolidColorBrush Color="{edge}" />',
            "CornerRadius=16",
        ]),
        # el botón de cada app
        ("Taskbar.TaskListButtonPanel@CommonStates > Border#BackgroundElement", [
            "CornerRadius=10",
            "Background@InactiveNormal=Transparent",
            f'Background@ActiveNormal:=<SolidColorBrush Color="{argb(deep, "38")}" />',
            f'Background@ActivePointerOver:=<SolidColorBrush Color="{argb(deep, "4D")}" />',
            f'Background@InactivePointerOver:=<SolidColorBrush Color="{argb("#FFFFFF", "1F")}" />',
        ]),
        # el puntito de «app abierta» → teal
        ("Taskbar.TaskListLabeledButtonPanel@RunningIndicatorStates > Rectangle#RunningIndicator", [
            f'Fill@ActiveRunningIndicator:=<SolidColorBrush Color="{argb(teal)}" />',
            f'Fill@InactiveRunningIndicator:=<SolidColorBrush Color="{argb(deep, "99")}" />',
            "RadiusX=2", "RadiusY=2", "Height=3",
        ]),
        # reloj y fecha, con la jerarquía de la paleta
        ("TextBlock#TimeInnerTextBlock", [
            f'Foreground:=<SolidColorBrush Color="{argb(s["fg"])}" />']),
        ("TextBlock#DateInnerTextBlock", [
            f'Foreground:=<SolidColorBrush Color="{argb(ro["grey"]["hex"])}" />']),
    ]

    out: dict[str, object] = {
        "theme": "DockLike",
        "clickThroughTaskbar": 1,     # recomendado por el propio mod para docks
        "xamlDiagnosticsHandling": "alert",
        "styleConstants[0]": "",
        "themeResourceVariables[0]": "",
    }
    for i, (target, rules) in enumerate(styles):
        out[f"controlStyles[{i}].target"] = target
        for j, rule in enumerate(rules):
            out[f"controlStyles[{i}].styles[{j}]"] = rule
    return out


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


def reg_file(blocks: dict[str, dict[str, object]], wipe: bool = True) -> str:
    """blocks: {mod: settings}. Borra la subclave Settings antes de reescribirla,
    para que no queden índices sueltos de una configuración anterior."""
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
                f'"SettingsChangeTime"=dword:{now:08x}', ""]
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
