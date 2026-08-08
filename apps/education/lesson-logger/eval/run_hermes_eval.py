#!/usr/bin/env python3
# Run the lesson-logger extraction eval THROUGH the Hermes agent: for each
# transcript in extraction-test-cases.md, ask Hermes (default Sonnet 4.6) to
# extract the lesson fields as JSON, then score against the ground truth.
#
# Programmatic access to Hermes is via agents/hermes/tools/hermes_client.py
# (OpenAI-compatible API, or `hermes -z` on the machine). See that dir's README
# for the one-time enable + `fly proxy` steps.
#
# Usage (where the Hermes API is reachable, e.g. laptop with `fly proxy` up):
#   export HERMES_API_KEY=...                 # the API_SERVER_KEY set on the machine
#   python3 run_extraction_eval.py                                  # HTTP, Sonnet 4.6
#   python3 run_extraction_eval.py --cli                           # on the machine, via hermes -z
#   python3 run_extraction_eval.py --model anthropic/claude-sonnet-4.6 --limit 3
import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo("America/Los_Angeles")
SUBJECTS = ["Math", "Reading", "Writing", "Art", "Science", "Music"]
_HERE = os.path.dirname(os.path.abspath(__file__))
CASES_MD = os.path.join(_HERE, "extraction-test-cases.md")
def _tools_dir():
    d = _HERE
    while d != os.path.dirname(d):
        cand = os.path.join(d, "agents", "hermes", "tools")
        if os.path.isdir(cand):
            return cand
        d = os.path.dirname(d)
    raise RuntimeError("could not locate agents/hermes/tools")
sys.path.insert(0, _tools_dir())
import hermes_client

### Prompt
EXTRACT_INSTRUCTIONS = (
    "You extract a single homeschool lesson record from a short message and output ONLY a "
    "JSON object — no prose, no confirmation, no saving.\n"
    "Keys: students (list of names), subject, duration (integer minutes), date, notes.\n"
    "Rules:\n"
    f"- subject: map to one of {SUBJECTS} when it clearly fits; otherwise keep the stated "
    'subject (e.g. "History").\n'
    '- students: list the kids named. If none are named, use ["Kid1"].\n'
    '- duration: integer minutes; normalize spoken forms ("half an hour"->30, "an hour and a '
    'half"->90, "a quarter of an hour"->15). No cap.\n'
    '- date: "today" unless a day is stated; "yesterday" for yesterday; else YYYY-MM-DD.\n'
    '- notes: the descriptive detail, lightly cleaned; "" if none.\n'
    'Example: {"students":["Kid1"],"subject":"Math","duration":30,"date":"today","notes":"fractions"}'
)
def build_prompt(transcript):
    return EXTRACT_INSTRUCTIONS + "\n\nMessage: " + transcript.strip()

### Parse the fixture
def parse_cases(md_text):
    cases = []
    for block in re.split(r"(?m)^###\s+Case\b", md_text)[1:]:
        tm = re.search(r"\*\*Transcript:\*\*\s*(.+)", block)
        jm = re.search(r"```json\s*(\{.*?\})\s*```", block, re.S)
        if not tm or not jm:
            continue
        cases.append({"transcript": tm.group(1).strip().strip('"'), "expected": json.loads(jm.group(1))})
    return cases

### Parse the model's reply
def parse_reply_json(text):
    t = (text or "").strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", t, re.S)
    if fenced:
        t = fenced.group(1)
    else:
        i, j = t.find("{"), t.rfind("}")
        if i != -1 and j > i:
            t = t[i:j + 1]
    return json.loads(t)

### Score
def _resolve_date(value, run_date):
    s = str(value or "").strip().lower()
    if s in ("", "today"):
        return run_date
    if s == "yesterday":
        return run_date - timedelta(days=1)
    return date.fromisoformat(s)
def score_case(expected, got, run_date):
    res = {"errors": []}
    exp_students = {str(s).strip().lower() for s in expected.get("students", [])}
    got_students = {str(s).strip().lower() for s in (got.get("students") or [])}
    res["students"] = exp_students == got_students
    res["subject"] = str(expected.get("subject", "")).strip().lower() == str(got.get("subject", "")).strip().lower()
    try:
        res["duration"] = int(expected.get("duration")) == int(got.get("duration"))
    except (TypeError, ValueError):
        res["duration"] = False
    try:
        res["date"] = _resolve_date(expected.get("date"), run_date) == _resolve_date(got.get("date"), run_date)
    except ValueError:
        res["date"] = False
    res["passed"] = all(res[k] for k in ("students", "subject", "duration", "date"))
    return res

### Run + report
def run_eval(cases, asker, run_date=None, limit=None):
    run_date = run_date or datetime.now(PACIFIC).date()
    results = []
    for i, c in enumerate(cases[:limit or len(cases)], 1):
        try:
            got = parse_reply_json(asker(build_prompt(c["transcript"])))
            score = score_case(c["expected"], got, run_date)
        except Exception as exc:  # noqa: BLE001 - any failure = a failed case, keep going
            got = {}
            score = {"passed": False, "errors": [str(exc)],
                     "students": False, "subject": False, "duration": False, "date": False}
        results.append({"i": i, "case": c, "got": got, "score": score})
    return results
def format_report(results):
    lines = []
    passed = 0
    fields = {"students": 0, "subject": 0, "duration": 0, "date": 0}
    for r in results:
        s = r["score"]
        passed += 1 if s["passed"] else 0
        for k in fields:
            fields[k] += 1 if s.get(k) else 0
        miss = [k for k in ("students", "subject", "duration", "date") if not s.get(k)]
        tag = "PASS" if s["passed"] else "FAIL"
        suffix = f"  (miss: {','.join(miss)})" if miss else ""
        if s.get("errors"):
            suffix = f"  [error: {s['errors'][0]}]"
        lines.append(f"  Case {r['i']}: {tag}{suffix}")
        if miss and not s.get("errors"):
            lines.append(f"     expected {json.dumps(r['case']['expected'])}")
            lines.append(f"     got      {json.dumps(r['got'])}")
    n = len(results) or 1
    lines.append("")
    lines.append(f"  Passed {passed}/{len(results)}  |  per-field: "
                 + ", ".join(f"{k} {v}/{len(results)}" for k, v in fields.items()))
    return "\n".join(lines)

### CLI
def main():
    ap = argparse.ArgumentParser(description="Lesson-logger extraction eval, through the Hermes agent.")
    ap.add_argument("--model", default=hermes_client.DEFAULT_MODEL)
    ap.add_argument("--cli", action="store_true", help="Use `hermes -z` (run on the machine).")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    cases = parse_cases(open(CASES_MD).read())
    print(f"Loaded {len(cases)} cases; model={args.model}; transport={'cli' if args.cli else 'http'}")
    if args.cli:
        asker = lambda p: hermes_client.cli_ask(p, args.model)
    else:
        client = hermes_client.HermesClient(model=args.model)
        asker = lambda p: client.ask(p)
    print(format_report(run_eval(cases, asker, limit=args.limit)))
if __name__ == "__main__":
    main()
