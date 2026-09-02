#!/usr/bin/env python3
"""La rama de git en la barra de tareas.

El diseño pide la rama del repo en la bandeja. Windows no tiene de dónde
sacarla, pero *Taskbar Clock Customization* sabe pedir texto por HTTP y pintarlo
como `%web1%`. Así que esto sirve la rama por loopback y el reloj la lee.

Windows llega al loopback de WSL: `localhostForwarding` está en true por
defecto, así que un `127.0.0.1:PUERTO` de aquí se ve desde explorer.exe.

    python3 lib/gitbranch.py            # servidor, primer plano
    python3 lib/gitbranch.py --once     # imprime lo que serviría y sale

Qué repo, por orden:

  1. El que apunta la shell. El tema zsh escribe la raíz del repo en el que
     estás en `~/.local/state/claude-terminal-theme/repo` en cada prompt. Es la
     señal exacta: la barra enseña la rama de donde estás trabajando.
  2. Si ese fichero no existe —tema sin instalar, o nunca abriste una shell—,
     se cae al último repo TOCADO: la mtime más nueva de .git/index, HEAD y
     FETCH_HEAD bajo las raíces configuradas. Es más tosco, porque `git status`
     no siempre reescribe el índice, pero da algo razonable.
"""
from __future__ import annotations
import argparse, http.server, os, pathlib, socketserver, subprocess, sys, time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import render  # noqa: E402

# La mtime que delata actividad. index cambia al hacer add/commit/status,
# HEAD al cambiar de rama, FETCH_HEAD al traer de remoto.
MARKERS = ("index", "HEAD", "FETCH_HEAD")
CACHE_TTL = 5.0          # segundos; el reloj pregunta cada minuto, no hace falta más


def _cfg() -> dict:
    pal = render.load()
    c = dict(pal.get("windowsDesktop", {}).get("gitBranch", {}))
    c.setdefault("port", 8756)
    c.setdefault("roots", ["~/projects"])
    c.setdefault("depth", 3)
    c.setdefault("dirtyMark", "*")
    c.setdefault("empty", "")
    c.setdefault("stateFile",
                 "${XDG_STATE_HOME:-~/.local/state}/claude-terminal-theme/repo")
    return c


def from_shell(cfg: dict) -> pathlib.Path | None:
    """La raíz que apuntó el último prompt de zsh, si sigue siendo un repo."""
    raw = cfg["stateFile"].replace("${XDG_STATE_HOME:-~/.local/state}",
                                   os.environ.get("XDG_STATE_HOME",
                                                  str(pathlib.Path.home() / ".local/state")))
    try:
        line = pathlib.Path(raw).expanduser().read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not line:
        return None                      # shell fuera de un repo: eso es un vacío
    p = pathlib.Path(line)
    return p if (p / ".git").exists() else None


def repos(roots: list[str], depth: int) -> list[pathlib.Path]:
    """Los .git bajo cada raíz, sin bajar más de `depth` niveles.

    Nada de rglob: en un home con node_modules eso tarda una eternidad.
    """
    found = []
    for root in roots:
        base = pathlib.Path(root).expanduser()
        if not base.is_dir():
            continue
        stack = [(base, 0)]
        while stack:
            d, lvl = stack.pop()
            try:
                entries = list(d.iterdir())
            except OSError:
                continue
            if any(e.name == ".git" for e in entries):
                found.append(d)
                continue          # un repo no contiene otro repo que nos importe
            if lvl < depth:
                stack += [(e, lvl + 1) for e in entries
                          if e.is_dir() and not e.name.startswith(".")]
    return found


def touched(repo: pathlib.Path) -> float:
    git = repo / ".git"
    best = 0.0
    for m in MARKERS:
        try:
            best = max(best, (git / m).stat().st_mtime)
        except OSError:
            pass
    return best


def branch_of(repo: pathlib.Path, dirty_mark: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
                       capture_output=True, text=True, timeout=5)
    if r.returncode != 0:
        return ""
    name = r.stdout.strip()
    if name == "HEAD":                       # detached: el hash corto dice más
        r = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=5)
        name = r.stdout.strip() or "detached"
    if dirty_mark:
        d = subprocess.run(["git", "-C", str(repo), "status", "--porcelain",
                            "--untracked-files=no"],
                           capture_output=True, text=True, timeout=10)
        if d.returncode == 0 and d.stdout.strip():
            name += dirty_mark
    return name


def current(cfg: dict) -> str:
    shell = from_shell(cfg)
    if shell is not None:
        return branch_of(shell, cfg["dirtyMark"]) or cfg["empty"]
    rs = repos(cfg["roots"], int(cfg["depth"]))
    if not rs:
        return cfg["empty"]
    newest = max(rs, key=touched)
    if touched(newest) == 0.0:
        return cfg["empty"]
    return branch_of(newest, cfg["dirtyMark"]) or cfg["empty"]


class Handler(http.server.BaseHTTPRequestHandler):
    cfg: dict = {}
    _cache: tuple[float, str] = (0.0, "")

    def do_GET(self):
        now = time.time()
        ts, val = Handler._cache
        if now - ts > CACHE_TTL:
            try:
                val = current(Handler.cfg)
            except Exception:
                val = Handler.cfg["empty"]
            Handler._cache = (now, val)
        body = val.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass                                  # nada de ruido en el journal


class Server(socketserver.TCPServer):
    allow_reuse_address = True                # si no, cada reinicio choca con TIME_WAIT


def main() -> int:
    ap = argparse.ArgumentParser(description="Sirve la rama de git por loopback.")
    ap.add_argument("--once", action="store_true", help="imprime y sale")
    a = ap.parse_args()
    cfg = _cfg()
    if a.once:
        print(current(cfg))
        return 0
    Handler.cfg = cfg
    with Server(("127.0.0.1", int(cfg["port"])), Handler) as srv:
        print(f"rama en http://127.0.0.1:{cfg['port']}/  "
              f"raices={cfg['roots']}", flush=True)
        srv.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
