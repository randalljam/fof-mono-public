import os
import tempfile
from pathlib import Path

import pytest

# app.py initializes the preferences database at import time. Point it at an
# isolated session directory before pytest imports either dashboard test module,
# so tests never read or overwrite the durable ../data/dashboard_state.sqlite.
_PREFS_TEMP_DIR = tempfile.TemporaryDirectory(
    prefix="lesson-dashboard-tests-")
os.environ["PREFS_DB"] = str(
    Path(_PREFS_TEMP_DIR.name) / "dashboard_state.sqlite")

@pytest.fixture
def anyio_backend():
    """The dashboard uses asyncio; do not require the optional Trio backend."""
    return "asyncio"

def pytest_unconfigure(config):
    """Remove the isolated preferences database after the test session."""
    _PREFS_TEMP_DIR.cleanup()
