# ===== START OF FILE apps/content_studio/config.py =====
# Central configuration and defaults for the content studio.
#
# Everything here is overridable per-call; these are just the sane defaults so
# the CLI, pipeline, providers, and verifiers all agree on one source of truth.

import os


### Environment / secrets
def _load_dotenv_if_available():
    """Best-effort load of a .env file. dotenv is optional; absence is fine."""
    try:
        from dotenv import load_dotenv
        load_dotenv(override=False)
    except Exception:
        pass
_load_dotenv_if_available()
def resolve_anthropic_api_key(explicit=None):
    """Resolve the Anthropic API key from an explicit arg or the environment.

    Honors the project's local convention (ANTHROPIC_API_KEY_LOCAL) as a fallback
    so this app slots into the same .env the rest of the repo uses.

    :param explicit: optional string key passed directly by the caller.
    :return: the resolved key string, or None if none is configured.
    """
    return (
        explicit
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY_LOCAL")
    )
# Aggregator keys: FAL_KEY (fal.ai) and REPLICATE_API_TOKEN (Replicate) are the
# two primary generation backends. RUNWAYML_API_SECRET is optional.

### Verifier models
# The visual verifier is a vision LLM. Opus 4.8 is the most capable and the best
# at the anatomical / "extra janky arm" judgement this whole app exists to catch.
VERIFIER_MODEL = "claude-opus-4-8"
# Speech verification transcribes the output and compares it to the requested
# text. Runs on fal (same FAL_KEY as generation).
TRANSCRIBER_MODEL = "fal-ai/whisper"

### Default providers per media kind
# 'fal' and 'replicate' are the two primary aggregators (accounts assumed);
# 'mock' runs fully offline and is what tests and keyless demos use.
DEFAULT_PROVIDERS = {"animation": "fal", "video": "fal", "audio": "fal"}

### fal.ai model defaults (all overridable per request via model= / --model)
# Video: ByteDance Seedance 2.0 (fal ids; the 2.0 family dropped the fal-ai/ prefix).
FAL_VIDEO_MODEL_T2V = "bytedance/seedance-2.0/text-to-video"
FAL_VIDEO_MODEL_I2V = "bytedance/seedance-2.0/image-to-video"
# Animation (short GIF-scale loops): the fast tier keeps cost/latency down.
FAL_ANIMATION_MODEL = "bytedance/seedance-2.0/fast/image-to-video"
# Audio.
FAL_SPEECH_MODEL = "fal-ai/minimax/speech-02-hd"
FAL_MUSIC_MODEL = "fal-ai/lyria2"
FAL_SFX_MODEL = "fal-ai/elevenlabs/sound-effects/v2"

### Replicate model defaults
# Seedance 2.0 on Replicate is one unified multimodal slug (t2v + i2v).
REPLICATE_VIDEO_MODEL = "bytedance/seedance-2.0"
REPLICATE_ANIMATION_MODEL = "bytedance/seedance-2.0"
REPLICATE_SPEECH_MODEL = "minimax/speech-02-hd"
REPLICATE_MUSIC_MODEL = "meta/musicgen"
REPLICATE_SFX_MODEL = "meta/musicgen"  # no dedicated sfx model; describe it in the prompt

### Generation defaults
DEFAULT_FPS = 12
DEFAULT_DURATION_S = 2.0        # animation loops
DEFAULT_VIDEO_DURATION_S = 5.0  # video clips
DEFAULT_VIDEO_RESOLUTION = "720p"
DEFAULT_VIDEO_ASPECT = "16:9"
# Long-edge cap for locally synthesized/converted animation frames.
DEFAULT_MAX_EDGE = 512

### Visual verification defaults
# How many frames to sample from the output and show the vision model. More
# frames = better temporal judgement but higher token cost. 6 is a good balance
# for a ~2s clip; longer videos may warrant 8-10.
DEFAULT_SAMPLE_FRAMES = 6
# Long-edge cap for frames sent to the vision model (controls token cost).
VERIFIER_FRAME_MAX_EDGE = 768
# Score policy (0-10 per dimension unless noted). A candidate must clear ALL of
# these to pass; see verify.apply_policy for the exact rules.
ACCEPT_SCORE = 70           # overall_score 0-100 threshold
MIN_ANATOMY = 7             # anatomy/structure integrity floor (the key gate)
MIN_IDENTITY = 6            # must still look like the input character
MIN_TEMPORAL = 5            # frame-to-frame consistency floor

### Audio verification defaults
MIN_SPEECH_SIMILARITY = 0.80    # normalized transcript-vs-text ratio to pass
AUDIO_DURATION_TOLERANCE_S = 1.5  # allowed |actual - requested| duration gap

### Pipeline defaults
# generate -> verify -> (regenerate with stronger negative guidance) loop.
DEFAULT_MAX_ATTEMPTS = 3            # how many regenerate rounds before giving up
DEFAULT_CANDIDATES_PER_ATTEMPT = 1  # best-of-N within a single round

### Output
# Outputs land under _data/ which is gitignored repo-wide (see root .gitignore).
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "_data", "outputs")

# ===== END OF FILE apps/content_studio/config.py =====
