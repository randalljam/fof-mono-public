#!/usr/bin/env python3
# Persist a confirmed homeschool lesson as an intermediate, human-readable JSON
# "session file", AND upsert it into the queryable SQLite store (write-through).
#
# Extraction + the confirmation loop are the AGENT's job (see SKILL.md). This
# script only validates + writes, so persisted records are always well-formed.
# Stdlib only for core save.
#
# Input: a JSON object on stdin or via --in <file>, e.g.
#   {"students": ["Kid1"], "subject": "Math", "duration": 30, "notes": "fractions"}
# Output: <log dir>/<date>_<subject>_<id8>.json  +  a row in <log dir>/lessons.db
#   log dir = $HERMES_LESSON_LOG_DIR, else $HERMES_HOME/lesson-logs, else ~/.hermes/lesson-logs
import argparse
import base64
import json
import os
import re
import sys
import urllib.request
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_lesson import EXTRACTOR_VERSION
import lessons_db

### Config
PACIFIC = ZoneInfo("America/Los_Angeles")
KNOWN_SUBJECTS = ["Math", "Reading", "Writing", "Art", "Science", "Music"]
DEFAULT_STUDENT = "Kid1"
DURATION_MIN = 1
DURATION_MAX = 1440

### Helpers
def _log_dir():
    """Resolve the lesson-logs output directory (agent volume, not the repo)."""
    env = os.environ.get("HERMES_LESSON_LOG_DIR")
    if env:
        return env
    home = os.environ.get("HERMES_HOME") or os.path.join(os.path.expanduser("~"), ".hermes")
    return os.path.join(home, "lesson-logs")
def _today_iso(now):
    return now.astimezone(PACIFIC).strftime("%Y-%m-%d")
def _norm_subject(value):
    """Canonicalize to one of KNOWN_SUBJECTS (case-insensitive); else keep as given."""
    s = str(value or "").strip()
    for known in KNOWN_SUBJECTS:
        if s.lower() == known.lower():
            return known, True
    return s, False
def _norm_name_list(value, default=None):
    """Normalize to a deduped list of names.

    When default is None, returns ([], False) for empty input. Otherwise returns
    (default, True) when nothing usable remains.
    """
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple)):
        items = list(value)
    elif value in (None, ""):
        items = []
    else:
        items = [str(value)]
    cleaned = []
    for s in items:
        s = str(s).strip()
        if s and s not in cleaned:
            cleaned.append(s)
    if not cleaned:
        if default is None:
            return [], False
        return list(default), True
    return cleaned, False
def _norm_students(value):
    """Normalize students; default to [Kid1] when none given."""
    return _norm_name_list(value, default=[DEFAULT_STUDENT])
def _norm_teachers(value, created_by=None):
    """Normalize teachers; resolve "not specified" to [created_by] when sender is known."""
    names, _ = _norm_name_list(value, default=None)
    is_unspecified = names == ["not specified"] or not names
    if is_unspecified and created_by:
        return [created_by], True
    if is_unspecified:
        return ["not specified"], True
    return names, False
def _norm_duration(value):
    """Coerce minutes to a positive integer (no rounding-to-5, no 60 cap)."""
    return int(round(float(value)))
def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-") or "lesson"

### Core
def build_entry(data, now=None):
    """Validate/normalize an extracted lesson dict into a saved entry + warnings.

    Raises ValueError when a required field is missing or malformed.
    """
    now = now or datetime.now(PACIFIC)
    if not isinstance(data, dict):
        raise ValueError("input must be a JSON object")
    if not str(data.get("subject") or "").strip():
        raise ValueError("subject is required")
    if data.get("duration") in (None, ""):
        raise ValueError("duration is required")
    subject, known = _norm_subject(data["subject"])
    created_by = str(data.get("createdBy") or "")
    students, students_defaulted = _norm_students(data.get("students"))
    teachers, teachers_defaulted = _norm_teachers(data.get("teachers"), created_by=created_by)
    try:
        duration = _norm_duration(data["duration"])
    except (TypeError, ValueError):
        raise ValueError(f"duration must be a number of minutes, got {data['duration']!r}")
    warnings = []
    if duration < DURATION_MIN:
        raise ValueError(f"duration must be at least {DURATION_MIN} minute")
    if duration > DURATION_MAX:
        warnings.append(f"duration {duration} exceeds {DURATION_MAX} min; clamped (looks like an extraction error)")
        duration = DURATION_MAX
    date = str(data.get("date") or "").strip() or _today_iso(now)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise ValueError(f"date must be YYYY-MM-DD, got {date!r}")
    entry = {
        "id": str(uuid.uuid4()),
        "date": date,
        "time": str(data.get("time") or ""),
        "students": students,
        "teachers": teachers,
        "subject": subject,
        "curricula": str(data.get("curricula") or ""),
        "duration": duration,
        "location": str(data.get("location") or ""),
        "notes": str(data.get("notes") or ""),
        "transcript": str(data.get("transcript") or ""),
        "createdBy": created_by,
        "createdAt": now.isoformat(),
        "extractorVersion": EXTRACTOR_VERSION,
    }
    if data.get("photoDataUrl"):
        entry["photoDataUrl"] = data["photoDataUrl"]
    if students_defaulted:
        warnings.append(f"no student named; defaulted to {DEFAULT_STUDENT} — confirm this is right")
    if teachers_defaulted and created_by:
        warnings.append(f"teacher not specified; defaulted to sender ({created_by}) — confirm this is right")
    elif teachers_defaulted:
        warnings.append("teacher not specified and no sender context — stored as \"not specified\"")
    if not known:
        warnings.append(f"subject {subject!r} is not one of {KNOWN_SUBJECTS}; saved as a custom subject")
    return entry, warnings
def save_entry(entry, log_dir=None):
    """Write an entry dict to a JSON session file; returns the path."""
    log_dir = log_dir or _log_dir()
    os.makedirs(log_dir, exist_ok=True)
    name = f"{entry['date']}_{_slug(entry['subject'])}_{entry['id'][:8]}.json"
    path = os.path.join(log_dir, name)
    with open(path, "w") as f:
        json.dump(entry, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return path
def notify_dashboard_sync():
    """Best-effort callback so the dashboard pulls the latest Hermes DB snapshot."""
    url = os.environ.get("LESSON_DASH_SYNC_URL")
    if not url:
        return None
    req = urllib.request.Request(url, data=b"", method="POST")
    user = os.environ.get("LESSON_DASH_SYNC_USER")
    password = os.environ.get("LESSON_DASH_SYNC_PASSWORD")
    if user and password:
        token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
        req.add_header("Authorization", f"Basic {token}")
    timeout = float(os.environ.get("LESSON_DASH_SYNC_TIMEOUT", "10"))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = getattr(response, "status", response.getcode())
            if 200 <= status < 300:
                return "dashboard sync requested"
            return f"dashboard sync request failed: HTTP {status}"
    except Exception as exc:
        return f"dashboard sync request failed: {exc}"
### CLI
def _read_input(infile):
    if infile:
        with open(infile) as f:
            return f.read()
    return sys.stdin.read()
def main():
    parser = argparse.ArgumentParser(description="Save a confirmed lesson as a JSON session file + DB row.")
    parser.add_argument("--in", dest="infile", help="JSON input file (else read stdin).")
    parser.add_argument("--log-dir", help="Override output dir (default $HERMES_LESSON_LOG_DIR or ~/.hermes/lesson-logs).")
    parser.add_argument("--db", help="Override SQLite DB path (default <log dir>/lessons.db).")
    args = parser.parse_args()
    raw = _read_input(args.infile)
    if not raw.strip():
        print("No input JSON provided (stdin or --in).", file=sys.stderr)
        sys.exit(1)
    try:
        data = json.loads(raw)
    except ValueError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)
    try:
        entry, warnings = build_entry(data)
    except ValueError as exc:
        print(f"Validation error: {exc}", file=sys.stderr)
        sys.exit(1)
    path = save_entry(entry, args.log_dir)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    # Write-through to the queryable DB; never lose the file if the DB hiccups.
    db_path = args.db or lessons_db.default_db_path()
    db_note = ""
    try:
        conn = lessons_db.connect(db_path)
        lessons_db.upsert_entry(conn, entry, source_file=path)
        conn.close()
        db_note = " (also added to lessons.db)"
        sync_note = notify_dashboard_sync()
        if sync_note == "dashboard sync requested":
            db_note = " (also added to lessons.db; dashboard sync requested)"
        elif sync_note:
            print(f"warning: {sync_note}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001 - DB issues must not lose the lesson
        print(f"warning: saved file but DB upsert failed: {exc}", file=sys.stderr)
    print(f"Saved lesson -> {path}{db_note}")
    print(json.dumps(entry, indent=2, ensure_ascii=False))
if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        # Output was piped into a reader that closed early (e.g. `| head`); not an error.
        try:
            sys.stdout.close()
        except OSError:
            pass
