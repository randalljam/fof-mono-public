# ===== START OF FILE apps/content_studio/model3d/config.py =====
# Configuration for the image -> mesh -> Blender rigged GLB pipeline.

import os

from apps.content_studio import config as content_config

### Mesh provider defaults
MESHY_BASE_URL = "https://api.meshy.ai/openapi/v1"
MESHY_AI_MODEL = "latest"
MESHY_TOPOLOGY = "triangle"
MESHY_TARGET_POLYCOUNT = 30000
MESHY_POSE_MODE = "a-pose"
MESHY_SYMMETRY_MODE = "auto"
MESHY_SHOULD_TEXTURE = True
MESHY_ENABLE_PBR = False
MESHY_POLL_INTERVAL_S = 10
MESHY_TIMEOUT_S = 2400
RODIN_BASE_URL = "https://hyperhuman.deemos.com/api/v2"
RODIN_FREE_TRIAL_KEY = "vibecoding"
RODIN_TIER = "Sketch"
RODIN_POLL_INTERVAL_S = 10
RODIN_TIMEOUT_S = 1800
DEFAULT_MESH_PROVIDER = "rodin"
REQUIRED_CLIPS = ["idle", "walk", "fly", "wing-stretch", "play", "jump", "fire", "hatch"]
DEFAULT_WORK_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "_data", "model3d")

### Environment / local tools
def resolve_meshy_api_key(explicit=None):
    """Resolve the Meshy API key from an explicit arg or the environment.

    Importing apps.content_studio.config above intentionally reuses its dotenv
    loading side effect, so MESHY_API_KEY can come from the same local .env.

    :param explicit: optional string key passed directly by the caller.
    :return: the resolved key string, or None if none is configured.
    """
    return explicit or os.environ.get("MESHY_API_KEY") or None
def resolve_hyper3d_api_key(explicit=None):
    """Resolve the Hyper3D API key from an explicit arg, the environment, or the free-trial key.

    Importing apps.content_studio.config above intentionally reuses its dotenv
    loading side effect, so HYPER3D_API_KEY can come from the same local .env.

    :param explicit: optional string key passed directly by the caller.
    :return: the resolved key string; falls back to the Rodin free-trial key.
    """
    return explicit or os.environ.get("HYPER3D_API_KEY") or RODIN_FREE_TRIAL_KEY
def find_blender():
    """Find the Blender executable for scripted/headless runs.

    :return: absolute path to the Blender binary.
    :raises RuntimeError: if neither BLENDER_BIN nor the macOS app path exists.
    """
    env_path = os.environ.get("BLENDER_BIN")
    default_path = "/Applications/Blender.app/Contents/MacOS/Blender"
    if env_path and os.path.exists(env_path):
        return env_path
    if os.path.exists(default_path):
        return default_path
    if env_path:
        raise RuntimeError(
            f"Blender executable not found. BLENDER_BIN is set to {env_path!r}, "
            f"but it does not exist, and {default_path!r} was not found.")
    raise RuntimeError(
        f"Blender executable not found. Set BLENDER_BIN or install Blender at {default_path!r}.")

# Keep the import visibly used for linters and for readers checking the dotenv side effect.
_CONTENT_CONFIG_MODULE = content_config

# ===== END OF FILE apps/content_studio/model3d/config.py =====
