"""Non-secret runtime settings for Deutsch Content Forge."""
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

### Generation knobs
FORMATS = {
    "essay": {
        "label": "Essay",
        "instruction": "Write a coherent essay with a clear thesis, explanatory sections, and a concise conclusion.",
    },
    "lesson": {
        "label": "Lesson",
        "instruction": "Write a structured lesson with objectives, explanation, examples, and questions-to-explore.",
    },
    "dialogue": {
        "label": "Dialogue",
        "instruction": "Write a dialogue between two named fictional speakers who test and improve ideas. Do not label either speaker as David Deutsch.",
    },
}
LENGTHS = {
    "short": {"label": "Short", "words": 300},
    "medium": {"label": "Medium", "words": 700},
    "long": {"label": "Long", "words": 1200},
}
DEFAULT_FORMAT = "essay"
DEFAULT_LENGTH = "medium"
DEFAULT_TONE = 3
def clean_format(value):
    """Normalize a format key."""
    return value if value in FORMATS else DEFAULT_FORMAT
def clean_length(value):
    """Normalize a length key."""
    return value if value in LENGTHS else DEFAULT_LENGTH
