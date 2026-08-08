import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GUARD = REPO / "scripts/python/fof_worktree_import_guard.py"
INSTALLER = REPO / "scripts/python/install_worktree_import_guard.py"


def load_guard_module():
    spec = importlib.util.spec_from_file_location("fof_worktree_import_guard", GUARD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


### Root detection
def test_is_fof_repo_root():
    guard = load_guard_module()
    assert guard.is_fof_repo_root(REPO) is True
    assert guard.is_fof_repo_root(REPO / "apps") is False


def test_find_repo_root_from_nested_script():
    guard = load_guard_module()
    script = REPO / "apps/holodeck/collect.py"
    root = guard.find_repo_root_from(script)
    assert root == REPO.resolve()


def test_user_script_path_ignores_venv_console_scripts(tmp_path):
    guard = load_guard_module()
    fake = tmp_path / ".venv" / "bin" / "pytest"
    fake.parent.mkdir(parents=True)
    fake.write_text("#!/bin/sh\n", encoding="utf-8")
    old_argv = sys.argv[:]
    try:
        sys.argv = [str(fake)]
        assert guard.user_script_path() is None
    finally:
        sys.argv = old_argv


### Installer
def test_install_guard_idempotent(tmp_path):
    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    py = venv / "bin/python3"
    for _ in range(2):
        result = subprocess.run(
            [str(py), str(INSTALLER), "--venv-python", str(py)],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            check=True,
        )
        assert "installed" in result.stdout or "import guard" in result.stdout
    check = subprocess.run(
        [str(py), str(INSTALLER), "--venv-python", str(py), "--check"],
        cwd=str(REPO),
        check=True,
    )
    assert check.returncode == 0


def test_nested_script_imports_local_checkout(tmp_path):
    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    py = venv / "bin/python3"
    subprocess.run([str(py), str(INSTALLER), "--venv-python", str(py)], cwd=str(REPO), check=True)
    probe = REPO / "apps/holodeck/_pytest_import_probe.py"
    probe.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "expected = Path(__file__).resolve().parents[2]\n"
        "roots = [Path(entry).resolve() for entry in sys.path[:5] if entry]\n"
        "assert expected in roots, sys.path[:5]\n"
        "print(expected)\n",
        encoding="utf-8",
    )
    try:
        nested = subprocess.run(
            [str(py), str(probe)],
            cwd=str(REPO / "apps/holodeck"),
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        probe.unlink(missing_ok=True)
    assert nested.returncode == 0, nested.stderr
    assert str(REPO.resolve()) in nested.stdout


### Packaging metadata
def test_setup_does_not_install_apps_core_packages():
    text = (REPO / "setup.py").read_text(encoding="utf-8")
    assert "find_packages" not in text
    assert "packages=[]" in text
