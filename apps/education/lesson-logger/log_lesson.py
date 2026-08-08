#!/usr/bin/env python3
# End-to-end lesson logging: extract fields from a transcript via OpenAI
# structured output, then validate and save as a JSON session file + DB row.
#
# This is the main entry point for the lesson-logger app — both the Hermes
# skill and the dashboard call this.
#
# Usage:
#   python3 log_lesson.py --transcript "Kid1 did 30 min of math" --sender TL
#   echo "40 min reading" | python3 log_lesson.py --sender TL
#   python3 log_lesson.py --in transcript.txt --sender Randy
#
# Env: OPENAI_API_KEY (required for extraction).
# Output: the saved entry as JSON on stdout; warnings on stderr.
import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

_SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")
sys.path.insert(0, _SCRIPTS)
import extract_lesson
import save_lesson

PACIFIC = ZoneInfo("America/Los_Angeles")

def _resolve_date(value):
    """Resolve 'today', 'yesterday', etc. to YYYY-MM-DD."""
    s = str(value or "").strip().lower()
    now = datetime.now(PACIFIC)
    if s in ("", "today"):
        return now.strftime("%Y-%m-%d")
    if s == "yesterday":
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    return value

def log_lesson(transcript, sender=None, model=None, log_dir=None, db_path=None, verbose=False):
    """Extract fields from a transcript, validate, and save. Returns (entry, warnings, path)."""
    model = model or extract_lesson.DEFAULT_MODEL
    extracted = extract_lesson.extract_lesson(transcript, model=model, verbose=verbose)
    extracted["transcript"] = transcript
    extracted["date"] = _resolve_date(extracted.get("date"))
    if sender:
        extracted["createdBy"] = sender
    entry, warnings = save_lesson.build_entry(extracted)
    path = save_lesson.save_entry(entry, log_dir=log_dir)
    import lessons_db
    try:
        conn = lessons_db.connect(db_path)
        lessons_db.upsert_entry(conn, entry, source_file=path)
        conn.close()
        sync_note = save_lesson.notify_dashboard_sync()
        if sync_note and sync_note != "dashboard sync requested":
            warnings.append(sync_note)
    except Exception as exc:
        warnings.append(f"saved file but DB upsert failed: {exc}")
    return entry, warnings, path

### CLI
def main():
    ap = argparse.ArgumentParser(description="Extract + save a lesson from a transcript (end-to-end).")
    ap.add_argument("--transcript", "-t", help="Transcript text (else read from --in or stdin).")
    ap.add_argument("--in", dest="infile", help="File containing the transcript.")
    ap.add_argument("--sender", "-s", help="Who sent the message (e.g. TL, Randy). Sets createdBy and teacher default.")
    ap.add_argument("--model", default=None, help=f"OpenAI model (default: {extract_lesson.DEFAULT_MODEL}).")
    ap.add_argument("--log-dir", help="Override lesson output dir.")
    ap.add_argument("--db", help="Override SQLite DB path.")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()
    if args.transcript:
        text = args.transcript
    elif args.infile:
        with open(args.infile) as f:
            text = f.read()
    else:
        text = sys.stdin.read()
    if not text.strip():
        print("No transcript provided.", file=sys.stderr)
        sys.exit(1)
    entry, warnings, path = log_lesson(
        text, sender=args.sender, model=args.model,
        log_dir=args.log_dir, db_path=args.db, verbose=args.verbose,
    )
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    print(f"Saved lesson -> {path}", file=sys.stderr)
    print(json.dumps(entry, indent=2, ensure_ascii=False))
if __name__ == "__main__":
    main()
