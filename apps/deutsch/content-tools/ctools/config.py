"""Non-secret runtime settings for the shared Deutsch content-tools harness."""
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
DEUTSCH_APPS_DIR = os.path.join(REPO_ROOT, "apps", "deutsch")
DGRAPH_APP_DIR = os.path.join(DEUTSCH_APPS_DIR, "deutsch-graph")
WEB_DIR = os.path.join(APP_DIR, "web")
SAMPLES_DIR = os.path.join(APP_DIR, "samples")
for runtime_path in (REPO_ROOT, DGRAPH_APP_DIR):
    if runtime_path not in sys.path:
        sys.path.insert(0, runtime_path)

### Shared tone knob
TONES = {
    1: {"label": "Gentle", "instruction": "Be exceptionally gentle, curious, and non-confrontational."},
    2: {"label": "Supportive", "instruction": "Be warm and supportive while still naming meaningful differences."},
    3: {"label": "Balanced", "instruction": "Be clear, even-handed, and candid without becoming combative."},
    4: {"label": "Direct", "instruction": "Be direct and probing; state disagreements plainly and respectfully."},
    5: {"label": "Critical", "instruction": "Apply strong critical pressure to weak explanations while remaining civil and evidence-grounded."},
}
DEFAULT_TONE = 3

### Tool registry
TOOLS = {
    "interject": {
        "label": "Deutsch Interject",
        "app_dir": os.path.join(DEUTSCH_APPS_DIR, "deutsch-interject"),
        "module": "dinterject.engine",
        "page": "/interject",
        "page_file": os.path.join("web", "deutsch-interject.html"),
    },
    "redo": {
        "label": "Content Redo",
        "app_dir": os.path.join(DEUTSCH_APPS_DIR, "content-redo"),
        "module": "dredo.engine",
        "page": "/redo",
        "page_file": os.path.join("web", "content-redo.html"),
    },
    "forge": {
        "label": "Content Forge",
        "app_dir": os.path.join(DEUTSCH_APPS_DIR, "content-forge"),
        "module": "dforge.engine",
        "page": "/forge",
        "page_file": os.path.join("web", "content-forge.html"),
    },
}
for tool_row in TOOLS.values():
    if tool_row["app_dir"] not in sys.path:
        sys.path.insert(0, tool_row["app_dir"])
def tool_app_dir(tool):
    """Absolute application directory for a registered tool."""
    return TOOLS[tool]["app_dir"]
def tool_page_path(tool):
    """Absolute path to a registered tool's HTML page."""
    return os.path.join(tool_app_dir(tool), TOOLS[tool]["page_file"])
def _module_path(tool):
    """Expected source path for a registered engine module."""
    return os.path.join(tool_app_dir(tool), *TOOLS[tool]["module"].split(".")) + ".py"
def tool_available(tool):
    """Whether the registered app, engine module, and HTML page are installed."""
    if tool not in TOOLS:
        return False
    return os.path.isdir(tool_app_dir(tool)) and os.path.isfile(_module_path(tool)) and os.path.isfile(tool_page_path(tool))
def tool_rows():
    """JSON-safe registry rows for the server and landing page."""
    return [{"key": key, "label": row["label"], "module": row["module"], "page": row["page"],
             "installed": tool_available(key)} for key, row in TOOLS.items()]
def sample_rows():
    """JSON-safe shared sample descriptors."""
    if not os.path.isdir(SAMPLES_DIR):
        return []
    rows = []
    for name in sorted(os.listdir(SAMPLES_DIR)):
        if name.endswith(".md"):
            label = os.path.splitext(name)[0].replace("-", " ").replace("_", " ").title()
            rows.append({"name": name, "label": label})
    return rows
