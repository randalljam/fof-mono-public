"""Non-secret runtime settings for Deutsch Interject."""
import os
import sys

### Paths
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(APP_DIR)))
DGRAPH_APP_DIR = os.path.join(REPO_ROOT, "apps", "deutsch", "deutsch-graph")
CONTENT_TOOLS_DIR = os.path.join(REPO_ROOT, "apps", "deutsch", "content-tools")
OUT_DIR = os.path.join(APP_DIR, "data", "out")
for runtime_path in (REPO_ROOT, DGRAPH_APP_DIR, CONTENT_TOOLS_DIR):
    if runtime_path not in sys.path:
        sys.path.insert(0, runtime_path)

### Fidelity knob
QUOTE_FIDELITY = {
    "quote": {
        "label": "Quote-grounded",
        "instruction": "Prefer brief framing plus verbatim source quotes. Cite every source and do not imitate an uncited voice.",
    },
    "paraphrase": {
        "label": "Grounded paraphrase",
        "instruction": "Paraphrase the provided sources lightly and keep every substantive point cited.",
    },
    "voice": {
        "label": "Synthetic voice",
        "instruction": "Use more customized virtual-Deutsch prose while remaining within the provided grounding and citing it.",
    },
}
DEFAULT_TONE = 3
DEFAULT_FIDELITY = "quote"
def clean_fidelity(value):
    """Normalize a fidelity key."""
    return value if value in QUOTE_FIDELITY else DEFAULT_FIDELITY
