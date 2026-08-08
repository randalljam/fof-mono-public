"""Single local FastAPI server for Deutsch content tools.
Security posture matches worldview-mirror: bind 127.0.0.1 in the CLI, inject a
per-run session token into served pages, and reject every /api/ call without it."""
import importlib
import json
import os
import secrets
from datetime import datetime, timezone
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from dgraph import grounding
from dgraph import query as dquery
from . import config
from . import runs

SESSION_TOKEN = os.environ.get("CT_TOKEN") or secrets.token_urlsafe(24)
app = FastAPI(title="Deutsch Content Tools", docs_url=None, redoc_url=None)
STATE = {}

### Startup and auth
@app.on_event("startup")
def startup():
    """Load the committed graph and citation index once for all tools."""
    STATE["graph"] = grounding.load_graph()
    STATE["citation_index"] = grounding.citation_index(STATE["graph"])
    STATE["graph_stats"] = dquery.stats(STATE["graph"])
    STATE["corpus_available"] = grounding.corpus_available(repo_root=config.REPO_ROOT)
@app.middleware("http")
async def require_token(request, call_next):
    """Reject /api/ requests without the session token."""
    if request.url.path.startswith("/api/") and request.headers.get("x-ct-token") != SESSION_TOKEN:
        return JSONResponse({"error": "missing or invalid session token"}, status_code=401)
    return await call_next(request)
def _ensure_state():
    """Initialize state for direct TestClient calls that bypass startup."""
    if "graph" not in STATE:
        startup()
def _now_string():
    """UTC timestamp for run provenance; engines receive it as data."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
def _read_page(path):
    """Read an HTML page with token and registry JSON injected."""
    with open(path, encoding="utf-8") as f:
        html = f.read()
    return html.replace("__CT_TOKEN__", SESSION_TOKEN).replace("__TOOLS_JSON__", json.dumps(config.tool_rows()))
def _import_engine(tool):
    """Lazy import one registered tool engine."""
    return importlib.import_module(config.TOOLS[tool]["module"])

### Pages
@app.get("/", response_class=HTMLResponse)
def index():
    """Serve the content-tools landing page."""
    return _read_page(os.path.join(config.WEB_DIR, "index.html"))
@app.get("/{tool}", response_class=HTMLResponse)
def tool_page(tool):
    """Serve a registered tool page when installed."""
    if tool not in config.TOOLS or not config.tool_available(tool):
        raise HTTPException(404, "tool not installed")
    path = config.tool_page_path(tool)
    if not os.path.exists(path):
        raise HTTPException(404, "tool page missing")
    return _read_page(path)

### API
@app.get("/api/state")
def get_state():
    """Everything a tool UI needs to boot."""
    _ensure_state()
    return {"tones": [{"level": k, "label": v["label"]} for k, v in sorted(config.TONES.items())],
            "defaults": {"tone": config.DEFAULT_TONE}, "tools": config.tool_rows(),
            "corpus_available": STATE["corpus_available"], "graph_stats": STATE["graph_stats"],
            "samples": config.sample_rows()}
@app.post("/api/{tool}/run")
async def run_tool(tool, payload=Body(...)):
    """Run one installed tool and save the result."""
    _ensure_state()
    if tool not in config.TOOLS or not config.tool_available(tool):
        raise HTTPException(404, "tool not installed")
    state = dict(STATE)
    state["generated_at"] = _now_string()
    state["repo_root"] = config.REPO_ROOT
    try:
        result = _import_engine(tool).run_from_request(payload, state)
    except Exception as e:
        raise HTTPException(502, "engine error: %s" % e)
    return runs.save_run(tool, result)
@app.get("/api/{tool}/runs")
def list_tool_runs(tool):
    """List saved runs for one installed or known tool."""
    if tool not in config.TOOLS:
        raise HTTPException(404, "unknown tool")
    return {"runs": runs.list_runs(tool)}
@app.get("/api/{tool}/runs/{run_id}")
def load_tool_run(tool, run_id):
    """Load one saved run."""
    if tool not in config.TOOLS:
        raise HTTPException(404, "unknown tool")
    run = runs.load_run(tool, run_id)
    if run is None:
        raise HTTPException(404, "unknown run")
    return run
@app.delete("/api/{tool}/runs/{run_id}")
def delete_tool_run(tool, run_id):
    """Delete one saved run."""
    if tool not in config.TOOLS:
        raise HTTPException(404, "unknown tool")
    if not runs.delete_run(tool, run_id):
        raise HTTPException(404, "unknown run")
    return {"deleted": run_id}
