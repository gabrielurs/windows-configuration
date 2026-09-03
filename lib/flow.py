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
import json, pathlib, subprocess, sys, time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import render  # noqa: E402

THEME_NAME = "ClaudeCLI"


def theme_xaml(pal: dict) -> str:
    s, ro = pal["surfaces"], pal["roles"]
    fl = pal["windowsDesktop"].get("launcher", {})
    teal = ro["teal"]["hex"]
    font = fl.get("font", "Cascadia Mono")

    def style(key, base, target, setters):
        rows = "\n".join(f'        <Setter Property="{p}" Value="{v}" />'
                         for p, v in setters)
        return (f'    <Style x:Key="{key}" BasedOn="{{StaticResource {base}}}"\n'
                f'        TargetType="{{x:Type {target}}}">\n{rows}\n    </Style>')

    blocks = [
        # el marco: fondo del tema y borde teal, como la ventana activa
        style("WindowBorderStyle", "BaseWindowBorderStyle", "Border", [
            ("Background", s["bg"]),
            ("BorderBrush", teal),
            ("BorderThickness", "1"),
            ("CornerRadius", str(fl.get("cornerRadius", 12)))]),
        # la caja de consulta: monoespaciada y con el cursor en teal, que es lo
        # que hace que lea como un prompt y no como un cuadro de búsqueda
        style("QueryBoxStyle", "BaseQueryBoxStyle", "TextBox", [
            ("Foreground", s["fg"]),
            ("CaretBrush", teal),
            ("SelectionBrush", s["selection"]),
            ("FontFamily", font)]),
        style("QuerySuggestionBoxStyle", "BaseQuerySuggestionBoxStyle", "TextBox", [
            ("Foreground", s["ghost"]),
            ("FontFamily", font)]),
        style("ItemGlyph", "BaseGlyphStyle", "TextBlock", [
            ("Foreground", teal)]),
        style("ItemTitleStyle", "BaseItemTitleStyle", "TextBlock", [
            ("Foreground", s["fg"])]),
        style("ItemSubTitleStyle", "BaseItemSubTitleStyle", "TextBlock", [
            ("Foreground", s["fgDim"]),
            ("FontFamily", font)]),
        style("ItemTitleSelectedStyle", "BaseItemTitleSelectedStyle", "TextBlock", [
            ("Foreground", teal)]),
        style("ItemSubTitleSelectedStyle", "BaseItemSubTitleSelectedStyle", "TextBlock", [
            ("Foreground", s["fgDim"]),
            ("FontFamily", font)]),
        style("SeparatorStyle", "BaseSeparatorStyle", "Rectangle", [
            ("Fill", s["border"]), ("Height", "1"), ("Margin", "8 0 8 8")]),
        style("PreviewBorderStyle", "BasePreviewBorderStyle", "Border", [
            ("BorderBrush", s["border"])]),
    ]
    # Flow lee el diccionario entero y da por hechas TODAS estas claves: si falta
    # una, GetResourceDictionary revienta con NullReferenceException y cae al
    # tema por defecto sin decir nada en la interfaz. Las que no cambiamos van
    # igualmente, como paso directo al estilo base.
    passthrough = [
        ("WindowStyle", "BaseWindowStyle", "Window"),
        ("PendingLineStyle", "BasePendingLineStyle", "Line"),
        ("ItemImageSelectedStyle", "BaseItemImageSelectedStyle", "Image"),
        ("ThumbStyle", "BaseThumbStyle", "Thumb"),
        ("ScrollBarStyle", "BaseScrollBarStyle", "ScrollBar"),
        ("HorizontalScrollBarStyle", "BaseHorizontalScrollBarStyle", "ScrollBar"),
        ("HorizontalThumbStyle", "BaseHorizontalThumbStyle", "Thumb"),
    ]
    blocks += [f'    <Style x:Key="{k}" BasedOn="{{StaticResource {b}}}"\n'
               f'        TargetType="{{x:Type {t}}}" />' for k, b, t in passthrough]
    return (
        '<ResourceDictionary\n'
        '    xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"\n'
        '    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">\n'
        '    <ResourceDictionary.MergedDictionaries>\n'
        '        <ResourceDictionary Source="pack://application:,,,/Themes/Base.xaml" />\n'
        '    </ResourceDictionary.MergedDictionaries>\n'
        f'    <!-- Generado por lib/flow.py desde palette.json. No editar a mano. -->\n'
        f'    <Thickness x:Key="ResultMargin">0 0 0 8</Thickness>\n'
        f'    <SolidColorBrush x:Key="ItemSelectedBackgroundColor">{s["selection"]}</SolidColorBrush>\n'
        + "\n".join(blocks) + "\n</ResourceDictionary>\n")


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
    theme.write_text(theme_xaml(pal), encoding="utf-8-sig")
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
        settings.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
        ctx.say(f"hotkey {d['Hotkey']}, centrado, sin sonido")

    exe = win_home / "AppData/Local/FlowLauncher/Flow.Launcher.exe"
    if exe.exists():
        subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                        f"Start-Process '{exe.as_posix()}'"], capture_output=True, cwd="/mnt/c")
    return True


if __name__ == "__main__":
    pal = render.load()
    out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(f"{THEME_NAME}.xaml")
    out.write_text(theme_xaml(pal), encoding="utf-8-sig")
    print(f"  {THEME_NAME}.xaml → {out}")
