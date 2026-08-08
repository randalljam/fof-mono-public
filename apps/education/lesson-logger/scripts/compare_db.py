#!/usr/bin/env python3
# Download lessons.db from Hermes and the lesson-logger dashboard on Fly, compare
# entry rows, and print a short summary or a long entry listing with summary last.
#
# Usage:
#   python3 compare_db.py                 # download both, short summary
#   python3 compare_db.py --long          # download both, list all entries, summary at end
#   python3 compare_db.py --hermes-db A --dashboard-db B   # compare local files only
import argparse
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

### Fly apps and remote paths
HERMES_APP = "[FLY-APP-NAME]"
DASHBOARD_APP = "fof-lesson-dash"
HERMES_REMOTE_DB = "/opt/data/lesson-logs/lessons.db"
DASHBOARD_REMOTE_DB = "/data/lessons.db"
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[3]
DEFAULT_CACHE_DIR = REPO_ROOT / "data" / "education" / "lesson-logger" / "compare_db"
APPS_THAT_AUTO_STOP = {DASHBOARD_APP}

### Output
def _verdict_label(same):
    """Visual same/differ marker for terminal output."""
    return "✅ SAME" if same else "❌ DIFFER"

### Fly machine helpers
def _fly_machines(app_name):
    """Return fly machines list JSON for an app."""
    result = subprocess.run(
        ["fly", "machines", "list", "-a", app_name, "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)
def _ensure_app_started(app_name, wait_seconds=60):
    """Start stopped Fly machines so fly ssh sftp can connect."""
    machines = _fly_machines(app_name)
    if not machines:
        raise SystemExit(f"{app_name}: no Fly machines found")
    stopped = [m for m in machines if m.get("state") == "stopped"]
    if not stopped:
        return
    print(f"Starting {len(stopped)} stopped machine(s) for {app_name}...", flush=True)
    for machine in stopped:
        subprocess.run(
            ["fly", "machine", "start", machine["id"], "-a", app_name],
            check=True,
        )
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        machines = _fly_machines(app_name)
        if all(m.get("state") == "started" for m in machines):
            print(f"  {app_name} ready", flush=True)
            return
        time.sleep(2)
    raise SystemExit(f"Timed out waiting for {app_name} machines to start")

### Download
def _download_remote_db(remote_path, local_path, app_name):
    """Pull a remote SQLite file from a Fly app volume via fly ssh sftp."""
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    if local_path.exists():
        local_path.unlink()
    if app_name in APPS_THAT_AUTO_STOP:
        _ensure_app_started(app_name)
    print(f"Downloading {remote_path} from {app_name}...", flush=True)
    result = subprocess.run(
        ["fly", "ssh", "sftp", "get", remote_path, str(local_path), "-a", app_name],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        combined = (result.stdout or "") + (result.stderr or "")
        if "no started VMs" in combined and app_name not in APPS_THAT_AUTO_STOP:
            _ensure_app_started(app_name)
            result = subprocess.run(
                ["fly", "ssh", "sftp", "get", remote_path, str(local_path), "-a", app_name],
                capture_output=True,
                text=True,
            )
        if result.returncode != 0:
            if result.stdout:
                print(result.stdout, file=sys.stderr, end="")
            if result.stderr:
                print(result.stderr, file=sys.stderr, end="")
            raise SystemExit(f"fly ssh sftp get failed for {app_name} ({result.returncode})")
    size = local_path.stat().st_size
    print(f"  -> {local_path} ({size:,} bytes)", flush=True)
    return local_path
def download_dbs(cache_dir=None):
    """Download Hermes and dashboard lesson DBs into cache_dir."""
    cache_dir = Path(cache_dir or DEFAULT_CACHE_DIR)
    hermes_path = cache_dir / "lessons_hermes.db"
    dashboard_path = cache_dir / "lessons_dashboard.db"
    _download_remote_db(HERMES_REMOTE_DB, hermes_path, HERMES_APP)
    _download_remote_db(DASHBOARD_REMOTE_DB, dashboard_path, DASHBOARD_APP)
    return hermes_path, dashboard_path

### DB reads
def _format_students(students_json):
    """Turn the JSON students column into a display string."""
    if not students_json:
        return "(none)"
    try:
        students = json.loads(students_json)
    except (TypeError, ValueError):
        return str(students_json)
    if not students:
        return "(none)"
    if isinstance(students, list):
        return ", ".join(str(s) for s in students)
    return str(students)
def _load_entries(db_path):
    """Return dict id -> row dict for all entries in a lessons DB."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'entries'"
        ).fetchone()
        if not row:
            raise SystemExit(f"{db_path}: no entries table")
        rows = conn.execute(
            "SELECT id, date, students, duration, subject FROM entries ORDER BY date, id"
        ).fetchall()
    finally:
        conn.close()
    return {row["id"]: dict(row) for row in rows}
def _entry_line(entry):
    """One-line display for an entry row."""
    students = _format_students(entry.get("students"))
    duration = entry.get("duration")
    duration_text = f"{duration} min" if duration is not None else "?"
    subject = entry.get("subject") or "(none)"
    date = entry.get("date") or "?"
    return f"{date:12}  {students:20}  {duration_text:8}  {subject}"

### Compare + print
def _compare(hermes_entries, dashboard_entries):
    """Return comparison facts used by short and long output.

    Catches three kinds of mismatch: entries only on one side, and entries
    present on both sides whose compared fields differ (so identical id sets
    with edited rows are not reported as SAME).
    """
    hermes_ids = set(hermes_entries)
    dashboard_ids = set(dashboard_entries)
    only_hermes = sorted(hermes_ids - dashboard_ids)
    only_dashboard = sorted(dashboard_ids - hermes_ids)
    differing = sorted(
        entry_id
        for entry_id in (hermes_ids & dashboard_ids)
        if hermes_entries[entry_id] != dashboard_entries[entry_id]
    )
    same = not only_hermes and not only_dashboard and not differing
    return {
        "same": same,
        "hermes_count": len(hermes_entries),
        "dashboard_count": len(dashboard_entries),
        "only_hermes": only_hermes,
        "only_dashboard": only_dashboard,
        "differing": differing,
    }
def _print_entries(title, entry_ids, entries_by_id):
    """Print a block of entry lines under a heading."""
    if not entry_ids:
        return
    print(title)
    print(f"{'date':12}  {'student(s)':20}  {'duration':8}  subject")
    print("-" * 60)
    for entry_id in entry_ids:
        print(_entry_line(entries_by_id[entry_id]))
    print()
def _print_differing(differing_ids, hermes_entries, dashboard_entries):
    """Print entries present on both sides whose compared fields differ."""
    if not differing_ids:
        return
    print(f"Differing entries ({len(differing_ids)}):")
    print(f"{'':12}{'date':12}  {'student(s)':20}  {'duration':8}  subject")
    print("-" * 60)
    for entry_id in differing_ids:
        print(f"  hermes:    {_entry_line(hermes_entries[entry_id])}")
        print(f"  dashboard: {_entry_line(dashboard_entries[entry_id])}")
    print()
def _print_summary(result):
    """Short summary block — printed last in long mode."""
    print("=== Summary ===")
    if result["same"]:
        print(f"{_verdict_label(True)} — {result['hermes_count']} entries on Hermes and dashboard")
    else:
        print(f"{_verdict_label(False)} — Hermes and dashboard differ")
        print(f"Hermes entries:    {result['hermes_count']}")
        print(f"Dashboard entries: {result['dashboard_count']}")
        if result["only_hermes"]:
            print(f"Extra on Hermes ({len(result['only_hermes'])}):")
            for entry_id in result["only_hermes"]:
                print(f"  {entry_id}")
        if result["only_dashboard"]:
            print(f"Extra on dashboard ({len(result['only_dashboard'])}):")
            for entry_id in result["only_dashboard"]:
                print(f"  {entry_id}")
        if result["differing"]:
            print(f"Differing entries ({len(result['differing'])}):")
            for entry_id in result["differing"]:
                print(f"  {entry_id}")
def run_compare(hermes_path, dashboard_path, long_mode=False):
    """Compare two local DB files and print short or long output."""
    hermes_entries = _load_entries(hermes_path)
    dashboard_entries = _load_entries(dashboard_path)
    result = _compare(hermes_entries, dashboard_entries)
    if long_mode:
        hermes_ids = sorted(hermes_entries)
        dashboard_ids = sorted(dashboard_entries)
        _print_entries(f"Hermes entries ({len(hermes_ids)}):", hermes_ids, hermes_entries)
        _print_entries(f"Dashboard entries ({len(dashboard_ids)}):", dashboard_ids, dashboard_entries)
        _print_summary(result)
        return
    if result["same"]:
        print(f"{_verdict_label(True)} — {result['hermes_count']} entries on Hermes and dashboard")
        return
    print(f"{_verdict_label(False)} — Hermes and dashboard differ")
    print(f"Hermes entries:    {result['hermes_count']}")
    print(f"Dashboard entries: {result['dashboard_count']}")
    if result["only_hermes"]:
        _print_entries(
            f"Extra on Hermes ({len(result['only_hermes'])}):",
            result["only_hermes"],
            hermes_entries,
        )
    if result["only_dashboard"]:
        _print_entries(
            f"Extra on dashboard ({len(result['only_dashboard'])}):",
            result["only_dashboard"],
            dashboard_entries,
        )
    _print_differing(result["differing"], hermes_entries, dashboard_entries)

### CLI
def main():
    parser = argparse.ArgumentParser(
        description="Download Hermes and dashboard lesson DBs from Fly and compare entries."
    )
    parser.add_argument(
        "--long",
        action="store_true",
        help="Print all entries from both DBs, then the summary at the end.",
    )
    parser.add_argument(
        "--cache-dir",
        default=str(DEFAULT_CACHE_DIR),
        help=f"Local directory for downloaded DB files (default: {DEFAULT_CACHE_DIR})",
    )
    parser.add_argument(
        "--hermes-db",
        help="Skip Hermes download; compare this local Hermes DB file instead.",
    )
    parser.add_argument(
        "--dashboard-db",
        help="Skip dashboard download; compare this local dashboard DB file instead.",
    )
    args = parser.parse_args()
    if args.hermes_db and args.dashboard_db:
        hermes_path = Path(args.hermes_db)
        dashboard_path = Path(args.dashboard_db)
    elif args.hermes_db or args.dashboard_db:
        parser.error("--hermes-db and --dashboard-db must be given together to skip download")
    else:
        hermes_path, dashboard_path = download_dbs(args.cache_dir)
    if not hermes_path.is_file():
        raise SystemExit(f"Hermes DB not found: {hermes_path}")
    if not dashboard_path.is_file():
        raise SystemExit(f"Dashboard DB not found: {dashboard_path}")
    run_compare(hermes_path, dashboard_path, long_mode=args.long)
if __name__ == "__main__":
    main()
