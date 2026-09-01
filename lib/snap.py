#!/usr/bin/env python3
"""Puente para que install.sh pueda apuntar ficheros en el snapshot.

    python3 lib/snap.py <fichero> [<fichero> ...]
"""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import state  # noqa: E402

snap = state.Snapshot()
for arg in sys.argv[1:]:
    snap.capture_file(arg)
snap.save()
