#!/usr/bin/env python3
"""Deshacer: devuelve la máquina al estado guardado en el snapshot original.

Los valores de HKCU y los ficheros se restauran directamente. Lo de HKLM (la
config de los mods de Windhawk) necesita elevación, así que se junta todo en un
.reg y se importa con una sola ventana de UAC.
"""
from __future__ import annotations
import pathlib, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import state, windhawk  # noqa: E402

UNIT = "claude-gitbranch.service"


def _stop_gitbranch(dry: bool) -> None:
    """Parar y desenganchar el servicio ANTES de que el snapshot borre el unit.

    Si se borra el fichero con el servicio aún enganchado, systemd se queda con
    un symlink roto en default.target.wants y lo canta en cada arranque.
    """
    unit = pathlib.Path.home() / ".config/systemd/user" / UNIT
    if not unit.exists():
        return
    if dry:
        print(f"  [dry] systemctl --user disable --now {UNIT}")
        return
    for args in (["disable", "--now", UNIT], ["daemon-reload"]):
        subprocess.run(["systemctl", "--user", *args],
                       capture_output=True, check=False)
    print(f"  {UNIT} parado y desenganchado")


def _admin_reg(entries: list[dict]) -> str:
    """Un .reg que devuelve las claves de HKLM a como estaban."""
    out = ["Windows Registry Editor Version 5.00", ""]
    for e in entries:
        if e["kind"] == "regkey":
            hive = e["key"].replace("HKLM", "HKEY_LOCAL_MACHINE", 1)
            out += [f"[-{hive}]", ""]          # fuera lo que hayamos escrito
            if not e.get("existed"):
                continue
            src = state.REGS / e["backup"]
            if not src.exists():
                continue
            # el export original, sin su cabecera
            body = src.read_text(encoding="utf-16").splitlines()
            out += [ln for ln in body if not ln.startswith("Windows Registry Editor")]
            out.append("")
        else:  # valor suelto de HKLM
            hive = e["key"].replace("HKLM", "HKEY_LOCAL_MACHINE", 1)
            out.append(f"[{hive}]")
            if e["existed"] and e["type"] == "REG_DWORD":
                out.append(f'"{e["name"]}"=dword:{int(e["data"], 0):08x}')
            elif e["existed"]:
                out.append(f'"{e["name"]}"="{e["data"]}"')
            else:
                out.append(f'"{e["name"]}"=-')
            out.append("")
    return "\r\n".join(out) + "\r\n"


def run(dry: bool = False, win_home: pathlib.Path | None = None) -> bool:
    snap = state.Snapshot(dry=dry)
    if not snap.exists:
        print("no hay snapshot: nada que deshacer")
        print(f"  (se esperaba en {state.MANIFEST})")
        return False

    n_file = sum(1 for e in snap.entries if e["kind"] == "file")
    n_reg = sum(1 for e in snap.entries if e["kind"] == "reg")
    n_key = sum(1 for e in snap.entries if e["kind"] == "regkey")
    print(f"snapshot con {n_file} ficheros, {n_reg} valores de registro "
          f"y {n_key} claves completas\n")

    _stop_gitbranch(dry)
    ok, bad, admin = snap.restore()
    print(f"\n{ok} restaurados, {bad} con problemas")

    if admin:
        print(f"\n{len(admin)} entradas de HKLM necesitan elevación (Windhawk):")
        content = _admin_reg(admin)
        out = (win_home or pathlib.Path("/mnt/c/Users/Public")) / "claude-theme-backup"
        path = out / "restore-claude.reg"
        if dry:
            print(f"  [dry] se escribiría {path} y se importaría con UAC")
        else:
            windhawk.write_reg(path, content)
            win = subprocess.run(["wslpath", "-w", str(path)],
                                 capture_output=True, text=True).stdout.strip()
            print(f"  importando {win} — acepta el UAC")
            good, msg = windhawk.import_elevated(win)
            print("  " + ("ok, " if good else "! ") + msg)

    if not dry:
        print("\nreinicia explorer para que se note:")
        print("  powershell.exe -Command \"Stop-Process -Name explorer -Force\"")
    return True
