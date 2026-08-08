#!/usr/bin/env python3
"""
file: apps/math-quiz/tools/ingest_drop_folder.py
title: Ingest single-session SQLite files dropped by OTHER apps into per-person files

A general server-side ingest for single-session .sqlite files that some OTHER application
drops into a watched folder — e.g. the MathQuest Minecraft mod (prefix "math-quest"). It does
for those drops exactly what anchor.html / dev_server's save-run does for a finished quiz: find
the learner, then create or append into that person's accumulated file in a destination folder
(anchor_store.accumulate — create / Continue-latest append / single->multi rename, idempotent).

  drop folder:   _data/_single-session-sqlite-files/   (shared with the anchor archive)
  match:         files named "<SOURCE_PREFIX>_*.sqlite"  (SOURCE_PREFIX="" matches ANY .sqlite)
  destination:   _data/<DEST_FOLDER>/   accumulated as  "<OUTPUT_PREFIX>_<name>_<date>...sqlite"

Test-vs-live is a one-constant switch: DEST_FOLDER defaults to "test" (TEST_DEST) for trials;
point it at "tlkids" (LIVE_DEST) — or pass --dest tlkids — to ingest real learner data.

Identity (name + start timestamp) for a drop comes from its filename when it follows the
<prefix>_<name>_<date>_<time> convention, else from its Sessions row (user_name + start_time).

A small JSON ledger per (output-prefix, destination) records what has been ingested so reruns
skip unchanged files; anchor_store.append_session dedups by session_id, so the ledger is an
optimization/record, not a correctness requirement. Source files are left in place (never moved
or deleted). Naming rules: docs/SPEC.md §8a. Run locally; never deploy.

Usage:
    cd apps/math-quiz
    python3 tools/ingest_drop_folder.py --dry-run            # show what would be ingested
    python3 tools/ingest_drop_folder.py                      # ingest math-quest drops into _data/test
    python3 tools/ingest_drop_folder.py --dest tlkids        # go live: ingest into _data/tlkids
    python3 tools/ingest_drop_folder.py --prefix ""          # ingest ANY .sqlite in the drop folder
"""
import os
import re
import sys
import json
import time
import sqlite3
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anchor_store  # noqa: E402

APP_DIR = Path(__file__).resolve().parent.parent          # apps/math-quiz
DATA_DIR = APP_DIR / os.environ.get("ANCHOR_DATA_DIR", "_data")

### Config constants (the test-vs-live switch lives here)
DROP_SUBDIR = "_single-session-sqlite-files"   # where other apps drop single-session files (shared w/ anchor archive)
TEST_DEST = "test"                             # destination folder while testing the pipeline
LIVE_DEST = "tlkids"                           # destination folder for real learner data
DEST_FOLDER = TEST_DEST                         # <-- flip to LIVE_DEST (or pass --dest tlkids) to go live
SOURCE_PREFIX = "math-quest"                    # only ingest files named "<prefix>_*.sqlite" ("" = any .sqlite)
OUTPUT_PREFIX = "math-quest"                     # prefix for the accumulated per-person files written to DEST_FOLDER
LEDGER_SUBDIR = "_ingest-ledgers"               # _data/_ingest-ledgers/<output_prefix>__<dest>.json

### Identity extraction
def _table_exists(conn, t):
    """True if table `t` exists in the sqlite connection."""
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone() is not None
def _normalize_stamp(raw, fallback_mtime):
    """Coerce a start_time (or fall back to the file mtime) into 'YYYY-MM-DD_HHMMSS'."""
    if raw:
        m = re.search(r"(\d{4}-\d{2}-\d{2})[ T_](\d{2}):?(\d{2}):?(\d{2})", str(raw))
        if m:
            return f"{m.group(1)}_{m.group(2)}{m.group(3)}{m.group(4)}"
    return time.strftime("%Y-%m-%d_%H%M%S", time.localtime(fallback_mtime))
def _identity_from_db(src_path):
    """(user_name, start_time) from the earliest Sessions row, or (None, None)."""
    try:
        c = sqlite3.connect(str(src_path))
    except Exception:
        return None, None
    try:
        if not _table_exists(c, "Sessions"):
            return None, None
        cols = {r[1] for r in c.execute("PRAGMA table_info(Sessions)")}
        if "user_name" not in cols:
            return None, None
        order = " ORDER BY start_time" if "start_time" in cols else ""
        st = "start_time" if "start_time" in cols else "NULL"
        row = c.execute(f"SELECT user_name, {st} FROM Sessions{order} LIMIT 1").fetchone()
        return (row[0], row[1]) if row else (None, None)
    except Exception:
        return None, None
    finally:
        c.close()
def extract_identity(src_path, filename, source_prefix):
    """(name, stamp) for a dropped file. Prefer the filename when it matches
    <source_prefix>_<name>_<date>_<time>; else read user_name/start_time from the Sessions
    row. stamp is normalized to 'YYYY-MM-DD_HHMMSS' (file mtime as a last resort)."""
    try:
        mtime = Path(src_path).stat().st_mtime
    except OSError:
        mtime = time.time()
    name = stamp = None
    if source_prefix:
        p = anchor_store.parse_filename(filename, prefix=source_prefix)
        if p:
            name = p["name"]
            if p["time"]:
                stamp = f"{p['date']}_{p['time']}"
    if not name or not stamp:
        db_name, db_start = _identity_from_db(src_path)
        name = name or db_name
        stamp = stamp or _normalize_stamp(db_start, mtime)
    return name, stamp

### Ledger (per output-prefix + destination)
def _ledger_path(data_dir, output_prefix, dest_folder):
    """JSON ledger path scoped to (output_prefix, dest_folder) so 'test' and 'tlkids' ingests
    are tracked independently — switching destinations re-ingests rather than false-skipping."""
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", f"{output_prefix}__{dest_folder}")
    return Path(data_dir) / LEDGER_SUBDIR / f"{safe}.json"
def _load_ledger(path):
    """Load the ingest ledger (filename -> record), or {} if absent/unreadable."""
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return {}
def _save_ledger(path, ledger):
    """Write the ledger atomically (via a temp file + replace)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(ledger, indent=2, sort_keys=True))
    tmp.replace(path)
def _file_sig(src_path):
    """(size, int(mtime)) signature used to detect a changed file under the same name."""
    st = Path(src_path).stat()
    return st.st_size, int(st.st_mtime)

### Core ingest
def ingest_folder(drop_dir=None, dest_folder=DEST_FOLDER, source_prefix=SOURCE_PREFIX,
                  output_prefix=OUTPUT_PREFIX, data_dir=None, dry_run=False, force=False):
    """Scan drop_dir for single-session .sqlite files matching source_prefix and accumulate
    each into the per-person file for its learner in data_dir/dest_folder (OUTPUT_PREFIX naming).
    Returns a summary dict {drop, dest, ledger, ingested, skipped, errors, results}. force=True
    reprocesses ledgered files (still idempotent — append_session dedups by session_id)."""
    data_dir = Path(data_dir) if data_dir else DATA_DIR
    drop_dir = Path(drop_dir) if drop_dir else (data_dir / DROP_SUBDIR)
    dest_dir = data_dir / dest_folder
    ledger_path = _ledger_path(data_dir, output_prefix, dest_folder)
    ledger = _load_ledger(ledger_path)
    results, changed = [], False
    for src in sorted(drop_dir.glob("*.sqlite")) if drop_dir.exists() else []:
        fn = src.name
        if source_prefix and not fn.startswith(source_prefix + "_"):
            continue   # not from this source app — leave it for the owning pipeline
        size, mtime = _file_sig(src)
        prior = ledger.get(fn)
        if prior and not force and prior.get("size") == size and prior.get("mtime") == mtime:
            results.append({"file": fn, "action": "skip-ledger", "added": 0})
            continue
        name, stamp = extract_identity(src, fn, source_prefix)
        if not name:
            results.append({"file": fn, "action": "error", "error": "no-user-name"})
            continue
        if dry_run:
            results.append({"file": fn, "action": "would-ingest", "name": name, "stamp": stamp})
            continue
        try:
            res = anchor_store.accumulate(dest_dir, name, stamp, str(src), prefix=output_prefix)
        except Exception as exc:
            results.append({"file": fn, "action": "error", "error": str(exc)})
            continue
        ledger[fn] = {"size": size, "mtime": mtime, "name": name, "stamp": stamp,
                      "action": res["action"], "filename": res["filename"], "added": res["added"],
                      "ingested_at": time.strftime("%Y-%m-%d_%H%M%S")}
        changed = True
        results.append({"file": fn, "name": name, **res})
    if changed and not dry_run:
        _save_ledger(ledger_path, ledger)
    ingested = sum(1 for r in results if r.get("action") in ("create", "append"))
    skipped = sum(1 for r in results if r.get("action") == "skip-ledger")
    errors = sum(1 for r in results if r.get("action") == "error")
    return {"drop": str(drop_dir), "dest": str(dest_dir), "ledger": str(ledger_path),
            "ingested": ingested, "skipped": skipped, "errors": errors, "results": results}

### CLI
def _print_summary(summary, dry_run):
    """Human-readable run summary to stdout."""
    print(f"drop:   {summary['drop']}")
    print(f"dest:   {summary['dest']}")
    print(f"ledger: {summary['ledger']}")
    for r in summary["results"]:
        act = r.get("action", "?")
        if act == "would-ingest":
            print(f"  WOULD INGEST  {r['file']}  -> {r['name']} ({r['stamp']})")
        elif act in ("create", "append"):
            print(f"  {act.upper():7} {r['file']}  -> {r['name']}: {r['filename']} (+{r['added']} session)")
        elif act == "skip-ledger":
            print(f"  skip          {r['file']}  (already ingested)")
        elif act == "error":
            print(f"  ERROR         {r['file']}  ({r.get('error')})")
    tag = "(dry run) " if dry_run else ""
    print(f"{tag}ingested {summary['ingested']}, skipped {summary['skipped']}, errors {summary['errors']}")
def main(argv=None):
    """Parse args and run one ingest pass."""
    ap = argparse.ArgumentParser(description="Ingest dropped single-session SQLite files into per-person files.")
    ap.add_argument("--dest", default=DEST_FOLDER, help=f"destination folder under _data/ (default {DEST_FOLDER}; live: {LIVE_DEST})")
    ap.add_argument("--prefix", default=SOURCE_PREFIX, help=f'source filename prefix to match (default "{SOURCE_PREFIX}"; "" = any .sqlite)')
    ap.add_argument("--output-prefix", default=OUTPUT_PREFIX, help=f"prefix for accumulated per-person files (default {OUTPUT_PREFIX})")
    ap.add_argument("--drop", default=None, help=f"drop folder to scan (default _data/{DROP_SUBDIR})")
    ap.add_argument("--data-dir", default=None, help="override _data/ root")
    ap.add_argument("--dry-run", action="store_true", help="show what would be ingested without writing")
    ap.add_argument("--force", action="store_true", help="reprocess ledgered files (still idempotent)")
    args = ap.parse_args(argv)
    summary = ingest_folder(drop_dir=args.drop, dest_folder=args.dest, source_prefix=args.prefix,
                            output_prefix=args.output_prefix, data_dir=args.data_dir,
                            dry_run=args.dry_run, force=args.force)
    _print_summary(summary, args.dry_run)
    return 0 if summary["errors"] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
