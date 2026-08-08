"""Worldview Atlas: load and validate the taxonomy (axes + named worldview profiles).
Taxonomy files are hand-curated under taxonomy/ — axes.jsonl plus profiles/*.json.
Positions use a shared scale: -2.0 (fully at pole_neg) .. +2.0 (fully at pole_pos)."""
import json
import os
from . import config

POSITION_MIN, POSITION_MAX = -2.0, 2.0
AXIS_REQUIRED = ("id", "label", "question", "pole_neg", "pole_pos")
POLE_REQUIRED = ("label", "definition")
PROFILE_REQUIRED = ("id", "label", "summary", "positions")

### Loading
def load_axes(taxonomy_dir=None):
    """Read taxonomy/axes.jsonl -> ordered list of axis dicts."""
    path = os.path.join(taxonomy_dir or config.TAXONOMY_DIR, "axes.jsonl")
    axes = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                axes.append(json.loads(line))
    return axes
def load_profiles(taxonomy_dir=None):
    """Read taxonomy/profiles/*.json -> {profile_id: profile dict}."""
    folder = os.path.join(taxonomy_dir or config.TAXONOMY_DIR, "profiles")
    profiles = {}
    for fname in sorted(os.listdir(folder)):
        if fname.endswith(".json"):
            with open(os.path.join(folder, fname), encoding="utf-8") as f:
                profile = json.load(f)
            profiles[profile["id"]] = profile
    return profiles
def load_atlas(taxonomy_dir=None):
    """Load the whole atlas -> {'axes': [...], 'axes_by_id': {...}, 'profiles': {...}}."""
    axes = load_axes(taxonomy_dir)
    return {"axes": axes, "axes_by_id": {a["id"]: a for a in axes}, "profiles": load_profiles(taxonomy_dir)}

### Validation
def validate_atlas(atlas, graph_nodes=None):
    """Structural validation -> list of error strings (empty = valid).
    With `graph_nodes` (id->node from the deutsch graph), also checks that every
    evidence `node` reference in profile positions resolves to a real graph node."""
    errors = []
    seen_axes = set()
    for axis in atlas["axes"]:
        for field in AXIS_REQUIRED:
            if field not in axis:
                errors.append("axis %s missing field %s" % (axis.get("id", "?"), field))
        for pole in ("pole_neg", "pole_pos"):
            for field in POLE_REQUIRED:
                if field not in axis.get(pole, {}):
                    errors.append("axis %s %s missing %s" % (axis.get("id", "?"), pole, field))
        if not str(axis.get("id", "")).startswith("axis:"):
            errors.append("axis id %r must start with 'axis:'" % axis.get("id"))
        if axis.get("id") in seen_axes:
            errors.append("duplicate axis id %s" % axis["id"])
        seen_axes.add(axis.get("id"))
    for pid, profile in atlas["profiles"].items():
        for field in PROFILE_REQUIRED:
            if field not in profile:
                errors.append("profile %s missing field %s" % (pid, field))
        if pid != profile.get("id"):
            errors.append("profile key %s != id %s" % (pid, profile.get("id")))
        if not str(pid).startswith("profile:"):
            errors.append("profile id %r must start with 'profile:'" % pid)
        seen_positions = set()
        for pos in profile.get("positions", []):
            axis_id = pos.get("axis")
            if axis_id not in seen_axes:
                errors.append("profile %s position references unknown axis %s" % (pid, axis_id))
            if axis_id in seen_positions:
                errors.append("profile %s has duplicate position for axis %s" % (pid, axis_id))
            seen_positions.add(axis_id)
            value = pos.get("position")
            if not isinstance(value, (int, float)) or not POSITION_MIN <= value <= POSITION_MAX:
                errors.append("profile %s axis %s position %r outside [%s, %s]" % (pid, axis_id, value, POSITION_MIN, POSITION_MAX))
            if not pos.get("summary"):
                errors.append("profile %s axis %s missing summary" % (pid, axis_id))
            for ev in pos.get("evidence", []):
                if not ev.get("node") and not ev.get("url"):
                    errors.append("profile %s axis %s evidence needs node or url" % (pid, axis_id))
                if graph_nodes is not None and ev.get("node") and ev["node"] not in graph_nodes:
                    errors.append("profile %s axis %s evidence node %s not in graph" % (pid, axis_id, ev["node"]))
    return errors
def profile_positions_by_axis(profile):
    """Profile -> {axis_id: position dict}."""
    return {p["axis"]: p for p in profile.get("positions", [])}
