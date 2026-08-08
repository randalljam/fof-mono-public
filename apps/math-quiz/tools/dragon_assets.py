"""Provision gitignored Pipa dragon GLBs into dragon/assets/models/.

createDragon loads assets/models/dragon{,-juvenile,-adult}.glb. Those files are
gitignored; when missing, the game silently falls back to the procedural purple
blob. Approved copies live under the content_studio profile (often via _LOCAL_FILES).
"""
import shutil
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = APP_DIR.parent.parent
APPROVED_DIR = (
    REPO_ROOT / "apps" / "content_studio" / "_data" / "profiles"
    / "math-quiz-dragon-baby" / "approved"
)
RUNTIME_MODELS_DIR = APP_DIR / "dragon" / "assets" / "models"
MODEL_FILES = (
    "dragon.glb",
    "dragon-juvenile.glb",
    "dragon-adult.glb",
)

def runtime_model_paths():
    return {name: RUNTIME_MODELS_DIR / name for name in MODEL_FILES}
def approved_sources_available():
    return all((APPROVED_DIR / name).is_file() for name in MODEL_FILES)
def ensure_local_models():
    """Copy missing approved Pipa GLBs into the game-served assets/models dir."""
    if not approved_sources_available():
        return {
            "ok": False,
            "error": "approved Pipa GLBs not found",
            "approvedDir": str(APPROVED_DIR),
            "copied": [],
            "present": [],
        }
    RUNTIME_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    copied = []
    present = []
    for name in MODEL_FILES:
        src = APPROVED_DIR / name
        dest = RUNTIME_MODELS_DIR / name
        if dest.is_file() and dest.stat().st_size > 0:
            present.append(name)
            continue
        shutil.copyfile(src, dest)
        copied.append(name)
        present.append(name)
    return {
        "ok": True,
        "approvedDir": str(APPROVED_DIR.resolve()),
        "runtimeDir": str(RUNTIME_MODELS_DIR),
        "copied": copied,
        "present": present,
    }
