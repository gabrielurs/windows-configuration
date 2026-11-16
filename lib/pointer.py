#!/usr/bin/env python3
"""El puntero del ratón, en el color de la paleta.

Solo si la paleta trae `windowsDesktop.pointer`: sin esa clave no se toca.

El «Negro» de Configuración NO es esto. Medido el 2026-11-16 dibujando los
cursores del sistema: «Negro» pone el esquema `Windows Black`, que son los
`*_r.cur` de 8 KB de Windows 95 —flecha con dientes de sierra, mano blanca de
píxeles— y deja `Hand` vacío. Lo que da un puntero oscuro con la forma moderna
es «Personalizado»: Windows genera diecisiete `*_eoa.cur` de 136 KB en
%LOCALAPPDATA%\\Microsoft\\Windows\\Cursors, teñidos con `CursorColor`, y apunta a
ellos todos los papeles de `HKCU\\Control Panel\\Cursors`.

Quien genera esos ficheros es la propia Configuración, y no hay API pública ni
valor de registro que lo dispare: se conduce su página con UI Automation
(patrones, no teclas ni ratón sintéticos). El color sí se escribe en el
registro, y la página lo recoge al volver a elegir «Personalizado» —medido: los
.cur cambian de hora y de color—.

Dos costes que hay que saber antes de encenderlo: un .cur no se anima, así que
el aro azul de «ocupado» pasa a ser un reloj de arena fijo; y el «prohibido»
pierde el rojo.
"""
from __future__ import annotations
import base64, pathlib, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import state  # noqa: E402

CURSORS = r"HKCU\Control Panel\Cursors"
ACCESS = r"HKCU\Software\Microsoft\Accessibility"
# Todos los papeles que la página reescribe. Pin y Person no existen con el
# esquema de serie: el snapshot los apunta como «no existía» y al deshacer se
# borran. El nombre del esquema —el valor por defecto de la clave— no se guarda:
# state.read_reg no lee valores sin nombre, y solo es la etiqueta del desplegable
# del panel de control clásico.
ROLES = ("AppStarting", "Arrow", "Crosshair", "Hand", "Help", "IBeam", "No",
         "NWPen", "SizeAll", "SizeNESW", "SizeNS", "SizeNWSE", "SizeWE",
         "UpArrow", "Wait", "Pin", "Person")
TYPE_CUSTOM = 6        # CursorType: 0 blanco, 1 negro, 2 invertido, 6 personalizado

# La página: GridViewItem 0-3 son Blanco, Negro, Invertido, Personalizado, en
# ese orden y en cualquier idioma; a partir del 4 van las muestras de color, que
# solo existen con «Personalizado» elegido. Se pasa por «Blanco» primero porque
# elegir lo que ya está elegido no regenera nada.
_UIA = r"""
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$AE=[Windows.Automation.AutomationElement]
$TS=[Windows.Automation.TreeScope]
function Win { $AE::RootElement.FindAll($TS::Children,(New-Object Windows.Automation.PropertyCondition($AE::ClassNameProperty,'ApplicationFrameWindow'))) |
  ? { $_.FindFirst($TS::Descendants,(New-Object Windows.Automation.PropertyCondition($AE::AutomationIdProperty,'SystemSettings_Accessibility_MouseCursorSize_Slider'))) } | Select -First 1 }
function Items($w) { $w.FindAll($TS::Descendants,(New-Object Windows.Automation.PropertyCondition($AE::ClassNameProperty,'GridViewItem'))) }
function Pick($w,$i) { (Items $w)[$i].GetCurrentPattern([Windows.Automation.SelectionItemPattern]::Pattern).Select(); Start-Sleep -Milliseconds 1500 }
$had = [bool](Get-Process SystemSettings -ErrorAction SilentlyContinue)
Start-Process 'ms-settings:easeofaccess-mousepointer'
$w=$null
for($n=0; $n -lt 40 -and -not $w; $n++){ Start-Sleep -Milliseconds 500; $w=Win }
if(-not $w){ throw 'la pagina del puntero no llego a abrirse' }
for($n=0; $n -lt 20 -and (Items $w).Count -lt 4; $n++){ Start-Sleep -Milliseconds 500 }
if((Items $w).Count -lt 4){ throw 'no encuentro los cuatro estilos de puntero' }
Pick $w 0
Set-ItemProperty 'HKCU:\Software\Microsoft\Accessibility' -Name CursorColor -Value __COLOR__ -Type DWord
Pick $w 3
if(-not $had){ $w.GetCurrentPattern([Windows.Automation.WindowPattern]::Pattern).Close() }
'ok'
"""

_RELOAD = (
    "Add-Type 'using System;using System.Runtime.InteropServices;"
    "public class P{[DllImport(\"user32.dll\",SetLastError=true)]"
    "public static extern bool SystemParametersInfo(uint a,uint b,IntPtr c,uint d);}';"
    # SPI_SETCURSORS: relee HKCU\Control Panel\Cursors y recarga los cursores.
    # Con SPIF_SENDCHANGE a secas (2): con SPIF_UPDATEINIFILE (3) devuelve FALSE
    # sin código de error —medido—, porque aquí no hay nada que escribir.
    "if ([P]::SystemParametersInfo(0x57,0,[IntPtr]::Zero,2)) { 'ok' } else { throw 'SPI_SETCURSORS' }")


def _ps(script: str) -> tuple[bool, str]:
    """Por -EncodedCommand: el script tiene varias líneas, y PowerShell por stdin
    o por -Command las rompe sin decir nada (ver HANDOFF)."""
    enc = base64.b64encode(script.encode("utf-16-le")).decode()
    r = subprocess.run(["powershell.exe", "-NoProfile", "-EncodedCommand", enc],
                       capture_output=True, cwd="/mnt/c")
    out = r.stdout.decode("cp850", "replace").strip()
    err = r.stderr.decode("cp850", "replace").strip()
    return r.returncode == 0 and out.endswith("ok"), out or err


def colorref(hex_: str) -> int:
    """#RRGGBB → COLORREF (0x00BBGGRR), que es como lo guarda Windows: el lima
    de serie, #BFFF00, está en el registro como 0xFFBF."""
    h = hex_.lstrip("#")
    return int(h[4:6] + h[2:4] + h[0:2], 16)


def _dword(key: str, name: str) -> int | None:
    v = state.read_reg(key, name)
    return int(v[1], 0) if v else None


def current() -> tuple[int | None, int | None, str]:
    """(CursorType, CursorColor, fichero de la flecha)."""
    arrow = state.read_reg(CURSORS, "Arrow")
    return _dword(ACCESS, "CursorType"), _dword(ACCESS, "CursorColor"), arrow[1] if arrow else ""


def is_applied(color: str) -> bool:
    typ, col, arrow = current()
    return (typ == TYPE_CUSTOM and col == colorref(color)
            and arrow.lower().endswith("arrow_eoa.cur"))


def apply(pal: dict, snap: state.Snapshot, ctx) -> bool:
    pt = pal["windowsDesktop"].get("pointer")
    if not pt:
        return False
    print("· puntero del ratón")
    color = pt["color"]
    if is_applied(color):
        ctx.say(f"el puntero ya es {color}")
        return False
    for name in ROLES:
        snap.capture_reg(CURSORS, name)
    for name in ("CursorType", "CursorColor"):
        snap.capture_reg(ACCESS, name)
    snap.save()                 # antes de tocar nada, como con el fondo
    ctx.say(f"puntero → personalizado, {color} (abre Configuración unos segundos)")
    if ctx.dry:
        return True
    ok, msg = _ps(_UIA.replace("__COLOR__", str(colorref(color))))
    if not ok:
        ctx.say("! " + msg[:200])
        return False
    if not is_applied(color):
        ctx.say("! Configuración dijo que sí, pero el registro no lo refleja")
        return False
    return True


def restore(snap: state.Snapshot, dry: bool) -> None:
    """Después de Snapshot.restore: el registro ya apunta a los cursores de
    antes, pero nadie los recarga hasta que se le pide."""
    if not any(e["kind"] == "reg" and e["key"] == CURSORS for e in snap.entries):
        return
    print("  puntero ← el de antes")
    if dry:
        return
    ok, msg = _ps(_RELOAD)
    if not ok:
        print("  ! " + msg[:160])
