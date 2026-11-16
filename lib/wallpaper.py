#!/usr/bin/env python3
"""El fondo de escritorio y la pantalla de bloqueo.

Solo si la paleta trae `windowsDesktop.wallpaper`: sin esa clave no se tocan, que
es como estuvo el tema hasta el modo claro (el usuario prefería su fondo).

El fondo se aplica con SystemParametersInfo y no escribiendo `WallPaper` en el
registro: escribirlo no repinta nada, igual que pasa con el acento. La pantalla
de bloqueo no está en ningún valor que se pueda escribir: va por la API de
Windows (Windows.System.UserProfile.LockScreen), y por eso su «antes» se guarda
como imagen en el snapshot y la devuelve `restore`, no `Snapshot.restore`.
"""
from __future__ import annotations
import pathlib, shutil, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import state  # noqa: E402

DESKTOP = r"HKCU\Control Panel\Desktop"
# Spotlight en el bloqueo: poner una imagen lo apaga, así que se apunta para que
# --uninstall lo devuelva. Sin probar con Spotlight encendido: aquí estaba a 0.
CDM = r"HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
SPOTLIGHT = ("RotatingLockScreenEnabled", "RotatingLockScreenOverlayEnabled")

# style → (WallpaperStyle, TileWallpaper)
STYLES = {
    "fill":    ("10", "0"),
    "fit":     ("6", "0"),
    "stretch": ("2", "0"),
    "center":  ("0", "0"),
    "tile":    ("0", "1"),
    "span":    ("22", "0"),
}

_WINRT = (
    "$null=[Windows.System.UserProfile.LockScreen,Windows.System.UserProfile,"
    "ContentType=WindowsRuntime];"
    "$null=[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime];"
    "Add-Type -AssemblyName System.Runtime.WindowsRuntime;"
)


def _ps(script: str) -> tuple[bool, str]:
    r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", script],
                       capture_output=True, cwd="/mnt/c")
    out = r.stdout.decode("cp850", "replace").strip()
    err = r.stderr.decode("cp850", "replace").strip()
    # Éxito es «ok» en stdout, no un stderr vacío: PowerShell suelta por stderr un
    # CLIXML de progreso («Preparando módulos para el primer uso») que no es error.
    return r.returncode == 0 and out.endswith("ok"), out or err


def _q(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def _win(path) -> str:
    return subprocess.run(["wslpath", "-w", str(path)],
                          capture_output=True, text=True).stdout.strip()


def set_desktop(image: str) -> tuple[bool, str]:
    """SPI_SETDESKWALLPAPER con SPIF_UPDATEINIFILE|SPIF_SENDCHANGE: escribe el
    valor y avisa a todo el mundo, que es lo que hace la Configuración."""
    return _ps(
        "Add-Type 'using System;using System.Runtime.InteropServices;"
        "public class W{[DllImport(\"user32.dll\",CharSet=CharSet.Unicode,SetLastError=true)]"
        "public static extern bool SystemParametersInfo(uint a,uint b,string c,uint d);}';"
        f"if ([W]::SystemParametersInfo(0x14,0,{_q(image)},3)) {{ 'ok' }} "
        "else { throw ('SystemParametersInfo: ' + [Runtime.InteropServices.Marshal]::GetLastWin32Error()) }")


def set_lock(image: str) -> tuple[bool, str]:
    """LockScreen.SetImageFileAsync. El fichero tiene que estar en un disco de
    Windows: StorageFile no abre rutas \\\\wsl.localhost."""
    return _ps(
        _WINRT +
        "$m=[System.WindowsRuntimeSystemExtensions].GetMethods();"
        "$op=($m|?{$_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and "
        "$_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'})[0];"
        "$act=($m|?{$_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and "
        "$_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction'})[0];"
        "$t=$op.MakeGenericMethod([Windows.Storage.StorageFile]).Invoke($null,"
        f"@([Windows.Storage.StorageFile]::GetFileFromPathAsync({_q(image)})));"
        "$t.Wait(-1)|Out-Null;"
        "$a=$act.Invoke($null,@([Windows.System.UserProfile.LockScreen]::SetImageFileAsync($t.Result)));"
        "$a.Wait(-1)|Out-Null;'ok'")


def save_lock(dest: pathlib.Path) -> pathlib.Path | None:
    """Vuelca la imagen actual del bloqueo a `dest`, con la extensión que toque
    según su contenido (la de esta máquina era un PNG, no el .jpg original)."""
    tmp = dest.with_suffix(".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)   # en una máquina nueva no existe aún
    ok, _ = _ps(
        _WINRT +
        "$in=[System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead("
        "[Windows.System.UserProfile.LockScreen]::GetImageStream());"
        f"$out=[System.IO.File]::Create({_q(_win(tmp))});"
        "$in.CopyTo($out);$out.Close();$in.Close();'ok'")
    if not ok or not tmp.exists() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        return None
    head = tmp.read_bytes()[:8]
    ext = ".png" if head.startswith(b"\x89PNG") else ".jpg" if head[:2] == b"\xff\xd8" else ".img"
    final = dest.with_suffix(ext)
    tmp.replace(final)
    return final


def apply(pal: dict, snap: state.Snapshot, ctx) -> bool:
    wp = pal["windowsDesktop"].get("wallpaper")
    if not wp:
        return False
    print("· fondo de escritorio y bloqueo")
    image = wp["image"]
    unix = subprocess.run(["wslpath", "-u", image], capture_output=True, text=True).stdout.strip()
    if not unix or not pathlib.Path(unix).is_file():
        ctx.say(f"! no existe {image}; dejo el fondo como está")
        return False
    style = wp.get("style", "fill")
    if style not in STYLES:
        raise SystemExit(f"wallpaper.style: «{style}» no vale; usa {sorted(STYLES)}")
    wstyle, tile = STYLES[style]

    changed = False
    want = {"WallPaper": image, "WallpaperStyle": wstyle, "TileWallpaper": tile}
    cur = {}
    for name in want:
        snap.capture_reg(DESKTOP, name)
        v = state.read_reg(DESKTOP, name)
        cur[name] = v[1] if v else None
    # El manifiesto se escribe al final de la ejecución; si algo revienta entre
    # cambiar el fondo y ese final, la siguiente vez tomaría el nuestro por el
    # original. Se guarda ya.
    snap.save()
    if all((cur[n] or "").lower() == want[n].lower() for n in want):
        ctx.say(f"el fondo ya es {image}")
    else:
        ctx.say(f"fondo → {image} ({style})")
        changed = True
        if not ctx.dry:
            for name in ("WallpaperStyle", "TileWallpaper"):
                subprocess.run(["reg.exe", "add", DESKTOP, "/v", name, "/t", "REG_SZ",
                                "/d", want[name], "/f"], capture_output=True, cwd="/mnt/c")
            ok, msg = set_desktop(image)
            if not ok:
                ctx.say("! " + msg[:160])

    if wp.get("lockScreen"):
        # Primer apunte manda, como en el resto del snapshot: la imagen que había
        # antes de conocer este repo, no la que pusimos nosotros la vez anterior.
        if not ctx.dry and snap.wants_lockscreen():
            saved = save_lock(state.FILES / "lockscreen-original")
            if saved:
                snap.capture_lockscreen(saved.name)
                for name in SPOTLIGHT:
                    snap.capture_reg(CDM, name)
                snap.save()      # la copia de la imagen es la única: que no se pierda su apunte
                ctx.say(f"bloqueo anterior guardado en el snapshot ({saved.name})")
            else:
                ctx.say("! no pude guardar la imagen de bloqueo actual; no la cambio")
                return changed
        # No hay forma barata de saber qué imagen tiene puesta (la API solo da
        # una copia recodificada), así que se pone siempre: es idempotente.
        ctx.say(f"bloqueo → {image}")
        if not ctx.dry:
            ok, msg = set_lock(image)
            if not ok:
                ctx.say("! " + msg[:160])
            changed |= ok
    return changed


def restore(snap: state.Snapshot, win_home: pathlib.Path | None, dry: bool) -> None:
    """Después de Snapshot.restore: repinta el fondo que dejó en el registro y
    devuelve la imagen de bloqueo guardada."""
    regs = {e["name"]: e for e in snap.entries
            if e["kind"] == "reg" and e["key"] == DESKTOP and e.get("existed")}
    if "WallPaper" in regs:
        image = regs["WallPaper"]["data"]
        print(f"  fondo ← {image}")
        if not dry:
            ok, msg = set_desktop(image)
            if not ok:
                print("  ! " + msg[:160])
    for e in snap.entries:
        if e["kind"] != "lockscreen":
            continue
        src = state.FILES / e["backup"]
        if not src.exists():
            print(f"  ! falta la copia de la imagen de bloqueo ({e['backup']})")
            continue
        # StorageFile no abre \\wsl.localhost: se pasa por un disco de Windows.
        tmp_dir = (win_home or pathlib.Path("/mnt/c/Users/Public")) / "claude-theme-backup"
        print(f"  bloqueo ← {e['backup']}")
        if dry:
            continue
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp = tmp_dir / e["backup"]
        shutil.copy2(src, tmp)
        ok, msg = set_lock(_win(tmp))
        if not ok:
            print("  ! " + msg[:160])
