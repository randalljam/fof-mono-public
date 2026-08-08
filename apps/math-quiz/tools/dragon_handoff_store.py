"""Dragon Baby cross-device handoff store — atomic checkpoints under
_data/<folder>/dragon-sync/. One active owner per learner; explicit transfer
or confirmed takeover only."""
import json
import os
import secrets
import time
from pathlib import Path

VALID_DEVICE_TYPES = frozenset({"desktop", "touch"})


def _sync_dir(data_dir, folder):
    d = Path(data_dir) / folder / "dragon-sync"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _handoff_path(data_dir, folder, user):
    return _sync_dir(data_dir, folder) / f"{user}_handoff.json"


def _read_json(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def _atomic_write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, separators=(",", ":")))
    tmp.replace(path)


def _now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _default_record():
    return {
        "revision": 0,
        "updatedAt": None,
        "owner": None,
        "pendingTransfer": None,
        "checkpoint": None,
    }


def _load(data_dir, folder, user):
    path = _handoff_path(data_dir, folder, user)
    if not path.is_file():
        return _default_record()
    data = _read_json(path, None)
    if not isinstance(data, dict):
        return _default_record()
    base = _default_record()
    base.update(data)
    return base


def _save(data_dir, folder, user, data):
    import dragon_progress_guard as dpg
    path = _handoff_path(data_dir, folder, user)
    # Snapshot the previous handoff blob before every write (checkpoint / transfer / etc.).
    dpg.backup_json_file(path, "dragon-sync")
    data["updatedAt"] = _now_iso()
    _atomic_write_json(path, data)
    return data


def _validate_device_type(device_type):
    dt = str(device_type or "").strip().lower()
    if dt not in VALID_DEVICE_TYPES:
        return None
    return dt


def _validate_checkpoint(checkpoint):
    if checkpoint is None:
        return {"ok": False, "error": "checkpoint required"}
    if not isinstance(checkpoint, dict):
        return {"ok": False, "error": "checkpoint must be an object"}
    if not isinstance(checkpoint.get("gameState"), dict):
        return {"ok": False, "error": "checkpoint.gameState required"}
    return {"ok": True}


def _owner_matches(data, device_id, owner_token):
    owner = data.get("owner") or {}
    if not device_id or not owner_token:
        return False
    return owner.get("deviceId") == device_id and owner.get("token") == owner_token


def _status_payload(data, device_id, device_type):
    owner = data.get("owner")
    pending = data.get("pendingTransfer")
    is_owner = bool(owner and owner.get("deviceId") == device_id)
    can_claim = bool(
        pending
        and pending.get("targetDeviceType") == device_type
        and not is_owner
    )
    inactive_reason = None
    if pending and not is_owner:
        inactive_reason = "transferred"
    elif owner and not is_owner and not can_claim:
        inactive_reason = "other_device"
    checkpoint = data.get("checkpoint") or {}
    summary = None
    if checkpoint:
        gs = checkpoint.get("gameState") or {}
        summary = {
            "hasPendingQuiz": bool(checkpoint.get("pendingQuiz")),
            "totalBursts": gs.get("totalBursts"),
            "dragonName": gs.get("dragonName"),
        }
    out = {
        "revision": data.get("revision") or 0,
        "owner": owner,
        "pendingTransfer": pending,
        "isOwner": is_owner,
        "canClaim": can_claim,
        "inactiveReason": inactive_reason,
        "checkpointSummary": summary,
        "updatedAt": data.get("updatedAt"),
    }
    # Owner / claimer need the full blob (incl. pendingQuiz) to resume a Go gate.
    if is_owner or can_claim:
        out["checkpoint"] = data.get("checkpoint")
    return out


def dragon_handoff_view(data_dir, folder, user, device_id="", device_type=""):
    """GET status for a device."""
    data = _load(data_dir, folder, user)
    dt = _validate_device_type(device_type) or "desktop"
    found = bool(data.get("checkpoint")) or (data.get("revision") or 0) > 0
    out = {
        "ok": True,
        "found": found,
        "folder": folder,
        "user": user,
    }
    out.update(_status_payload(data, str(device_id or ""), dt))
    return out


def dragon_handoff_action(data_dir, folder, user, action, payload):
    """POST initialize | checkpoint | transfer | claim | takeover."""
    action = str(action or "").strip().lower()
    device_id = str(payload.get("deviceId") or "").strip()
    device_type = _validate_device_type(payload.get("deviceType"))
    owner_token = str(payload.get("ownerToken") or "").strip()
    expected_revision = payload.get("revision")
    checkpoint = payload.get("checkpoint")
    target_type = _validate_device_type(payload.get("targetDeviceType"))
    if not device_id:
        return {"ok": False, "error": "deviceId required"}
    if not device_type:
        return {"ok": False, "error": "deviceType must be desktop or touch"}
    data = _load(data_dir, folder, user)
    if action == "initialize":
        return _action_initialize(data_dir, folder, user, data, device_id, device_type, checkpoint)
    if action == "checkpoint":
        return _action_checkpoint(
            data_dir, folder, user, data, device_id, device_type, owner_token,
            expected_revision, checkpoint,
        )
    if action == "transfer":
        return _action_transfer(
            data_dir, folder, user, data, device_id, device_type, owner_token,
            expected_revision, checkpoint, target_type,
        )
    if action == "claim":
        return _action_claim(data_dir, folder, user, data, device_id, device_type)
    if action == "takeover":
        confirm = payload.get("confirm") is True or str(payload.get("confirm") or "").lower() in ("1", "true", "yes")
        if not confirm:
            return {"ok": False, "error": "confirm required for takeover"}
        return _action_takeover(
            data_dir, folder, user, data, device_id, device_type, checkpoint,
        )
    return {"ok": False, "error": "action must be initialize|checkpoint|transfer|claim|takeover"}


def _action_initialize(data_dir, folder, user, data, device_id, device_type, checkpoint):
    import dragon_progress_guard as dpg
    chk = _validate_checkpoint(checkpoint)
    if not chk["ok"]:
        return chk
    if data.get("checkpoint") and (data.get("revision") or 0) > 0:
        owner = data.get("owner") or {}
        if owner.get("deviceId") and owner.get("deviceId") != device_id:
            return {"ok": False, "error": "checkpoint already initialized on server"}
    token = secrets.token_hex(16)
    data["revision"] = max(1, (data.get("revision") or 0) + 1)
    data["owner"] = {
        "deviceId": device_id,
        "deviceType": device_type,
        "token": token,
        "lastSeenAt": _now_iso(),
    }
    data["pendingTransfer"] = None
    merged, preserved = dpg.preserve_checkpoint(data.get("checkpoint"), checkpoint)
    data["checkpoint"] = merged
    _save(data_dir, folder, user, data)
    out = {
        "ok": True,
        "folder": folder,
        "user": user,
        "revision": data["revision"],
        "ownerToken": token,
        "isOwner": True,
        "checkpoint": data["checkpoint"],
    }
    if preserved:
        out["preservedWorldProgress"] = True
    return out


def _action_checkpoint(data_dir, folder, user, data, device_id, device_type, owner_token, expected_revision, checkpoint):
    import dragon_progress_guard as dpg
    chk = _validate_checkpoint(checkpoint)
    if not chk["ok"]:
        return chk
    if not _owner_matches(data, device_id, owner_token):
        return {"ok": False, "error": "stale owner or wrong token"}
    rev = data.get("revision") or 0
    if expected_revision is not None and int(expected_revision) != rev:
        return {"ok": False, "error": "revision mismatch", "revision": rev}
    data["revision"] = rev + 1
    data["owner"]["lastSeenAt"] = _now_iso()
    data["owner"]["deviceType"] = device_type
    merged, preserved = dpg.preserve_checkpoint(data.get("checkpoint"), checkpoint)
    data["checkpoint"] = merged
    _save(data_dir, folder, user, data)
    out = {
        "ok": True,
        "folder": folder,
        "user": user,
        "revision": data["revision"],
        "ownerToken": owner_token,
    }
    if preserved:
        out["preservedWorldProgress"] = True
    return out


def _action_transfer(data_dir, folder, user, data, device_id, device_type, owner_token, expected_revision, checkpoint, target_type):
    import dragon_progress_guard as dpg
    chk = _validate_checkpoint(checkpoint)
    if not chk["ok"]:
        return chk
    if not target_type:
        return {"ok": False, "error": "targetDeviceType must be desktop or touch"}
    if target_type == device_type:
        return {"ok": False, "error": "targetDeviceType must differ from this device"}
    if not _owner_matches(data, device_id, owner_token):
        return {"ok": False, "error": "stale owner or wrong token"}
    rev = data.get("revision") or 0
    if expected_revision is not None and int(expected_revision) != rev:
        return {"ok": False, "error": "revision mismatch", "revision": rev}
    data["revision"] = rev + 1
    merged, preserved = dpg.preserve_checkpoint(data.get("checkpoint"), checkpoint)
    data["checkpoint"] = merged
    data["pendingTransfer"] = {
        "targetDeviceType": target_type,
        "requestedAt": _now_iso(),
        "fromRevision": data["revision"],
    }
    data["owner"] = None
    _save(data_dir, folder, user, data)
    out = {
        "ok": True,
        "folder": folder,
        "user": user,
        "revision": data["revision"],
        "pendingTransfer": data["pendingTransfer"],
        "inactiveReason": "transferred",
    }
    if preserved:
        out["preservedWorldProgress"] = True
    return out


def _action_claim(data_dir, folder, user, data, device_id, device_type):
    pending = data.get("pendingTransfer")
    if not pending:
        return {"ok": False, "error": "no pending transfer"}
    if pending.get("targetDeviceType") != device_type:
        return {"ok": False, "error": "wrong device type for pending transfer"}
    if not data.get("checkpoint"):
        return {"ok": False, "error": "no checkpoint to claim"}
    token = secrets.token_hex(16)
    data["revision"] = (data.get("revision") or 0) + 1
    data["owner"] = {
        "deviceId": device_id,
        "deviceType": device_type,
        "token": token,
        "lastSeenAt": _now_iso(),
    }
    data["pendingTransfer"] = None
    _save(data_dir, folder, user, data)
    return {
        "ok": True,
        "folder": folder,
        "user": user,
        "revision": data["revision"],
        "ownerToken": token,
        "isOwner": True,
        "checkpoint": data["checkpoint"],
    }


def _action_takeover(data_dir, folder, user, data, device_id, device_type, checkpoint):
    """Steal ownership. Prefer keeping the server checkpoint (and its pendingQuiz).

    If the client sends a checkpoint, merge carefully: never drop an in-flight
    pendingQuiz that the server already has when the client omitted it.
    """
    if checkpoint:
        import dragon_progress_guard as dpg
        chk = _validate_checkpoint(checkpoint)
        if not chk["ok"]:
            return chk
        merged, _preserved = dpg.preserve_checkpoint(data.get("checkpoint"), checkpoint)
        data["checkpoint"] = merged
    elif not data.get("checkpoint"):
        return {"ok": False, "error": "no checkpoint on server"}
    token = secrets.token_hex(16)
    data["revision"] = (data.get("revision") or 0) + 1
    data["owner"] = {
        "deviceId": device_id,
        "deviceType": device_type,
        "token": token,
        "lastSeenAt": _now_iso(),
    }
    data["pendingTransfer"] = None
    _save(data_dir, folder, user, data)
    return {
        "ok": True,
        "folder": folder,
        "user": user,
        "revision": data["revision"],
        "ownerToken": token,
        "isOwner": True,
        "checkpoint": data["checkpoint"],
    }
