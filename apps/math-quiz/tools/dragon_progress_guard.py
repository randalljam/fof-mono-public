"""Guard + snapshot helpers for dragon world progress (gems, signs, nest stations).

Empty browser localStorage (wrong origin/port, cleared site data) used to POST a
blank snapshot and wipe the on-disk GM / handoff files. These helpers:
  1. score world-progress richness
  2. merge-preserve richer fields when an incoming save looks wiped
  3. copy the previous JSON file into _BACKUP before overwrite
"""
import os
import time
from pathlib import Path


DEFAULT_BACKUP_PARENT = Path("/Users/randytrue/Documents/Code/_BACKUP/math-quiz")
MAX_SNAPSHOTS_PER_STEM = 80


def backup_parent_dir(sqlite_backup_root=None):
    """Sibling of sqlite-snapshots (or ANCHOR_DRAGON_BACKUP_DIR)."""
    env = os.environ.get("ANCHOR_DRAGON_BACKUP_DIR", "").strip()
    if env:
        return Path(env).expanduser()
    if sqlite_backup_root is not None:
        return Path(sqlite_backup_root).expanduser().resolve().parent
    return DEFAULT_BACKUP_PARENT


def snapshot_dir(kind, sqlite_backup_root=None):
    """kind: 'dragon-gm' | 'dragon-sync'."""
    return backup_parent_dir(sqlite_backup_root) / f"{kind}-snapshots"


def backup_json_file(src_path, kind, sqlite_backup_root=None, stamp=None):
    """Copy existing JSON to kind-snapshots before overwrite. Best-effort."""
    try:
        src = Path(src_path)
        if not src.is_file() or src.stat().st_size == 0:
            return None
        stamp = stamp or time.strftime("%Y-%m-%d_%H%M%S")
        dest_dir = snapshot_dir(kind, sqlite_backup_root)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{src.stem}_backup_{stamp}{src.suffix}"
        dest.write_bytes(src.read_bytes())
        _prune_snapshots(dest_dir, src.stem)
        return str(dest)
    except Exception as exc:
        return {"backupError": str(exc)}


def _prune_snapshots(dest_dir, stem):
    try:
        files = sorted(
            dest_dir.glob(f"{stem}_backup_*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in files[MAX_SNAPSHOTS_PER_STEM:]:
            try:
                old.unlink()
            except Exception:
                pass
    except Exception:
        pass


def world_progress_score(state):
    """Higher = more kid world progress worth protecting."""
    if not isinstance(state, dict):
        return 0
    stations = state.get("stations") or {}
    signs = stations.get("signs") if isinstance(stations, dict) else {}
    levels = stations.get("levels") if isinstance(stations, dict) else {}
    if not isinstance(signs, dict):
        signs = {}
    if not isinstance(levels, dict):
        levels = {}
    sign_chars = sum(len(str(v or "").strip()) for v in signs.values())
    level_sum = sum(int(v or 0) for v in levels.values() if str(v).strip() != "")
    volcano = state.get("volcano") or {}
    lava = state.get("lava") or {}
    stopped = lava.get("stopped") if isinstance(lava, dict) else []
    if not isinstance(stopped, list):
        stopped = []
    gems = int(state.get("gems") or 0)
    bursts = int(state.get("totalBursts") or 0)
    name = 10 if state.get("dragonName") else 0
    seen = len(state.get("seenBeatIds") or []) if isinstance(state.get("seenBeatIds"), list) else 0
    scrolls = int(state.get("scrollsCollected") or 0)
    cleared = int(volcano.get("cleared") or 0) if isinstance(volcano, dict) else 0
    summited = 20 if isinstance(volcano, dict) and volcano.get("summited") else 0
    return (
        gems
        + bursts * 3
        + sign_chars * 2
        + level_sum * 25
        + cleared * 15
        + summited
        + len(stopped) * 12
        + name
        + max(seen, scrolls)
    )


def _merge_station_maps(existing_stations, incoming_stations):
    existing_stations = existing_stations if isinstance(existing_stations, dict) else {}
    incoming_stations = incoming_stations if isinstance(incoming_stations, dict) else {}
    out = dict(incoming_stations)
    ex_signs = existing_stations.get("signs") if isinstance(existing_stations.get("signs"), dict) else {}
    in_signs = incoming_stations.get("signs") if isinstance(incoming_stations.get("signs"), dict) else {}
    merged_signs = dict(in_signs)
    for key, val in ex_signs.items():
        if str(val or "").strip() and not str(merged_signs.get(key) or "").strip():
            merged_signs[key] = val
    ex_levels = existing_stations.get("levels") if isinstance(existing_stations.get("levels"), dict) else {}
    in_levels = incoming_stations.get("levels") if isinstance(incoming_stations.get("levels"), dict) else {}
    merged_levels = dict(in_levels)
    for key, val in ex_levels.items():
        try:
            ev = int(val or 0)
        except (TypeError, ValueError):
            ev = 0
        try:
            iv = int(merged_levels.get(key) or 0)
        except (TypeError, ValueError):
            iv = 0
        if ev > iv:
            merged_levels[key] = ev
    out["signs"] = merged_signs
    out["levels"] = merged_levels
    if existing_stations.get("intro") and not out.get("intro"):
        out["intro"] = True
    return out


def _merge_volcano(existing, incoming):
    existing = existing if isinstance(existing, dict) else {}
    incoming = incoming if isinstance(incoming, dict) else {}
    out = dict(incoming)
    if existing.get("intro") and not out.get("intro"):
        out["intro"] = True
    try:
        ec = int(existing.get("cleared") or 0)
    except (TypeError, ValueError):
        ec = 0
    try:
        ic = int(out.get("cleared") or 0)
    except (TypeError, ValueError):
        ic = 0
    out["cleared"] = max(ec, ic)
    out["summited"] = bool(out.get("summited") or existing.get("summited"))
    return out


def _merge_lava(existing, incoming):
    existing = existing if isinstance(existing, dict) else {}
    incoming = incoming if isinstance(incoming, dict) else {}
    out = dict(incoming)
    if existing.get("intro") and not out.get("intro"):
        out["intro"] = True
    out["won"] = bool(out.get("won") or existing.get("won"))
    if out.get("startPct") is None and existing.get("startPct") is not None:
        out["startPct"] = existing.get("startPct")
    ex_stopped = existing.get("stopped") if isinstance(existing.get("stopped"), list) else []
    in_stopped = out.get("stopped") if isinstance(out.get("stopped"), list) else []
    # Keep the larger unique set (order: incoming first, then existing extras).
    seen = set()
    merged = []
    for item in list(in_stopped) + list(ex_stopped):
        if item in seen:
            continue
        seen.add(item)
        merged.append(item)
    out["stopped"] = merged
    return out


def _looks_wiped(state):
    """True when a save looks like blank localStorage (the failure mode we saw)."""
    if not isinstance(state, dict):
        return True
    stations = state.get("stations") or {}
    signs = stations.get("signs") if isinstance(stations, dict) else {}
    levels = stations.get("levels") if isinstance(stations, dict) else {}
    if not isinstance(signs, dict):
        signs = {}
    if not isinstance(levels, dict):
        levels = {}
    sign_chars = sum(len(str(v or "").strip()) for v in signs.values())
    level_sum = sum(int(v or 0) for v in levels.values() if str(v).strip() != "")
    gems = int(state.get("gems") or 0)
    name = state.get("dragonName")
    volcano = state.get("volcano") or {}
    cleared = int(volcano.get("cleared") or 0) if isinstance(volcano, dict) else 0
    # Wipe signature: no sign text, no station levels, no/low gems, no name.
    return sign_chars == 0 and level_sum == 0 and gems < 20 and not name and cleared == 0
def preserve_world_progress(existing_state, incoming_state):
    """If incoming looks wiped relative to existing, keep the richer world fields.

    Only intervenes for wipe-shaped saves (empty signs/stations, low gems, no
    dragon name). Ordinary handoff/takeover updates with real progress pass through.
    Returns (merged_state, preserved).
    """
    if not isinstance(incoming_state, dict):
        return existing_state if isinstance(existing_state, dict) else {}, bool(existing_state)
    if not isinstance(existing_state, dict) or not existing_state:
        return dict(incoming_state), False
    ex_score = world_progress_score(existing_state)
    in_score = world_progress_score(incoming_state)
    # Only intervene when existing is meaningfully richer AND incoming looks wiped.
    if ex_score < 30 or in_score >= ex_score or not _looks_wiped(incoming_state):
        return dict(incoming_state), False
    out = dict(incoming_state)
    preserved = False
    if int(existing_state.get("gems") or 0) > int(out.get("gems") or 0):
        out["gems"] = existing_state.get("gems")
        preserved = True
    if existing_state.get("dragonName") and not out.get("dragonName"):
        out["dragonName"] = existing_state.get("dragonName")
        preserved = True
    if int(existing_state.get("totalBursts") or 0) > int(out.get("totalBursts") or 0):
        out["totalBursts"] = existing_state.get("totalBursts")
        preserved = True
    try:
        ex_pct = float(existing_state.get("maxPct") or 0)
    except (TypeError, ValueError):
        ex_pct = 0
    try:
        in_pct = float(out.get("maxPct") or 0)
    except (TypeError, ValueError):
        in_pct = 0
    if ex_pct > in_pct:
        out["maxPct"] = existing_state.get("maxPct")
        preserved = True
    for key in ("celebratedIds", "unlockedIds", "visitedStones", "seenBeatIds"):
        ex_list = existing_state.get(key) if isinstance(existing_state.get(key), list) else []
        in_list = out.get(key) if isinstance(out.get(key), list) else []
        if ex_list:
            merged = list(in_list)
            for item in ex_list:
                if item not in merged:
                    merged.append(item)
            if merged != in_list:
                out[key] = merged
                preserved = True
    if existing_state.get("eggFound") and not out.get("eggFound"):
        out["eggFound"] = True
        preserved = True
    if existing_state.get("hatched") and not out.get("hatched"):
        out["hatched"] = True
        preserved = True
    if existing_state.get("stations") or out.get("stations"):
        merged_stations = _merge_station_maps(existing_state.get("stations"), out.get("stations"))
        if merged_stations != (out.get("stations") or {}):
            out["stations"] = merged_stations
            preserved = True
    if existing_state.get("volcano") or out.get("volcano"):
        merged_v = _merge_volcano(existing_state.get("volcano"), out.get("volcano"))
        if merged_v != (out.get("volcano") or {}):
            out["volcano"] = merged_v
            preserved = True
    if existing_state.get("lava") or out.get("lava"):
        merged_l = _merge_lava(existing_state.get("lava"), out.get("lava"))
        if merged_l != (out.get("lava") or {}):
            out["lava"] = merged_l
            preserved = True
    ex_recent = existing_state.get("recentBursts") if isinstance(existing_state.get("recentBursts"), list) else []
    in_recent = out.get("recentBursts") if isinstance(out.get("recentBursts"), list) else []
    if len(ex_recent) > len(in_recent):
        out["recentBursts"] = ex_recent
        preserved = True
    if int(existing_state.get("scrollsCollected") or 0) > int(out.get("scrollsCollected") or 0):
        out["scrollsCollected"] = existing_state.get("scrollsCollected")
        preserved = True
    return out, preserved


def preserve_checkpoint(existing_checkpoint, incoming_checkpoint):
    """Apply world-progress preserve to checkpoint.gameState."""
    if not isinstance(incoming_checkpoint, dict):
        return existing_checkpoint if isinstance(existing_checkpoint, dict) else {}, False
    out = dict(incoming_checkpoint)
    existing_gs = (existing_checkpoint or {}).get("gameState") if isinstance(existing_checkpoint, dict) else None
    incoming_gs = out.get("gameState")
    merged_gs, preserved = preserve_world_progress(existing_gs, incoming_gs)
    out["gameState"] = merged_gs
    # Never drop an in-flight pendingQuiz the server already has.
    if isinstance(existing_checkpoint, dict):
        if existing_checkpoint.get("pendingQuiz") and not out.get("pendingQuiz"):
            out["pendingQuiz"] = existing_checkpoint["pendingQuiz"]
            preserved = True
    return out, preserved
