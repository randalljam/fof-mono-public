"""Prepend the invoking FoF checkout root to sys.path at interpreter startup.

Installed into the venv site-packages via install_worktree_import_guard.py.
Detects repo root from a real user script path (not venv console scripts) or cwd.
"""
import os
import sys
from pathlib import Path

_REPO_MARKERS = ("AGENTS.md", "core", "apps")


def is_fof_repo_root(path):
    base = Path(path)
    if not base.is_dir():
        return False
    for name in _REPO_MARKERS:
        candidate = base / name
        if name.endswith(".md"):
            if not candidate.is_file():
                return False
        elif not candidate.is_dir():
            return False
    return True


def find_repo_root_from(start):
    current = Path(start).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if is_fof_repo_root(candidate):
            return candidate
    return None


def user_script_path():
    if len(sys.argv) < 1:
        return None
    raw = sys.argv[0]
    if not raw or raw == "-c":
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    else:
        path = path.resolve()
    if not path.exists():
        return None
    if path.suffix.lower() != ".py":
        return None
    parts = path.parts
    if ".venv" in parts:
        idx = parts.index(".venv")
        if idx + 1 < len(parts) and parts[idx + 1] == "bin":
            return None
    return path


def prepend_repo_root(root):
    root_str = str(root)
    if sys.path[:1] == [root_str]:
        return
    while root_str in sys.path:
        sys.path.remove(root_str)
    sys.path.insert(0, root_str)


def selected_repo_root():
    script = user_script_path()
    if script is not None:
        root = find_repo_root_from(script)
        if root is not None:
            return root
    return find_repo_root_from(Path.cwd())


def activate():
    root = selected_repo_root()
    if root is None:
        return None
    prepend_repo_root(root)
    return root


activate()
