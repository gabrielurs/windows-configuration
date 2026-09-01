#!/usr/bin/env python3
import argparse, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import uninstall, apply_windows  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()
home = apply_windows.win_userprofile() if pathlib.Path("/mnt/c").is_dir() else None
uninstall.run(dry=a.dry_run, win_home=home)
