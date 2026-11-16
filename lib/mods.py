#!/usr/bin/env python3
"""Instalar los mods de Windhawk sin abrir Windhawk.

Windhawk no tiene línea de comandos para esto, pero lo que hace su botón
«Install» se puede leer en su extensión (`UI\\resources\\app\\extensions\\windhawk\\
dist\\extension.js`, función `installMod`) y son cuatro pasos:

  1. baja el mod YA COMPILADO de `mods.windhawk.net/mods/<id>/<versión>_<32|64>.dll`
     —solo compila en local si se le pide en sus ajustes—;
  2. lo deja en `%ProgramData%\\Windhawk\\Engine\\Mods\\<32|64>\\<id>_<versión>_<azar>.dll`;
  3. guarda el fuente en `ModsSource\\<id>.wh.cpp`;
  4. escribe en `HKLM\\SOFTWARE\\Windhawk\\Engine\\Mods\\<id>` qué DLL es, en qué
     procesos entra y su versión. El motor vigila esa clave y lo carga solo.

Esto hace lo mismo. Comprobado el 2026-11-16: los 14 mods instalados a mano en
esta máquina son idénticos, byte a byte, a los que sirve esa URL.

Lo que añade: la versión de cada mod y la huella SHA-256 de cada fichero están
FIJADAS en `windows/mods.json`. Un mod es código que se inyecta en explorer.exe
—y dos de ellos, en todos los procesos—; el botón «Install» era la única
revisión humana que había, y automatizarlo sin fijar nada sería instalar a
ciegas lo que el servidor tenga ese día. Si una huella no coincide, no se
instala nada.

Las dos carpetas y la clave son de administrador: se baja y se comprueba sin
elevar, y todo lo que hay que escribir va en UN script elevado, un solo UAC.
"""
from __future__ import annotations
import hashlib, json, pathlib, random, re, subprocess, sys, urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import windhawk  # noqa: E402

URL = "https://mods.windhawk.net/mods/"
CACHE = pathlib.Path.home() / ".cache/claude-terminal-theme/mods"
PROGRAM = r"C:\Program Files\Windhawk"
# Las bibliotecas que todo mod necesita a su lado. La interfaz de Windhawk las
# copia al arrancar; en una máquina donde nunca se abrió, no están, y un mod sin
# ellas no carga. (origen en Compiler\<target>\bin, nombre con el que se dejan)
TARGETS = {"32": "i686-w64-mingw32", "64": "x86_64-w64-mingw32"}
LIBS = (("libc++.dll", "libc++.whl"), ("libunwind.dll", "libunwind.whl"),
        ("windhawk-mod-shim.dll", "windhawk-mod-shim.dll"))


def subfolders(mod: dict) -> list[str]:
    """En qué carpetas va el mod: las que tienen huella en su ficha."""
    return [s for s in ("32", "64") if s in mod.get("sha256", {})]


def _get(url: str) -> bytes:
    # El mismo User-Agent que manda Windhawk; ningún dato del usuario.
    req = urllib.request.Request(url, headers={"User-Agent": "Windhawk/1.7.3"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fetch(mod: dict) -> dict[str, pathlib.Path]:
    """Baja (o saca de la caché) los ficheros del mod y comprueba sus huellas.
    Devuelve {"32"|"64"|"source": ruta}. Lanza ValueError si algo no cuadra."""
    mid, ver = mod["id"], mod["version"]
    want = mod["sha256"]
    out: dict[str, pathlib.Path] = {}
    for kind in subfolders(mod) + ["source"]:
        name = f"{ver}.wh.cpp" if kind == "source" else f"{ver}_{kind}.dll"
        path = CACHE / mid / name
        if not (path.is_file() and _sha(path.read_bytes()) == want[kind]):
            data = _get(f"{URL}{mid}/{name}")
            if _sha(data) != want[kind]:
                raise ValueError(
                    f"{mid} {name}: la huella no coincide con windows/mods.json "
                    f"(esperada {want[kind][:12]}…, recibida {_sha(data)[:12]}…). No se instala.")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        out[kind] = path
    return out


def _q(s: str) -> str:
    return "'" + str(s).replace("'", "''") + "'"


def _winpath(p) -> str:
    return subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()


def script(mods: list[dict], stage_win: str, dll_names: dict[str, str]) -> str:
    """El PowerShell que corre elevado. Todo o nada no se puede —son ficheros y
    registro—, pero se para en el primer error y deja dicho cuál en el log."""
    lines = [
        "$ErrorActionPreference='Stop'",
        f"$stage={_q(stage_win)}",
        "$log=Join-Path $stage 'resultado.txt'",
        "try {",
        "  $data=Join-Path $env:ProgramData 'Windhawk'",
        f"  $prog={_q(PROGRAM)}",
        "  $key='HKLM:\\SOFTWARE\\Windhawk\\Engine\\Mods'",
        "  New-Item -ItemType Directory -Force (Join-Path $data 'ModsSource') | Out-Null",
        "  if(-not (Test-Path $key)){ New-Item -Path $key -Force | Out-Null }",
    ]
    for sub, target in TARGETS.items():
        lines.append(f"  $d=Join-Path $data 'Engine\\Mods\\{sub}'; New-Item -ItemType Directory -Force $d | Out-Null")
        for src, dst in LIBS:
            lines.append(
                f"  $s=Join-Path $prog 'Compiler\\{target}\\bin\\{src}'; $t=Join-Path $d '{dst}'; "
                "if((Test-Path $s) -and -not (Test-Path $t)){ Copy-Item $s $t }")
    for m in mods:
        mid, dll = m["id"], dll_names[m["id"]]
        for sub in subfolders(m):
            lines.append(f"  Copy-Item (Join-Path $stage {_q(mid + '_' + sub + '.dll')}) "
                         f"(Join-Path $data {_q('Engine' + chr(92) + 'Mods' + chr(92) + sub + chr(92) + dll)})")
        lines.append(f"  Copy-Item (Join-Path $stage {_q(mid + '.wh.cpp')}) "
                     f"(Join-Path $data {_q('ModsSource' + chr(92) + mid + '.wh.cpp')}) -Force")
        k = f"(Join-Path $key {_q(mid)})"
        lines.append(f"  if(-not (Test-Path {k})){{ New-Item -Path {k} -Force | Out-Null }}")
        # El mismo orden y los mismos tipos con que lo escribe Windhawk. Las
        # listas van unidas con «|».
        for name, val in (("LibraryFileName", dll), ("Include", "|".join(m.get("include", []))),
                          ("Exclude", "|".join(m.get("exclude", []))),
                          ("Architecture", "|".join(m.get("architecture", []))),
                          ("Version", m["version"])):
            lines.append(f"  Set-ItemProperty -Path {k} -Name {name} -Value {_q(val)} -Type String")
        lines.append(f"  Set-ItemProperty -Path {k} -Name Disabled -Value 0 -Type DWord")
    lines += [
        "  Set-Content -Path $log -Value 'ok' -Encoding ASCII",
        "} catch {",
        "  Set-Content -Path $log -Value ('error: ' + $_.Exception.Message) -Encoding UTF8",
        "  exit 1",
        "}",
        "",
    ]
    return "\r\n".join(lines)


def install(ids: list[str], snap, ctx, win_home) -> list[str]:
    """Instala los mods `ids`. Devuelve los que quedaron instalados."""
    cat = windhawk.catalog()
    mods = [cat[i] for i in ids]
    sin_huella = [m["id"] for m in mods if not (m.get("version") and subfolders(m))]
    if sin_huella:
        ctx.say("! sin versión o huella en windows/mods.json: " + ", ".join(sin_huella))
        mods = [m for m in mods if m["id"] not in sin_huella]
    if not mods:
        return []
    files = {}
    for m in mods:
        try:
            files[m["id"]] = fetch(m)
            ctx.say(f"{m['id']} {m['version']}: bajado y huella comprobada")
        except Exception as e:                       # red caída, 404, huella distinta
            ctx.say(f"! {m['id']}: {e}")
    mods = [m for m in mods if m["id"] in files]
    if not mods:
        return []

    stage = (win_home or pathlib.Path("/mnt/c/Users/Public")) / "claude-theme-backup/mods-stage"
    if stage.exists():
        for f in stage.iterdir():
            f.unlink()
    stage.mkdir(parents=True, exist_ok=True)
    names = {}
    for m in mods:
        mid = m["id"]
        # el sufijo al azar es de Windhawk: así un mod actualizado no pisa la
        # DLL que explorer tiene cargada
        names[mid] = f"{mid}_{m['version']}_{random.randint(100000, 999999)}.dll"
        for sub in subfolders(m):
            (stage / f"{mid}_{sub}.dll").write_bytes(files[mid][sub].read_bytes())
        (stage / f"{mid}.wh.cpp").write_bytes(files[mid]["source"].read_bytes())
        # la clave entera, que no existía: --uninstall la borra
        snap.capture_regkey(f"{windhawk.MODS_KEY}\\{mid}")
    snap.save()
    ps1 = stage / "instalar.ps1"
    ps1.write_text(script(mods, _winpath(stage), names), encoding="utf-8-sig")

    ctx.say(f"instalando {len(mods)} mods — acepta el UAC")
    run = (f"$p = Start-Process powershell.exe -Verb RunAs -Wait -PassThru -WindowStyle Hidden "
           f"-ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',{_q(_winpath(ps1))}; exit $p.ExitCode")
    subprocess.run(["powershell.exe", "-NoProfile", "-Command", run], capture_output=True, cwd="/mnt/c")
    log = stage / "resultado.txt"
    result = log.read_text(encoding="utf-8-sig", errors="replace").strip() if log.exists() else "sin resultado (¿UAC cancelado?)"
    for f in stage.iterdir():
        f.unlink()
    stage.rmdir()
    if result != "ok":
        ctx.say("! " + result[:200])
    done = [m["id"] for m in mods if windhawk.installed(m["id"])]
    if done:
        ctx.say("instalados: " + ", ".join(done))
    return done


def pin() -> None:
    """Reescribe versión, procesos y huellas de `windows/mods.json` con lo que
    hay instalado en ESTA máquina. Para subir un mod de versión: instalarlo desde
    Windhawk, probarlo, y lanzar esto."""
    out = subprocess.run(["reg.exe", "query", windhawk.MODS_KEY, "/s"],
                         capture_output=True, cwd="/mnt/c").stdout.decode("cp850", "replace")
    reg: dict[str, dict[str, str]] = {}
    cur = None
    for line in out.splitlines():
        line = line.rstrip("\r")
        m = re.match(r"^HKEY_LOCAL_MACHINE\\SOFTWARE\\Windhawk\\Engine\\Mods\\([^\\]+)$", line)
        if m:
            cur = m.group(1); reg[cur] = {}; continue
        if line.startswith("HKEY"):
            cur = None; continue
        m = re.match(r"^\s{4}(\S+)\s{4}REG_\w+\s{4}(.*)$", line)
        if m and cur:
            reg[cur][m.group(1)] = m.group(2)
    data = json.loads(windhawk.MANIFEST.read_text(encoding="utf-8"))
    split = lambda s: [x for x in s.split("|") if x]
    for mod in data["mods"]:
        c = reg.get(mod["id"])
        if not c:
            print(f"  {mod['id']}: no está instalado aquí, se queda como estaba")
            continue
        ver, arch = c["Version"], split(c.get("Architecture", ""))
        subs = ["64"] if arch and "x86" not in arch else ["32", "64"]
        mod.update(version=ver, architecture=arch, include=split(c.get("Include", "")),
                   exclude=split(c.get("Exclude", "")))
        mod["sha256"] = {s: _sha(_get(f"{URL}{mod['id']}/{ver}_{s}.dll")) for s in subs}
        mod["sha256"]["source"] = _sha(_get(f"{URL}{mod['id']}/{ver}.wh.cpp"))
        print(f"  {mod['id']} {ver}  [{', '.join(subs)}]")
    windhawk.MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if sys.argv[1:] == ["pin"]:
        pin()
    else:
        sys.exit("uso: python3 lib/mods.py pin")
