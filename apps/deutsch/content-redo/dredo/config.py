"""Non-secret runtime settings for Deutsch Content Redo."""
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

### Rewrite knobs
REMIX_DEGREES = {
    1: {
        "label": "Corrections only",
        "instruction": "Correct only outright contradictions of grounded Deutsch positions.",
        "change_types": ["correct"],
    },
    2: {
        "label": "Correct and reframe",
        "instruction": "Correct contradictions and reframe pessimistic, inductivist, or authority-based passages.",
        "change_types": ["correct", "reframe"],
    },
    3: {
        "label": "Full remix",
        "instruction": "Correct, reframe, and add clearly marked knowledge-creation material where grounded.",
        "change_types": ["correct", "reframe", "add"],
    },
}
READING_LEVELS = {
    "adult": {
        "label": "Adult",
        "instruction": "Preserve the source's adult register and conceptual precision.",
    },
    "young": {
        "label": "Young reader",
        "instruction": "Aim at ages 10-13 with shorter sentences and inline definitions of difficult terms.",
    },
    "child": {
        "label": "Child",
        "instruction": "Aim at ages 6-9 with simple vocabulary, concrete examples, and kid-friendly definitions.",
    },
}
DEFAULT_TONE = 3
DEFAULT_DEGREE = 2
DEFAULT_READING_LEVEL = "adult"
LENGTH_TOLERANCE = 0.40
REWRITE_BATCH_SIZE = 5
def clean_degree(value):
    """Normalize a remix degree."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = DEFAULT_DEGREE
    return value if value in REMIX_DEGREES else DEFAULT_DEGREE
def clean_reading_level(value):
    """Normalize a reading-level key."""
    return value if value in READING_LEVELS else DEFAULT_READING_LEVEL
