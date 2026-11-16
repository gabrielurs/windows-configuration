#!/usr/bin/env python3
"""La barra de título de las ventanas clásicas, más baja.

Solo si la paleta trae `windowsDesktop.titleBar`.

Alcance, medido y no supuesto: esto son las «métricas no cliente» de Windows
(NONCLIENTMETRICS), y solo las obedecen las ventanas que dejan que Windows les
pinte el marco: diálogos, el Panel de control, regedit, las aplicaciones Win32
de siempre. NO las obedecen las que se pintan su propia cabecera —el
Explorador, Windows Terminal, Chrome, VS Code, Slack, Configuración—, que son
la mayoría de las que se usan a diario; cada una tiene su ajuste o ninguno.

Se aplica con SystemParametersInfo y no escribiendo `WindowMetrics` en el
registro: escribirlo no cambia nada hasta cerrar sesión, igual que pasa con el
fondo y con el acento. SPIF_UPDATEINIFILE lo deja guardado y SPIF_SENDCHANGE
avisa a las ventanas abiertas, que se redibujan en el acto.

No se toca el borde (`iPaddedBorderWidth`): ahorraría 4 px más arriba, pero es
también la zona de la que se agarra una ventana para cambiarle el tamaño, y a 0
queda en un píxel.
"""
from __future__ import annotations
import base64, pathlib, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import state  # noqa: E402

METRICS = r"HKCU\Control Panel\Desktop\WindowMetrics"
# Lo que SPI_SETNONCLIENTMETRICS reescribe en el registro al guardar. Se apunta
# todo para el snapshot, aunque aquí solo se cambie el alto del título.
VALUES = ("CaptionHeight", "CaptionWidth", "SmCaptionHeight", "SmCaptionWidth",
          "MenuHeight", "MenuWidth", "ScrollHeight", "ScrollWidth", "BorderWidth",
          "PaddedBorderWidth", "CaptionFont", "SmCaptionFont", "MenuFont",
          "StatusFont", "MessageFont")

_PS = r"""
$ErrorActionPreference='Stop'
Add-Type @'
using System;using System.Runtime.InteropServices;
public class NC{
[StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)]public struct LOGFONT{public int lfHeight,lfWidth,lfEscapement,lfOrientation,lfWeight;public byte lfItalic,lfUnderline,lfStrikeOut,lfCharSet,lfOutPrecision,lfClipPrecision,lfQuality,lfPitchAndFamily;[MarshalAs(UnmanagedType.ByValTStr,SizeConst=32)]public string lfFaceName;}
[StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)]public struct NCM{public int cbSize,iBorderWidth,iScrollWidth,iScrollHeight,iCaptionWidth,iCaptionHeight;public LOGFONT lfCaptionFont;public int iSmCaptionWidth,iSmCaptionHeight;public LOGFONT lfSmCaptionFont;public int iMenuWidth,iMenuHeight;public LOGFONT lfMenuFont,lfStatusFont,lfMessageFont;public int iPaddedBorderWidth;}
[DllImport("user32.dll",CharSet=CharSet.Unicode,SetLastError=true)]public static extern bool SystemParametersInfo(uint a,uint b,ref NCM c,uint d);}
'@
$m=New-Object NC+NCM; $m.cbSize=[Runtime.InteropServices.Marshal]::SizeOf($m)
if(-not [NC]::SystemParametersInfo(0x29,$m.cbSize,[ref]$m,0)){ throw 'SPI_GETNONCLIENTMETRICS' }
$want=__HEIGHT__
if($want -gt 0 -and $m.iCaptionHeight -ne $want){
  $m.iCaptionHeight=$want
  if(-not [NC]::SystemParametersInfo(0x2A,$m.cbSize,[ref]$m,3)){ throw 'SPI_SETNONCLIENTMETRICS' }
}
"caption=$($m.iCaptionHeight)"
'ok'
"""


def _ps(script: str) -> tuple[bool, str]:
    enc = base64.b64encode(script.encode("utf-16-le")).decode()
    r = subprocess.run(["powershell.exe", "-NoProfile", "-EncodedCommand", enc],
                       capture_output=True, cwd="/mnt/c")
    out = r.stdout.decode("cp850", "replace").strip()
    return r.returncode == 0 and out.endswith("ok"), out or r.stderr.decode("cp850", "replace").strip()


def caption_height() -> int | None:
    """El alto actual del título, en píxeles, preguntado a Windows."""
    ok, out = _ps(_PS.replace("__HEIGHT__", "0"))
    for line in out.splitlines():
        if line.startswith("caption="):
            return int(line.split("=", 1)[1])
    return None


def px(twips: str) -> int:
    """El registro guarda las métricas en twips negativos: -15 por píxel a 96 ppp
    (-330 son los 22 px de serie)."""
    return round(-int(twips) / 15)


def apply(pal: dict, snap: state.Snapshot, ctx) -> bool:
    tb = pal["windowsDesktop"].get("titleBar")
    if not tb:
        return False
    print("· barra de título de las ventanas clásicas")
    want = int(tb["captionHeight"])
    cur = caption_height()
    if cur == want:
        ctx.say(f"el título ya mide {want} px")
        return False
    for name in VALUES:
        snap.capture_reg(METRICS, name)
    snap.save()
    ctx.say(f"título: {cur} → {want} px")
    if ctx.dry:
        return True
    ok, msg = _ps(_PS.replace("__HEIGHT__", str(want)))
    if not ok:
        ctx.say("! " + msg[:200])
    return ok


def restore(snap: state.Snapshot, dry: bool) -> None:
    """Después de Snapshot.restore: el registro ya tiene el alto de antes, pero
    las ventanas abiertas no se enteran hasta que se les avisa."""
    e = next((e for e in snap.entries if e["kind"] == "reg" and e["key"] == METRICS
              and e["name"] == "CaptionHeight" and e.get("existed")), None)
    if not e:
        return
    print(f"  título de las ventanas ← {px(e['data'])} px")
    if dry:
        return
    ok, msg = _ps(_PS.replace("__HEIGHT__", str(px(e["data"]))))
    if not ok:
        print("  ! " + msg[:160])
