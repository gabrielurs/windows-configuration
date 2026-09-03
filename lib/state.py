#!/usr/bin/env python3
"""Snapshot del estado ORIGINAL, para poder deshacerlo todo.

La idea: la primera vez que el instalador va a tocar algo, apunta cómo estaba.
Ese primer apunte manda — reinstalar mil veces no lo pisa — así que
`--uninstall` siempre devuelve la máquina a como estaba antes de conocer este
repo, no a como estaba en la penúltima instalación.

Se guardan dos cosas:
  · ficheros  → copia íntegra, o la marca «no existía» para borrarlo al deshacer
  · valores de registro → clave, nombre, tipo y dato, o «no existía»
"""
from __future__ import annotations
import hashlib, json, pathlib, re, shutil, subprocess

HOME = pathlib.Path.home()
SNAP = HOME / ".local/share/claude-terminal-theme/snapshot"
MANIFEST = SNAP / "manifest.json"
FILES = SNAP / "files"
REGS = SNAP / "reg"

# reg.exe query imprime:  «    Nombre    REG_TIPO    dato»
_RE_VAL = re.compile(r"^\s{4}(\S.*?)\s{4,}(REG_[A-Z_]+)\s{4,}(.*)$")


class Snapshot:
    def __init__(self, dry: bool = False):
        self.dry = dry
        self.entries: list[dict] = []
        if MANIFEST.exists():
            self.entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self._seen = {self._key(e) for e in self.entries}

    # ── infraestructura ───────────────────────────────────────────────
    @staticmethod
    def _key(e: dict) -> tuple:
        if e["kind"] == "file":
            return ("file", e["path"])
        if e["kind"] == "regkey":
            return ("regkey", e["key"].upper())
        return ("reg", e["key"].upper(), e["name"].upper())

    def _add(self, entry: dict):
        k = self._key(entry)
        if k in self._seen:          # primer apunte manda
            return False
        self.entries.append(entry)
        self._seen.add(k)
        return True

    def save(self):
        if self.dry:
            return
        SNAP.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(self.entries, indent=2, ensure_ascii=False),
                            encoding="utf-8")

    @property
    def exists(self) -> bool:
        return MANIFEST.exists()

    # ── captura ───────────────────────────────────────────────────────
    def capture_file(self, path) -> None:
        path = pathlib.Path(path)
        entry = {"kind": "file", "path": str(path), "existed": path.exists()}
        if path.exists():
            tag = hashlib.sha1(str(path).encode()).hexdigest()[:10]
            entry["backup"] = f"{tag}-{path.name}"
        if not self._add(entry) or self.dry:
            return
        if path.exists():
            FILES.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, FILES / entry["backup"])

    def capture_regkey(self, key: str) -> None:
        """Exporta una clave entera. Para HKLM, donde restaurar valor a valor no
        basta: hay que poder devolver la subclave tal cual estaba."""
        tag = hashlib.sha1(key.upper().encode()).hexdigest()[:10]
        entry = {"kind": "regkey", "key": key, "backup": f"{tag}.reg"}
        r = subprocess.run(["reg.exe", "query", key], capture_output=True, cwd="/mnt/c")
        entry["existed"] = r.returncode == 0
        if not self._add(entry) or self.dry or not entry["existed"]:
            return
        REGS.mkdir(parents=True, exist_ok=True)
        win = subprocess.run(["wslpath", "-w", str(REGS / entry["backup"])],
                             capture_output=True, text=True).stdout.strip()
        subprocess.run(["reg.exe", "export", key, win, "/y"],
                       capture_output=True, cwd="/mnt/c")

    def capture_reg(self, key: str, name: str) -> None:
        cur = read_reg(key, name)
        entry = {"kind": "reg", "key": key, "name": name, "existed": cur is not None}
        if cur:
            entry["type"], entry["data"] = cur
        self._add(entry)

    # ── restauración ──────────────────────────────────────────────────
    def restore(self, say=print) -> tuple[int, int, list[dict]]:
        """Devuelve (restaurados, fallidos, pendientes_de_elevacion)."""
        ok = bad = 0
        needs_admin: list[dict] = []
        for e in reversed(self.entries):
            if e["kind"] == "file":
                p = pathlib.Path(e["path"])
                if e["existed"]:
                    src = FILES / e["backup"]
                    if not src.exists():
                        say(f"  ! falta la copia de {p.name}")
                        bad += 1
                        continue
                    say(f"  restauro {p}")
                    if not self.dry:
                        p.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, p)
                elif p.exists():
                    say(f"  borro {p} (no existía antes)")
                    if not self.dry:
                        p.unlink()
                ok += 1
            elif e["kind"] == "regkey":
                needs_admin.append(e)          # exportación completa: se hace con UAC
            else:
                if e["key"].upper().startswith("HKLM"):
                    needs_admin.append(e)
                    continue
                if self._restore_reg(e, say):
                    ok += 1
                else:
                    bad += 1
        return ok, bad, needs_admin

    def _restore_reg(self, e: dict, say) -> bool:
        if e["existed"]:
            # Los blobs binarios (Favorites de la barra son 5 KB de hex) hacen
            # ilegible el informe: se resume, que aquí interesa QUÉ se restaura.
            d = e["data"]
            if len(d) > 60:
                d = f"{d[:40]}… ({len(d)//2} bytes)"
            say(f"  {e['name']} ← {d}")
            cmd = ["reg.exe", "add", e["key"], "/v", e["name"],
                   "/t", e["type"], "/d", e["data"], "/f"]
        else:
            say(f"  {e['name']} ← borrar (no existía)")
            cmd = ["reg.exe", "delete", e["key"], "/v", e["name"], "/f"]
        if self.dry:
            return True
        r = subprocess.run(cmd, capture_output=True, cwd="/mnt/c")
        if r.returncode != 0 and not e["existed"]:
            return True          # borrar algo que ya no está no es un fallo
        if r.returncode != 0:
            # Sin esto, el informe dice «1 con problemas» y no cuál: un contador
            # sin nombre no sirve para arreglar nada. Salió al ejecutar el
            # desinstalador de verdad por primera vez.
            err = r.stderr.decode("cp850", "replace").strip().splitlines()
            say(f"    ! no se pudo: {err[0] if err else 'reg.exe devolvió '
                f'{r.returncode}'}")
        return r.returncode == 0


def read_reg(key: str, name: str) -> tuple[str, str] | None:
    """(tipo, dato) del valor, o None si no existe."""
    try:
        r = subprocess.run(["reg.exe", "query", key, "/v", name],
                           capture_output=True, timeout=20, cwd="/mnt/c")
    except Exception:
        return None
    if r.returncode != 0:
        return None
    for line in r.stdout.decode("cp850", "replace").splitlines():
        m = _RE_VAL.match(line.rstrip("\r"))
        if m and m.group(1).strip().lower() == name.lower():
            return m.group(2), m.group(3).strip()
    return None
