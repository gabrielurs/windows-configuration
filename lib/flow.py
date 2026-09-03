#!/usr/bin/env python3
"""El buscador flotante, al estilo Spotlight, con la paleta del tema.

Windows no trae nada parecido y su buscador no se deja pintar —la lupa de Win+S
es un icono bicolor que el styler no toca—, así que en vez de pelearse con él se
pone al lado uno que sí obedece: Flow Launcher, cuyos temas son ficheros XAML
sueltos en %APPDATA%\\FlowLauncher\\Themes.

Este módulo genera ese XAML desde palette.json, igual que el resto del repo
genera el .zsh-theme o el perfil de PowerShell. Un solo sitio donde cambiar un
color y que cambie en todas partes.
"""
from __future__ import annotations
import json, pathlib, re, subprocess, sys, time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import render  # noqa: E402

THEME_NAME = "ClaudeCLI"
RUN_KEY = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run"


def base_keys(win_home) -> set[str]:
    """Las claves Base* que define el Base.xaml INSTALADO.

    No vale una lista fija sacada de la plantilla de su repo: la de la rama dev
    trae claves que la version instalada no tiene, y un StaticResource a una
    clave inexistente revienta el parseo del tema entero. Flow entonces avisa
    con un dialogo —«Fail to load theme, fallback to default»— que NO aparece en
    su log, asi que desde aqui solo se ve que el ajuste se revierte solo.
    """
    import glob
    hits = glob.glob(str(win_home / "AppData/Local/FlowLauncher/app-*/Themes/Base.xaml"))
    if not hits:
        return set()
    txt = pathlib.Path(sorted(hits)[-1]).read_text(encoding="utf-8-sig", errors="replace")
    return set(re.findall(r'x:Key="(Base[A-Za-z]+)"', txt))


def theme_xaml(pal: dict, have: set[str] | None = None) -> str:
    """El XAML del tema, calcado en estructura a los que trae Flow.

    Calcado a propósito. Flow valida el diccionario y, si algo no le encaja,
    **cae al tema por defecto sin decir nada**: ni error en la interfaz ni
    excepción en el log. Se descubrió poniendo uno de sus temas —«Darker», que
    sí se queda— y viendo que el nuestro se revertía en 20 segundos.

    Por eso aquí no se inventa nada: mismas claves, mismos BasedOn, mismos
    TargetType que su plantilla, y lo único que cambia son los colores.
    """
    s, ro = pal["surfaces"], pal["roles"]
    teal = ro["teal"]["hex"]

    def style(key, base, target, setters=()):
        # si la version instalada no define ese Base*, mejor omitir el estilo
        # entero que tumbar el tema por una referencia rota
        if have is not None and base not in have:
            return None
        if not setters:
            return (f'    <Style x:Key="{key}" BasedOn="{{StaticResource {base}}}"\n'
                    f'        TargetType="{{x:Type {target}}}" />')
        rows = "\n".join(f'        <Setter Property="{p}" Value="{v}" />' for p, v in setters)
        return (f'    <Style x:Key="{key}" BasedOn="{{StaticResource {base}}}"\n'
                f'        TargetType="{{x:Type {target}}}">\n{rows}\n    </Style>')

    blocks = [
        style("ItemGlyph", "BaseGlyphStyle", "TextBlock", [("Foreground", teal)]),
        style("QueryBoxStyle", "BaseQueryBoxStyle", "TextBox", [
            ("SelectionBrush", s["selection"])]),
        style("QuerySuggestionBoxStyle", "BaseQuerySuggestionBoxStyle", "TextBox", [
            ("Foreground", s["ghost"])]),
        style("WindowBorderStyle", "BaseWindowBorderStyle", "Border", [
            ("Background", s["bg"])]),
        style("WindowStyle", "BaseWindowStyle", "Window"),
        style("PendingLineStyle", "BasePendingLineStyle", "Line"),
        style("ItemTitleStyle", "BaseItemTitleStyle", "TextBlock"),
        style("ItemSubTitleStyle", "BaseItemSubTitleStyle", "TextBlock", [
            ("Foreground", s["fgDim"])]),
        style("ItemTitleSelectedStyle", "BaseItemTitleSelectedStyle", "TextBlock", [
            ("Cursor", "Arrow")]),
        style("ItemSubTitleSelectedStyle", "BaseItemSubTitleSelectedStyle", "TextBlock", [
            ("Foreground", s["fgDim"]), ("Cursor", "Arrow")]),
        style("ItemImageSelectedStyle", "BaseItemImageSelectedStyle", "Image", [
            ("Cursor", "Arrow")]),
        style("ThumbStyle", "BaseThumbStyle", "Thumb"),
        style("ScrollBarStyle", "BaseScrollBarStyle", "ScrollBar"),
        style("HorizontalScrollBarStyle", "BaseHorizontalScrollBarStyle", "ScrollBar"),
        style("HorizontalThumbStyle", "BaseHorizontalThumbStyle", "Thumb"),
        style("SeparatorStyle", "BaseSeparatorStyle", "Rectangle", [
            ("Fill", s["border"]), ("Height", "1"), ("Margin", "8 0 8 8")]),
        style("PreviewBorderStyle", "BasePreviewBorderStyle", "Border", [
            ("BorderBrush", s["border"])]),
    ]
    return (
        '<ResourceDictionary\n'
        '    xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"\n'
        '    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"\n'
        '    xmlns:system="clr-namespace:System;assembly=mscorlib">\n'
        '    <ResourceDictionary.MergedDictionaries>\n'
        '        <ResourceDictionary Source="pack://application:,,,/Themes/Base.xaml" />\n'
        '    </ResourceDictionary.MergedDictionaries>\n'
        '    <!-- Generado por lib/flow.py desde palette.json. No editar a mano. -->\n'
        '    <Thickness x:Key="ResultMargin">0 0 0 8</Thickness>\n'
        f'    <SolidColorBrush x:Key="ItemSelectedBackgroundColor">{s["selection"]}</SolidColorBrush>\n'
        + "\n".join(b for b in blocks if b) + "\n</ResourceDictionary>\n")


def apply(pal: dict, snap, ctx, win_home, remove: bool = False) -> bool:
    """Deja el tema y los ajustes de Flow Launcher. Devuelve True si tocó algo.

    Los ajustes se escriben con Flow PARADO: si está vivo, vuelca su copia en
    memoria al salir y se lleva por delante lo que acabas de poner. Es el mismo
    patrón que con el blob de anclados de la barra.
    """
    if remove:
        return False
    print("· buscador flotante (Flow Launcher)")
    root = win_home / "AppData/Roaming/FlowLauncher"
    if not root.is_dir():
        ctx.say("no está instalado, salto — winget install Flow-Launcher.Flow-Launcher")
        return False

    fl = pal["windowsDesktop"].get("launcher", {})
    theme = root / "Themes" / f"{THEME_NAME}.xaml"
    settings = root / "Settings/Settings.json"

    snap.capture_file(theme)
    snap.capture_file(settings)
    if ctx.dry:
        ctx.say(f"{THEME_NAME}.xaml + hotkey {fl.get('hotkey', 'Ctrl + Space')}")
        return True

    theme.parent.mkdir(parents=True, exist_ok=True)
    theme.write_text(theme_xaml(pal, base_keys(win_home)), encoding="utf-8-sig")
    ctx.say(f"{THEME_NAME}.xaml generado desde la paleta")

    subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                    "Get-Process -Name 'Flow.Launcher' -ErrorAction SilentlyContinue "
                    "| Stop-Process -Force"], capture_output=True, cwd="/mnt/c")
    time.sleep(3)

    if settings.exists():
        d = json.loads(settings.read_text(encoding="utf-8-sig"))
        d["Theme"] = THEME_NAME
        d["Hotkey"] = fl.get("hotkey", "Ctrl + Space")
        d["QueryBoxFont"] = fl.get("font", "Cascadia Mono")
        d["SearchWindowAlign"] = "Center"
        d["UseSound"] = False
        # Arrancar con el equipo, y oculto: un lanzador que hay que abrir a mano
        # no es un lanzador. Recien instalado viene en False y sin entrada de
        # arranque de ningun tipo — comprobado, ni Run ni tarea programada ni
        # carpeta de Inicio.
        d["StartFlowLauncherOnSystemStartup"] = True
        d["HideOnStartup"] = True
        settings.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
        ctx.say(f"hotkey {d['Hotkey']}, centrado, sin sonido")

    exe = win_home / "AppData/Local/FlowLauncher/Flow.Launcher.exe"
    # La entrada de arranque se escribe aparte: el ajuste del JSON por si solo no
    # la crea, la crea Flow al conmutarla en su interfaz. Como aqui no pasamos
    # por su interfaz, se pone a mano.
    if exe.exists():
        win = subprocess.run(["wslpath", "-w", str(exe)],
                             capture_output=True, text=True).stdout.strip()
        snap.capture_reg(RUN_KEY, "FlowLauncher")
        subprocess.run(["reg.exe", "add", RUN_KEY, "/v", "FlowLauncher", "/t", "REG_SZ",
                        "/d", win, "/f"], capture_output=True, cwd="/mnt/c")
        ctx.say("arranca con el equipo, oculto")
        subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                        f"Start-Process '{win}'"], capture_output=True, cwd="/mnt/c")
    return True


if __name__ == "__main__":
    pal = render.load()
    out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(f"{THEME_NAME}.xaml")
    out.write_text(theme_xaml(pal), encoding="utf-8-sig")
    print(f"  {THEME_NAME}.xaml → {out}")
