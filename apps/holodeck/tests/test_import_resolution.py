import subprocess
import sys
from pathlib import Path

import pytest

from apps.holodeck import server as holodeck_server


REPO = holodeck_server.ROOT.resolve()


### Subprocess import resolution
def test_run_collect_subprocess_uses_module_invocation():
    src = Path(holodeck_server.__file__).read_text(encoding="utf-8")
    assert '"-m"' in src
    assert "apps.holodeck.collect" in src


def test_script_collect_resolves_local_branches_module():
    result = subprocess.run(
        [sys.executable, "-v", str(REPO / "apps/holodeck/collect.py"), "--list"],
        cwd=str(REPO / "apps/holodeck"),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    combined = result.stdout + result.stderr
    assert str(REPO / "apps/holodeck/collect.py") in combined or "worktrees" in result.stdout


def test_module_collect_list_from_checkout_root():
    result = subprocess.run(
        [sys.executable, "-m", "apps.holodeck.collect", "--list"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "branches" in result.stdout


def test_server_imports_holodeck_under_root():
    holodeck_server.assert_holodeck_modules_under_root()
