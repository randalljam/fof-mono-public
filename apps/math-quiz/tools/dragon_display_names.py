"""Local-only dragon learner aliases: canonical code id -> on-disk name.

The map in apps/math-quiz/dragon/data/display_names.json (gitignored) lets committed
code use ids like Kid1 while local SQLite / dragon saves keep a kid's real name. The
same value is used for UI labels and for every dev-server file lookup.
"""
import json
import shutil
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DISPLAY_NAMES_FILE = APP_DIR / "dragon" / "data" / "display_names.json"
DISPLAY_NAMES_EXAMPLE = APP_DIR / "dragon" / "display_names.example.json"

_cache = None


def ensure_local_file():
    """Create data/display_names.json from the committed example when missing."""
    if DISPLAY_NAMES_FILE.is_file():
        return
    DISPLAY_NAMES_FILE.parent.mkdir(parents=True, exist_ok=True)
    if DISPLAY_NAMES_EXAMPLE.is_file():
        shutil.copyfile(DISPLAY_NAMES_EXAMPLE, DISPLAY_NAMES_FILE)


def load_names():
    global _cache
    if _cache is not None:
        return _cache
    if not DISPLAY_NAMES_FILE.is_file():
        _cache = {}
        return _cache
    try:
        data = json.loads(DISPLAY_NAMES_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            _cache = {}
            return _cache
        _cache = {str(k): str(v) for k, v in data.items() if k and v}
    except Exception:
        _cache = {}
    return _cache


def resolve_data_user(user):
    """Map a canonical learner id to the name used in local files."""
    if not user:
        return user
    return load_names().get(user, user)


def view():
    return {"ok": True, "names": load_names()}
