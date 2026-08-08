"""User worldview profile: fully visible, user-owned, editable, deletable.
Stored as pretty JSON under data/profiles/ (gitignored) plus a regenerated
human-readable markdown mirror in the corpus FIELD: value block grammar.
Positions per axis come from explicit user overrides first, else a
confidence-weighted mean of accumulated observations."""
import datetime
import json
import os
from . import config

### Persistence
def _paths(profile_id, profiles_dir=None):
    """(json_path, md_path) for a profile id."""
    folder = profiles_dir or config.PROFILES_DIR
    return os.path.join(folder, profile_id + ".json"), os.path.join(folder, profile_id + ".md")
def _now():
    """ISO-8601 local timestamp to the second."""
    return datetime.datetime.now().isoformat(timespec="seconds")
def new_profile(profile_id=config.USER_PROFILE_ID, label="My worldview"):
    """Fresh empty profile dict."""
    return {"id": profile_id, "label": label, "created": _now(), "updated": _now(),
            "observations": [], "axis_overrides": {}}
def load_profile(profile_id=config.USER_PROFILE_ID, profiles_dir=None):
    """Load a profile from disk, or a fresh one when absent."""
    json_path, _ = _paths(profile_id, profiles_dir)
    if not os.path.exists(json_path):
        return new_profile(profile_id)
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)
def save_profile(profile, profiles_dir=None, axes=None):
    """Write JSON + regenerate the markdown mirror. Returns the json path."""
    profile["updated"] = _now()
    json_path, md_path = _paths(profile["id"], profiles_dir)
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(profile_markdown(profile, axes or []))
    return json_path
def delete_profile(profile_id=config.USER_PROFILE_ID, profiles_dir=None):
    """Delete both stored files for a profile (the user's right-to-erase)."""
    for path in _paths(profile_id, profiles_dir):
        if os.path.exists(path):
            os.remove(path)

### Observations and overrides
def add_observation(profile, belief, axis, position, confidence, quote="", source="chat", thread=None):
    """Append one belief observation; returns the created entry."""
    obs = {"id": "obs-%03d" % (1 + max([0] + [int(o["id"].split("-")[1]) for o in profile["observations"]])),
           "belief": belief, "axis": axis, "position": position, "confidence": confidence,
           "quote": quote, "source": source, "thread": thread, "date": _now()}
    profile["observations"].append(obs)
    return obs
def delete_observation(profile, obs_id):
    """Remove an observation by id; returns True when found."""
    before = len(profile["observations"])
    profile["observations"] = [o for o in profile["observations"] if o["id"] != obs_id]
    return len(profile["observations"]) < before
def set_axis_override(profile, axis, position, note=""):
    """User directly asserts their position on an axis (wins over observations)."""
    profile["axis_overrides"][axis] = {"position": position, "note": note, "date": _now()}
def clear_axis_override(profile, axis):
    """Remove a direct axis assertion."""
    profile["axis_overrides"].pop(axis, None)

### Aggregation
def aggregate_positions(profile):
    """{axis_id: {'position': float, 'basis': 'override'|'observed', 'count': n}}.
    Observed positions are confidence-weighted means over that axis's observations."""
    out = {}
    sums = {}
    for obs in profile["observations"]:
        axis = obs["axis"]
        weight = max(float(obs.get("confidence", 0.5)), 0.05)
        total, wsum, count = sums.get(axis, (0.0, 0.0, 0))
        sums[axis] = (total + weight * float(obs["position"]), wsum + weight, count + 1)
    for axis, (total, wsum, count) in sums.items():
        out[axis] = {"position": round(total / wsum, 2), "basis": "observed", "count": count}
    for axis, override in profile["axis_overrides"].items():
        out[axis] = {"position": float(override["position"]), "basis": "override",
                     "count": out.get(axis, {}).get("count", 0)}
    return out

### Markdown mirror (transparency artifact — corpus FIELD: value block grammar)
def profile_markdown(profile, axes):
    """Render the profile as human-readable markdown."""
    labels = {a["id"]: a["label"] for a in axes}
    lines = ["file: apps/deutsch/worldview-mirror/data/profiles/%s.md" % profile["id"],
             "title: Worldview profile — %s" % profile["label"],
             "last-updated: %s" % profile["updated"], "",
             "Generated mirror of %s.json — the JSON file is the source of truth; edit via the app or the JSON." % profile["id"], "",
             "### positions"]
    agg = aggregate_positions(profile)
    for axis, info in sorted(agg.items()):
        lines += ["AXIS: %s" % labels.get(axis, axis), "AXIS_ID: %s" % axis,
                  "POSITION: %+.2f" % info["position"], "BASIS: %s (%d observations)" % (info["basis"], info["count"]), ""]
    lines.append("### observations")
    for obs in profile["observations"]:
        lines += ["ID: %s" % obs["id"], "DATE: %s" % obs["date"], "BELIEF: %s" % obs["belief"],
                  "AXIS: %s" % labels.get(obs["axis"], obs["axis"]), "POSITION: %+.2f" % obs["position"],
                  "CONFIDENCE: %.2f" % obs["confidence"]]
        if obs.get("quote"):
            lines.append("QUOTE: %s" % obs["quote"])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
