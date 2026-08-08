#!/usr/bin/env python3
"""Print resolved apps/core origins for the current checkout."""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path


def repo_root():
    return Path(__file__).resolve().parents[2]


def load_module_file(module_name):
    spec = importlib.util.find_spec(module_name)
    if spec is None or spec.origin is None:
        return None
    return spec.origin


def main():
    root = repo_root()
    cwd = Path.cwd().resolve()
    print("checkout:", root)
    print("cwd:", cwd)
    print("python:", sys.executable)
    try:
        import apps.holodeck.collectors.branches as branches
        apps_file = load_module_file("apps")
        core_file = load_module_file("core")
        print("apps.__file__:", apps_file)
        print("core.__file__:", core_file)
        print("branches.__file__:", branches.__file__)
        under = str(root) in str(Path(branches.__file__).resolve())
        print("branches under checkout:", under)
        if not under:
            return 1
    except Exception as exc:
        print("import error:", exc)
        return 1
    nested = subprocess.run(
        [sys.executable, str(root / "apps/holodeck/collect.py"), "--list"],
        cwd=str(root / "apps/holodeck"),
        capture_output=True,
        text=True,
        check=False,
    )
    print("nested collect --list rc:", nested.returncode)
    if nested.returncode != 0:
        print(nested.stderr.strip())
        return nested.returncode
    print("nested collect --list: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
