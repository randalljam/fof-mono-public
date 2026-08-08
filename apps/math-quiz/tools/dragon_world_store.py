"""Canonical full dragon gameState on disk — mirrors browser localStorage.

Stored at _data/<folder>/dragon-world/<user>.json so any device on the LAN
dev server can load the same gems / signs / nest / story world. Independent of
handoff ownership (which is about who is actively playing right now).
"""
import json
import time
from pathlib import Path

import dragon_progress_guard as dpg


def _world_dir(data_dir, folder):
    d = Path(data_dir) / folder / "dragon-world"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _world_path(data_dir, folder, user):
    return _world_dir(data_dir, folder) / f"{user}.json"


def _read_json(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def dragon_world_view(data_dir, folder, user):
    path = _world_path(data_dir, folder, user)
    if not path.is_file():
        return {"ok": True, "found": False, "folder": folder, "user": user}
    data = _read_json(path, None)
    if not isinstance(data, dict) or not isinstance(data.get("gameState"), dict):
        return {"ok": True, "found": False, "folder": folder, "user": user}
    return {
        "ok": True,
        "found": True,
        "folder": folder,
        "user": user,
        "updatedAt": data.get("updatedAt"),
        "gameState": data.get("gameState"),
    }


def save_dragon_world(data_dir, folder, user, game_state, sqlite_backup_root=None):
    """Persist full gameState; backup previous file; refuse wipe-shaped overwrites."""
    if not isinstance(game_state, dict):
        return {"ok": False, "error": "gameState required"}
    path = _world_path(data_dir, folder, user)
    existing = _read_json(path, None) if path.is_file() else None
    existing_gs = (existing or {}).get("gameState") if isinstance(existing, dict) else None
    incoming = dict(game_state)
    if "learner" not in incoming:
        incoming["learner"] = user
    else:
        incoming["learner"] = user
    merged, preserved = dpg.preserve_world_progress(existing_gs, incoming)
    backup = dpg.backup_json_file(path, "dragon-world", sqlite_backup_root=sqlite_backup_root)
    payload = {
        "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "gameState": merged,
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload))
    tmp.replace(path)
    out = {
        "ok": True,
        "folder": folder,
        "user": user,
        "updatedAt": payload["updatedAt"],
        "gameState": merged,
    }
    if backup:
        out["backup"] = backup
    if preserved:
        out["preservedWorldProgress"] = True
    return out


def clone_dragon_world(data_dir, folder, source_user, target_user, sqlite_backup_root=None):
    """Copy source's world file onto target (rewrites learner name)."""
    src = _world_path(data_dir, folder, source_user)
    dst = _world_path(data_dir, folder, target_user)
    if not src.is_file():
        if dst.is_file():
            try:
                dst.unlink()
            except OSError:
                pass
        return {"copied": False}
    data = _read_json(src, None)
    if not isinstance(data, dict) or not isinstance(data.get("gameState"), dict):
        return {"copied": False}
    gs = dict(data["gameState"])
    gs["learner"] = target_user
    return {
        "copied": True,
        **{k: v for k, v in save_dragon_world(
            data_dir, folder, target_user, gs, sqlite_backup_root=sqlite_backup_root
        ).items() if k != "ok"},
    }
