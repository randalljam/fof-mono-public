#!/usr/bin/env python3
"""Install or verify the FoF worktree import guard in a venv."""
import argparse
import glob
import os
import shutil
import sys
from pathlib import Path

GUARD_MODULE = "fof_worktree_import_guard.py"
PTH_NAME = "fof_worktree_import_guard.pth"
LEGACY_EDITABLE_GLOB = "__editable__.fof_mono*"
FINDER_NAME = "__editable___fof_mono_1_0_finder.py"


def editable_maps_checkout_code(sp):
    finder = Path(sp) / FINDER_NAME
    if not finder.is_file():
        return False
    text = finder.read_text(encoding="utf-8")
    return "'apps':" in text or '"apps":' in text


def legacy_editable_artifacts(sp):
    if editable_maps_checkout_code(sp):
        return sorted(glob.glob(str(Path(sp) / LEGACY_EDITABLE_GLOB)))
    return []


def repo_root():
    return Path(__file__).resolve().parents[2]


def site_packages(venv_python):
    venv_python = Path(venv_python)
    if not venv_python.is_file():
        raise SystemExit("venv python not found: " + str(venv_python))
    venv_root = venv_python.parent.parent
    candidates = sorted((venv_root / "lib").glob("python*/site-packages"))
    if not candidates:
        raise SystemExit("site-packages not found under venv: " + str(venv_root))
    return candidates[-1]


def guard_source():
    return repo_root() / "scripts/python" / GUARD_MODULE


def install_guard(venv_python, check_only=False):
    venv_python = Path(venv_python)
    if not venv_python.is_file():
        raise SystemExit("venv python not found: " + str(venv_python))
    sp = site_packages(venv_python)
    if not sp.is_dir():
        raise SystemExit("site-packages not found: " + str(sp))
    src = guard_source()
    if not src.is_file():
        raise SystemExit("guard source missing: " + str(src))
    dest_module = sp / GUARD_MODULE
    dest_pth = sp / PTH_NAME
    legacy = legacy_editable_artifacts(sp)
    if check_only:
        ok = dest_module.is_file() and dest_pth.is_file() and not legacy
        return ok, sp, legacy
    shutil.copy2(src, dest_module)
    dest_pth.write_text("import fof_worktree_import_guard\n", encoding="utf-8")
    removed = []
    for path in legacy:
        p = Path(path)
        if p.is_file():
            p.unlink()
            removed.append(p.name)
        elif p.is_dir():
            shutil.rmtree(p)
            removed.append(p.name + "/")
    return sp, removed


def main(argv=None):
    parser = argparse.ArgumentParser(description="Install FoF worktree import guard into a venv")
    parser.add_argument("--venv-python", default=str(repo_root() / ".venv/bin/python3"))
    parser.add_argument("--check", action="store_true", help="Verify guard present; exit 1 if missing")
    args = parser.parse_args(argv)
    if args.check:
        ok, sp, legacy = install_guard(args.venv_python, check_only=True)
        if not ok:
            print("import guard: MISSING or legacy editable present in", sp)
            if legacy:
                print("legacy editable:", legacy)
            return 1
        print("import guard: OK (", sp, ")")
        return 0
    sp, removed = install_guard(args.venv_python, check_only=False)
    print("import guard: installed ->", sp / GUARD_MODULE)
    print("import guard: pth ->", sp / PTH_NAME)
    if removed:
        print("removed legacy editable artifacts:", ", ".join(removed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
