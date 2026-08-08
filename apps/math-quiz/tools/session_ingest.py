#!/usr/bin/env python3
"""Reusable single-session SQLite ingest for Math Quiz-compatible runs.

This is the shared local-disk path used by the Math Quiz dev server and by external
local apps such as MathQuest:

1. Preserve the raw timestamped single-session SQLite file in
   _data/_single-session-sqlite-files/.
2. Accumulate that session into the active per-user folder with anchor_store's
   create / append / single-to-multi naming rules.

The module is importable from Python and also exposes a small JSON-printing CLI so a
local Minecraft server can invoke the same logic without reimplementing SQLite merge
behavior in Java.
"""
import argparse
import json
import re
import shutil
from pathlib import Path

import anchor_store

SINGLE_SESSION_DIR = "_single-session-sqlite-files"
_DATE = r"\d{4}-\d{2}-\d{2}"
_TIME = r"\d{6}"


def archive_single_session(data_dir, filename, raw_bytes=None, src_path=None, single_session_folder=SINGLE_SESSION_DIR):
    """Write or copy one raw single-session SQLite file into the archive folder."""
    if raw_bytes is None and src_path is None:
        raise ValueError("raw_bytes or src_path is required")
    data_dir = Path(data_dir)
    archive_dir = data_dir / single_session_folder
    archive_dir.mkdir(parents=True, exist_ok=True)
    dest = archive_dir / Path(filename).name
    if raw_bytes is not None:
        dest.write_bytes(raw_bytes)
    else:
        src = Path(src_path)
        if src.resolve() != dest.resolve():
            shutil.copyfile(src, dest)
    return {
        "singleSessionFile": dest.name,
        "singleSessionPath": str(dest),
    }


def _stamp_from_filename(filename, prefix):
    parsed = anchor_store.parse_filename(Path(filename).name, prefix=prefix)
    if not parsed:
        m = re.search(rf"_(?P<date>{_DATE})_(?P<time>{_TIME})\.sqlite$", Path(filename).name)
        if m:
            return f"{m['date']}_{m['time']}"
    if not parsed or parsed.get("multi") or not parsed.get("time"):
        raise ValueError(f"Cannot infer single-session stamp from {filename!r} for prefix {prefix!r}")
    return f"{parsed['date']}_{parsed['time']}"


def _parse_user_file_any_prefix(filename, user_name):
    name = re.escape(user_name)
    m = re.match(rf"^(?P<prefix>.+)_{name}_(?P<date>{_DATE})(?:_(?P<trail>[^.]+))?\.sqlite$", filename)
    if not m:
        return None
    trail = m["trail"]
    is_single = bool(trail and re.fullmatch(_TIME, trail))
    return {
        "filename": filename,
        "prefix": m["prefix"],
        "date": m["date"],
        "time": trail if is_single else None,
        "suffix": None if is_single else trail,
        "multi": not is_single,
    }


def _pick_latest_user_file_any_prefix(active_dir, user_name):
    matches = []
    for filename, modified in anchor_store.local_entries(active_dir):
        parsed = _parse_user_file_any_prefix(filename, user_name)
        if parsed:
            parsed["modified"] = modified
            matches.append(parsed)
    if not matches:
        return None

    def key(parsed):
        # The filename date after _<name>_ is the primary recency rule. A same-day
        # multi-session file sorts after a same-day single-session file.
        return (
            parsed["date"],
            parsed["time"] or "999999",
            parsed["modified"] or 0,
            parsed["filename"],
        )

    matches.sort(key=key)
    return matches[-1]


def has_existing_user_file(active_dir, user_name, prefix=anchor_store.PREFIX, match_any_prefix=False):
    if match_any_prefix and _pick_latest_user_file_any_prefix(active_dir, user_name) is not None:
        return True
    return anchor_store.pick_latest(anchor_store.local_entries(active_dir), user_name, prefix=prefix) is not None


def _accumulate_into_existing_target(active_dir, user_name, single_session_path, target):
    active_dir = Path(active_dir)
    single_session_path = Path(single_session_path)
    existing_filenames = [fn for fn, _ in anchor_store.local_entries(active_dir)]
    target_name = target["filename"]
    if target["multi"]:
        out_name = target_name
    else:
        out_name = anchor_store.next_multi_name(
            existing_filenames,
            user_name,
            target["date"],
            prefix=target["prefix"],
        )
    out_path = active_dir / out_name
    target_path = active_dir / target_name
    if target_path.resolve() != out_path.resolve():
        shutil.copyfile(target_path, out_path)
    added = anchor_store.append_session(str(out_path), str(single_session_path))
    if target_name != out_name:
        old = active_dir / target_name
        if old.exists() and old.resolve() != out_path.resolve():
            old.unlink()
    return {
        "action": "append",
        "filename": out_name,
        "target": target_name,
        "path": str(out_path),
        "added": added,
        "matchedBy": "name-date-any-prefix",
    }


def accumulate_single_session_to_file(active_file, single_session_path):
    """Accumulate an archived single-session file into one exact active SQLite file."""
    active_file = Path(active_file)
    single_session_path = Path(single_session_path)
    active_file.parent.mkdir(parents=True, exist_ok=True)
    if active_file.exists():
        added = anchor_store.append_session(str(active_file), str(single_session_path))
        action = "append"
    else:
        shutil.copyfile(single_session_path, active_file)
        added = 1
        action = "create"
    return {
        "action": action,
        "filename": active_file.name,
        "target": active_file.name,
        "path": str(active_file),
        "added": added,
        "matchedBy": "exact-active-file",
        "ok": True,
        "activeDir": str(active_file.parent),
    }


def accumulate_single_session(
    active_dir,
    user_name,
    single_session_path,
    *,
    stamp=None,
    prefix=anchor_store.PREFIX,
    force_new=False,
    require_existing=False,
    match_any_prefix=False,
):
    """Accumulate an archived single-session file into one active per-user SQLite file."""
    active_dir = Path(active_dir)
    single_session_path = Path(single_session_path)
    if stamp is None:
        stamp = _stamp_from_filename(single_session_path.name, prefix)
    if require_existing and not force_new and not has_existing_user_file(
        active_dir, user_name, prefix=prefix, match_any_prefix=match_any_prefix
    ):
        return {
            "ok": False,
            "error": "no-continue-file",
            "message": f'No existing file for "{user_name}" in "{active_dir.name}" to continue.',
        }
    target = None if force_new or not match_any_prefix else _pick_latest_user_file_any_prefix(active_dir, user_name)
    if target is not None:
        result = _accumulate_into_existing_target(active_dir, user_name, single_session_path, target)
    else:
        result = anchor_store.accumulate(active_dir, user_name, stamp, single_session_path, prefix=prefix,
                                         force_new=force_new)
    result["ok"] = True
    result["activeDir"] = str(active_dir)
    return result


def ingest_single_session(
    single_session_path,
    user_name,
    active_dir,
    *,
    active_file=None,
    archive_dir=None,
    stamp=None,
    prefix=anchor_store.PREFIX,
    force_new=False,
    require_existing=False,
    match_any_prefix=False,
):
    """Archive a raw single-session file if needed, then accumulate it into active_dir."""
    single_session_path = Path(single_session_path)
    if archive_dir is not None:
        archive_dir = Path(archive_dir)
        data_dir = archive_dir.parent if archive_dir.name == SINGLE_SESSION_DIR else archive_dir.parent
        archive = archive_single_session(data_dir, single_session_path.name, src_path=single_session_path,
                                         single_session_folder=archive_dir.name)
        archived_path = Path(archive["singleSessionPath"])
    else:
        archive = {"singleSessionFile": single_session_path.name, "singleSessionPath": str(single_session_path)}
        archived_path = single_session_path
    if active_file is not None:
        result = accumulate_single_session_to_file(active_file, archived_path)
    else:
        result = accumulate_single_session(
            active_dir,
            user_name,
            archived_path,
            stamp=stamp,
            prefix=prefix,
            force_new=force_new,
            require_existing=require_existing,
            match_any_prefix=match_any_prefix,
        )
    return {**archive, **result}


def ingest_bytes(
    data_dir,
    active_folder,
    user_name,
    stamp,
    raw_bytes,
    *,
    prefix=anchor_store.PREFIX,
    force_new=False,
    require_existing=False,
    match_any_prefix=False,
    single_session_folder=SINGLE_SESSION_DIR,
):
    """Archive raw bytes and accumulate them into data_dir/active_folder."""
    data_dir = Path(data_dir)
    filename = anchor_store.single_session_name(user_name, stamp, prefix=prefix)
    archive = archive_single_session(data_dir, filename, raw_bytes=raw_bytes, single_session_folder=single_session_folder)
    result = accumulate_single_session(
        data_dir / active_folder,
        user_name,
        Path(archive["singleSessionPath"]),
        stamp=stamp,
        prefix=prefix,
        force_new=force_new,
        require_existing=require_existing,
        match_any_prefix=match_any_prefix,
    )
    return {**archive, **result}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Archive and accumulate one Math Quiz-compatible SQLite session.")
    parser.add_argument("--single-session", required=True, help="Path to the raw single-session .sqlite file")
    parser.add_argument("--user", required=True, help="Canonical/real user name")
    parser.add_argument("--active-dir", help="Folder containing active per-user accumulated DBs")
    parser.add_argument("--active-file", help="Exact active accumulated DB to create or append")
    parser.add_argument("--archive-dir", help="Raw single-session archive folder")
    parser.add_argument("--stamp", help="YYYY-MM-DD_HHMMSS; inferred from filename when omitted")
    parser.add_argument("--prefix", default=anchor_store.PREFIX, help="Filename prefix, e.g. math-flu or mathquest")
    parser.add_argument("--match-any-prefix", action="store_true",
                        help="Match the active file by _<user>_ and newest filename date, ignoring prefix")
    parser.add_argument("--force-new", action="store_true", help="Start a fresh lineage")
    parser.add_argument("--require-existing", action="store_true", help="Fail Continue when the user has no active file")
    args = parser.parse_args(argv)
    if not args.active_dir and not args.active_file:
        parser.error("--active-dir or --active-file is required")

    result = ingest_single_session(
        args.single_session,
        args.user,
        args.active_dir,
        active_file=args.active_file,
        archive_dir=args.archive_dir,
        stamp=args.stamp,
        prefix=args.prefix,
        force_new=args.force_new,
        require_existing=args.require_existing,
        match_any_prefix=args.match_any_prefix,
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
