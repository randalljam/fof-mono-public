"""Persistent user-editable holodeck state."""

import json
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

WORKTREE_FIELDS = {
    "active",
    "order",
    "next_step",
    "last_done",
    "last_done_status",
    "notes",
    "submitted_via",
    "submitted_at",
    "ai_responded",
    "primary_interface",
    "steps",
    "deactivated_at",
}
WORKTREE_TEXT_FIELDS = {"next_step", "last_done", "notes"}
SUBMITTED_VIA_VALUES = {"cursor", "claude-cli", "claude-app", "codex-cli", "codex-app"}
NEXT_STEP_FIELDS = {"text", "done"}
LAST_DONE_STATUSES = {"none", "needs-review", "reviewed", "tested"}

### Shape
def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")
def empty_state(updated_at=None):
    return {"updated_at": updated_at, "next_steps": [], "worktrees": {}}
def worktree_defaults():
    return {
        "active": True,
        "order": None,
        "next_step": None,
        "last_done": None,
        "last_done_status": "none",
        "notes": None,
        "submitted_via": None,
        "submitted_at": None,
        "ai_responded": False,
        "primary_interface": None,
        "steps": [],
        "deactivated_at": None,
    }
def normalize_text_or_none(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise ValueError("expected string or null")
def normalize_iso_or_none(value, field_name):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(field_name + " must be an ISO string or null")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(field_name + " must be an ISO string or null")
    return value
def normalize_ai_interface(value, field_name):
    if value is not None and value not in SUBMITTED_VIA_VALUES:
        raise ValueError(field_name + " must be one of: " + ", ".join(sorted(SUBMITTED_VIA_VALUES)) + ", or null")
    return value
def normalize_next_step(item):
    if not isinstance(item, dict):
        raise ValueError("next step must be an object")
    if not isinstance(item.get("id"), str) or not item.get("id"):
        raise ValueError("next step id must be a string")
    if not isinstance(item.get("text"), str):
        raise ValueError("next step text must be a string")
    if not isinstance(item.get("done"), bool):
        raise ValueError("next step done must be a boolean")
    created_at = item.get("created_at")
    if created_at is not None and not isinstance(created_at, str):
        raise ValueError("next step created_at must be a string or null")
    source = item.get("source")
    if source is not None and not isinstance(source, str):
        raise ValueError("next step source must be a string or null")
    return {"id": item["id"], "text": item["text"], "done": item["done"], "created_at": created_at, "source": source}
def normalize_next_step_list(value, field_name):
    if not isinstance(value, list):
        raise ValueError(field_name + " must be a list")
    return [normalize_next_step(item) for item in value]
def normalize_worktree_entry(entry):
    normalized = worktree_defaults()
    if not isinstance(entry, dict):
        return normalized
    if "active" in entry:
        if not isinstance(entry["active"], bool):
            raise ValueError("active must be a boolean")
        normalized["active"] = entry["active"]
    if "order" in entry:
        if entry["order"] is not None and not isinstance(entry["order"], int):
            raise ValueError("order must be an integer or null")
        normalized["order"] = entry["order"]
    for key in WORKTREE_TEXT_FIELDS:
        if key in entry:
            normalized[key] = normalize_text_or_none(entry[key])
    if "last_done_status" in entry:
        if entry["last_done_status"] not in LAST_DONE_STATUSES:
            raise ValueError("last_done_status must be one of: " + ", ".join(sorted(LAST_DONE_STATUSES)))
        normalized["last_done_status"] = entry["last_done_status"]
    if "submitted_via" in entry:
        normalized["submitted_via"] = normalize_ai_interface(entry["submitted_via"], "submitted_via")
    if "submitted_at" in entry:
        normalized["submitted_at"] = normalize_iso_or_none(entry["submitted_at"], "submitted_at")
    if "ai_responded" in entry:
        if not isinstance(entry["ai_responded"], bool):
            raise ValueError("ai_responded must be a boolean")
        normalized["ai_responded"] = entry["ai_responded"]
    if "primary_interface" in entry:
        normalized["primary_interface"] = normalize_ai_interface(entry["primary_interface"], "primary_interface")
    if normalized["primary_interface"] is None and normalized["submitted_via"] is not None:
        normalized["primary_interface"] = normalized["submitted_via"]
    if "steps" in entry:
        normalized["steps"] = normalize_next_step_list(entry["steps"], "steps")
    if "deactivated_at" in entry:
        normalized["deactivated_at"] = normalize_iso_or_none(entry["deactivated_at"], "deactivated_at")
    return normalized
def normalize_state(raw):
    if not isinstance(raw, dict):
        return empty_state()
    state = empty_state(raw.get("updated_at") if isinstance(raw.get("updated_at"), str) else None)
    next_steps = raw.get("next_steps") or []
    if not isinstance(next_steps, list):
        raise ValueError("next_steps must be a list")
    state["next_steps"] = normalize_next_step_list(next_steps, "next_steps")
    worktrees = raw.get("worktrees") or {}
    if not isinstance(worktrees, dict):
        raise ValueError("worktrees must be an object")
    for branch, entry in worktrees.items():
        if isinstance(branch, str) and branch:
            state["worktrees"][branch] = normalize_worktree_entry(entry)
    return state

### Worktrees
def validate_worktree_update(updates):
    if not isinstance(updates, dict):
        raise ValueError("body must be an object")
    unknown = set(updates) - WORKTREE_FIELDS
    if unknown:
        raise ValueError("unknown worktree state field: " + sorted(unknown)[0])
    normalize_worktree_entry(updates)
def merge_worktree_state(state, branch, updates, updated_at=None):
    if not isinstance(branch, str) or not branch:
        raise ValueError("branch must be a string")
    validate_worktree_update(updates)
    state = normalize_state(state)
    entry = normalize_worktree_entry(state["worktrees"].get(branch))
    merged = dict(entry)
    for key, value in updates.items():
        merged[key] = value
    if updates.get("primary_interface") is None and "primary_interface" in updates and "submitted_via" not in updates:
        merged["submitted_via"] = None
    state["worktrees"][branch] = normalize_worktree_entry(merged)
    state["updated_at"] = updated_at or now_iso()
    return state, state["worktrees"][branch]
def assign_worktree_order(state, order, updated_at=None):
    if not isinstance(order, list) or not all(isinstance(item, str) and item for item in order):
        raise ValueError("order must be a list of branch names")
    state = normalize_state(state)
    seen = set()
    ordered = []
    for branch in order:
        if branch not in seen:
            seen.add(branch)
            ordered.append(branch)
    for branch in list(state["worktrees"]):
        entry = dict(state["worktrees"][branch])
        entry["order"] = None
        state["worktrees"][branch] = normalize_worktree_entry(entry)
    for index, branch in enumerate(ordered):
        entry = normalize_worktree_entry(state["worktrees"].get(branch))
        entry["order"] = index
        state["worktrees"][branch] = entry
    state["updated_at"] = updated_at or now_iso()
    return state, state["worktrees"]

### Next steps
def create_next_step(state, text, created_at=None, id_value=None, source=None):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text must be a non-empty string")
    if source is not None and not isinstance(source, str):
        raise ValueError("source must be a string or null")
    state = normalize_state(state)
    timestamp = created_at or now_iso()
    item = {"id": id_value or uuid.uuid4().hex[:12], "text": text, "done": False, "created_at": timestamp, "source": source}
    state["next_steps"].insert(0, item)
    state["updated_at"] = timestamp
    return state, item
def find_next_step(state, step_id):
    for index, item in enumerate(state.get("next_steps") or []):
        if item.get("id") == step_id:
            return index, item
    raise KeyError(step_id)
def update_next_step(state, step_id, updates, updated_at=None):
    if not isinstance(updates, dict):
        raise ValueError("body must be an object")
    unknown = set(updates) - NEXT_STEP_FIELDS
    if unknown:
        raise ValueError("unknown next step field: " + sorted(unknown)[0])
    state = normalize_state(state)
    index, item = find_next_step(state, step_id)
    updated = dict(item)
    if "text" in updates:
        if not isinstance(updates["text"], str) or not updates["text"].strip():
            raise ValueError("text must be a non-empty string")
        updated["text"] = updates["text"]
    if "done" in updates:
        if not isinstance(updates["done"], bool):
            raise ValueError("done must be a boolean")
        updated["done"] = updates["done"]
    state["next_steps"][index] = normalize_next_step(updated)
    state["updated_at"] = updated_at or now_iso()
    return state, state["next_steps"][index]
def delete_next_step(state, step_id, updated_at=None):
    state = normalize_state(state)
    index, item = find_next_step(state, step_id)
    del state["next_steps"][index]
    state["updated_at"] = updated_at or now_iso()
    return state, item
def assign_next_steps_order(state, order, updated_at=None):
    if not isinstance(order, list) or not all(isinstance(item, str) and item for item in order):
        raise ValueError("order must be a list of next step ids")
    state = normalize_state(state)
    existing_ids = {item["id"] for item in state["next_steps"]}
    seen = set()
    ordered_ids = []
    for step_id in order:
        if step_id not in existing_ids:
            raise ValueError("unknown next step id: " + step_id)
        if step_id in seen:
            continue
        seen.add(step_id)
        ordered_ids.append(step_id)
    items_by_id = {item["id"]: item for item in state["next_steps"]}
    tail = [item for item in state["next_steps"] if item["id"] not in seen]
    state["next_steps"] = [items_by_id[step_id] for step_id in ordered_ids] + tail
    state["updated_at"] = updated_at or now_iso()
    return state, state["next_steps"]

### I/O
def load_state(path):
    path = Path(path)
    if not path.exists():
        return empty_state()
    with path.open("r", encoding="utf-8") as handle:
        return normalize_state(json.load(handle))
def write_state(path, state):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_state(state)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), prefix=path.name + ".", suffix=".tmp", delete=False)
    tmp_name = handle.name
    try:
        with handle:
            json.dump(normalized, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise
    return normalized
