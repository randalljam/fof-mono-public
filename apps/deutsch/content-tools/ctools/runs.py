"""Saved-run JSON store for Deutsch content tools."""
import json
import os
import re
from . import config

RUN_RE = re.compile(r"^run-(\d{4})-")
def _tool_dir(tool):
    """Absolute app directory for `tool`."""
    if tool not in config.TOOLS:
        raise KeyError("unknown tool: " + tool)
    return config.tool_app_dir(tool)
def _runs_dir(tool):
    """Run storage directory for `tool`."""
    return os.path.join(_tool_dir(tool), "data", "runs")
def _slug(text):
    """Short filesystem-safe slug."""
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return (text or "run")[:36].strip("-") or "run"
def _next_id(tool, slug):
    """Next zero-padded counter id from existing run files."""
    runs_dir = _runs_dir(tool)
    max_num = 0
    if os.path.isdir(runs_dir):
        for name in os.listdir(runs_dir):
            match = RUN_RE.match(name)
            if match:
                max_num = max(max_num, int(match.group(1)))
    return "run-%04d-%s" % (max_num + 1, _slug(slug))
def _path(tool, run_id):
    """JSON file path for one run id."""
    return os.path.join(_runs_dir(tool), run_id + ".json")
def save_run(tool, run):
    """Save one run and return the stored dict with run_id."""
    os.makedirs(_runs_dir(tool), exist_ok=True)
    stored = dict(run)
    run_id = stored.get("run_id") or _next_id(tool, stored.get("source_name") or stored.get("title") or tool)
    stored["run_id"] = run_id
    with open(_path(tool, run_id), "w", encoding="utf-8") as f:
        json.dump(stored, f, indent=2, sort_keys=True)
    return stored
def load_run(tool, run_id):
    """Load a saved run or return None."""
    path = _path(tool, run_id)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)
def _summary(run):
    """Small list-row summary for a stored run: shared fields plus the engine's own summary dict."""
    return {"run_id": run.get("run_id"), "source_name": run.get("source_name", ""),
            "generated_at": run.get("generated_at", ""), "knobs": run.get("knobs", {}),
            "summary": run.get("summary", {})}
def list_runs(tool):
    """List saved runs newest first by counter id."""
    runs_dir = _runs_dir(tool)
    if not os.path.isdir(runs_dir):
        return []
    rows = []
    for name in sorted(os.listdir(runs_dir), reverse=True):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(runs_dir, name), encoding="utf-8") as f:
                rows.append(_summary(json.load(f)))
        except (OSError, json.JSONDecodeError):
            continue
    return rows
def delete_run(tool, run_id):
    """Delete a run file, returning True when it existed."""
    path = _path(tool, run_id)
    if not os.path.exists(path):
        return False
    os.remove(path)
    return True
