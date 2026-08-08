"""Non-secret runtime settings for Worldview Mirror."""
import os
import sys

### Paths
def find_repo_root(start):
    """Walk upward to the monorepo root."""
    path = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(path, "AGENTS.md")) and os.path.exists(os.path.join(path, ".git")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            raise RuntimeError("repo root not found above " + start)
        path = parent
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = find_repo_root(APP_DIR)
DGRAPH_APP_DIR = os.path.join(REPO_ROOT, "apps", "deutsch", "deutsch-graph")
GRAPH_DIR = os.path.join(DGRAPH_APP_DIR, "graph")
TAXONOMY_DIR = os.path.join(APP_DIR, "taxonomy")
WEB_DIR = os.path.join(APP_DIR, "web")
PROFILES_DIR = os.path.join(APP_DIR, "data", "profiles")
THREADS_DIR = os.path.join(APP_DIR, "data", "threads")
for runtime_path in (REPO_ROOT, DGRAPH_APP_DIR):
    if runtime_path not in sys.path:
        sys.path.insert(0, runtime_path)

### Product defaults
TONES = {
    1: {"label": "Gentle", "instruction": "Be exceptionally gentle, curious, and non-confrontational."},
    2: {"label": "Supportive", "instruction": "Be warm and supportive while still naming meaningful differences."},
    3: {"label": "Balanced", "instruction": "Be clear, even-handed, and candid without becoming combative."},
    4: {"label": "Direct", "instruction": "Be direct and probing; state disagreements plainly and respectfully."},
    5: {"label": "Critical", "instruction": "Apply strong critical pressure to weak explanations while remaining civil and evidence-grounded."},
}
DEFAULT_TONE = 3
DEFAULT_LENS = "profile:deep-optimism"
USER_PROFILE_ID = "user"
def default_model():
    """Configured Worldview Mirror model, falling back to the shared OpenAI model."""
    selected = os.environ.get("WVM_OPENAI_MODEL")
    if selected:
        return selected
    from core import llm
    return llm.OPENAI_MODEL
