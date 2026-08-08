"""Build the holodeck backend snapshot."""

import sys
from pathlib import Path

# Running `python apps/holodeck/collect.py` puts this file's directory on
# sys.path[0], not the repo root. Pin this checkout before importing apps.*.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT_STR = str(_REPO_ROOT)
if sys.path[:1] != [_REPO_ROOT_STR]:
    while _REPO_ROOT_STR in sys.path:
        sys.path.remove(_REPO_ROOT_STR)
    sys.path.insert(0, _REPO_ROOT_STR)

import argparse
import json
import time
from datetime import datetime

from apps.holodeck.collectors import LAYER_NAMES
from apps.holodeck.collectors import apps as apps_collector
from apps.holodeck.collectors import branches as branches_collector
from apps.holodeck.collectors import core as core_collector
from apps.holodeck.collectors import deploy as deploy_collector
from apps.holodeck.collectors import sessions as sessions_collector
from apps.holodeck.collectors import skills as skills_collector
from apps.holodeck.collectors import specs as specs_collector
from apps.holodeck.collectors import worktrees as worktrees_collector
from apps.holodeck.worktree_colors_palette import write_worktree_colors_palette

SNAPSHOT_REL = Path("apps/holodeck/data/snapshot.json")

### Snapshot
def repo_root():
    return _REPO_ROOT
def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")
def empty_snapshot(root):
    return {
        "generated_at": now_iso(),
        "repo_root": str(root),
        "layer_meta": {name: {"generated_at": None, "took_s": None, "error": None} for name in LAYER_NAMES},
        "layers": {name: [] for name in LAYER_NAMES},
    }
def snapshot_path(root):
    return Path(root) / SNAPSHOT_REL
def load_snapshot(root):
    path = snapshot_path(root)
    if not path.exists():
        return empty_snapshot(root)
    with path.open("r", encoding="utf-8") as handle:
        snapshot = json.load(handle)
    for name in LAYER_NAMES:
        snapshot.setdefault("layers", {}).setdefault(name, [])
        snapshot.setdefault("layer_meta", {}).setdefault(name, {"generated_at": None, "took_s": None, "error": None})
    return snapshot
def write_snapshot(root, snapshot):
    path = snapshot_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, sort_keys=True)
        handle.write("\n")
def merge_snapshot(existing, updates, root, generated_at=None):
    snapshot = existing
    snapshot["generated_at"] = generated_at or now_iso()
    snapshot["repo_root"] = str(root)
    snapshot.setdefault("layers", {})
    snapshot.setdefault("layer_meta", {})
    for name in LAYER_NAMES:
        snapshot["layers"].setdefault(name, [])
        snapshot["layer_meta"].setdefault(name, {"generated_at": None, "took_s": None, "error": None})
    for name, result in updates.items():
        snapshot["layers"][name] = result["items"]
        meta = {
            "generated_at": result["generated_at"],
            "took_s": result["took_s"],
            "error": result["error"],
        }
        for key, value in (result.get("meta") or {}).items():
            if key in ("generated_at", "took_s", "error"):
                continue
            meta[key] = value
        snapshot["layer_meta"][name] = meta
    return snapshot

### Collection
def normalize_collector_result(value):
    if isinstance(value, tuple) and len(value) == 3:
        return value[0], value[1], value[2] or {}
    if isinstance(value, tuple) and len(value) == 2:
        return value[0], value[1], {}
    return value, None, {}
def collect_layer(name, root, layers, prior_snapshot=None):
    prior = prior_snapshot or {}
    prior_layers = prior.get("layers") or {}
    prior_meta = prior.get("layer_meta") or {}
    if name == "worktrees":
        return worktrees_collector.collect_worktrees(root)
    if name == "branches":
        return branches_collector.collect_branches(
            root,
            worktrees=layers.get("worktrees"),
            previous_branches=prior_layers.get("branches"),
            previous_meta=prior_meta.get("branches"),
        )
    if name == "apps":
        return apps_collector.collect_apps(root)
    if name == "core":
        return core_collector.collect_core(root)
    if name == "skills":
        return skills_collector.collect_skills(root)
    if name == "specs":
        return specs_collector.collect_specs(root, worktrees=layers.get("worktrees"))
    if name == "sessions":
        return sessions_collector.collect_sessions(root, worktrees=layers.get("worktrees"), include_cloud=True)
    if name == "deploy":
        return deploy_collector.collect_deploy(root)
    raise ValueError("unknown layer: " + name)
def run_collectors(root, selected, base_snapshot, prior_snapshot=None):
    updates = {}
    layers = dict(base_snapshot.get("layers") or {})
    prior = prior_snapshot if prior_snapshot is not None else base_snapshot
    for name in selected:
        started = time.perf_counter()
        generated_at = now_iso()
        error = None
        meta = {}
        try:
            items, note, meta = normalize_collector_result(collect_layer(name, root, layers, prior_snapshot=prior))
            error = note
        except Exception as exc:
            items = []
            error = str(exc)
            meta = {}
        took_s = round(time.perf_counter() - started, 3)
        updates[name] = {"items": items, "generated_at": generated_at, "took_s": took_s, "error": error, "meta": meta}
        layers[name] = items
        print_layer_summary(name, items, took_s, error)
    return updates
def print_layer_summary(name, items, took_s, error):
    count = len(items) if hasattr(items, "__len__") else 0
    line = f"{name}: {count} items in {took_s:.3f}s"
    if error:
        line += " note=" + str(error)
    print(line)

### CLI
def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Collect holodeck backend snapshot")
    parser.add_argument("--layer", action="append", choices=LAYER_NAMES, help="Refresh one layer; repeatable")
    parser.add_argument("--list", action="store_true", help="Print layer names")
    return parser.parse_args(argv)
def main(argv=None):
    args = parse_args(argv)
    if args.list:
        for name in LAYER_NAMES:
            print(name)
        return 0
    root = repo_root()
    selected = args.layer or LAYER_NAMES
    prior = load_snapshot(root)
    base = prior if args.layer else empty_snapshot(root)
    updates = run_collectors(root, selected, base, prior_snapshot=prior)
    snapshot = merge_snapshot(base, updates, root)
    write_snapshot(root, snapshot)
    try:
        write_worktree_colors_palette(root)
    except Exception as exc:
        print("worktree-colors palette: failed — " + str(exc))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
