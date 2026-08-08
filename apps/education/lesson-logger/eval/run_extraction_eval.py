#!/usr/bin/env python3
# Run the lesson-logger extraction eval using OpenAI structured output
# (function calling). For each transcript in extraction-test-cases.md, call
# the extract_lesson script to extract fields as JSON, then score against
# ground truth.
#
# Usage:
#   export OPENAI_API_KEY=...
#   python3 run_extraction_eval.py                           # gpt-4.1-mini
#   python3 run_extraction_eval.py --model gpt-4o-mini       # different model
#   python3 run_extraction_eval.py --limit 3 --verbose
import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.join(os.path.dirname(_HERE), "scripts")
sys.path.insert(0, _SCRIPTS)
import extract_lesson

PACIFIC = ZoneInfo("America/Los_Angeles")
CASES_MD = os.path.join(_HERE, "extraction-test-cases.md")

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
    # students — case-insensitive set equality
    exp_students = {str(s).strip().lower() for s in expected.get("students", [])}
    got_students = {str(s).strip().lower() for s in (got.get("students") or [])}
    res["students"] = exp_students == got_students
    # teachers — case-insensitive set equality
    exp_teachers = {str(s).strip().lower() for s in expected.get("teachers", [])}
    got_teachers = {str(s).strip().lower() for s in (got.get("teachers") or [])}
    res["teachers"] = exp_teachers == got_teachers
    # subject — case-insensitive
    res["subject"] = str(expected.get("subject", "")).strip().lower() == str(got.get("subject", "")).strip().lower()
    # duration — integer equality
    try:
        res["duration"] = int(expected.get("duration")) == int(got.get("duration"))
    except (TypeError, ValueError):
        res["duration"] = False
    # date — resolved equality
    try:
        res["date"] = _resolve_date(expected.get("date"), run_date) == _resolve_date(got.get("date"), run_date)
    except ValueError:
        res["date"] = False
    # curricula — case-insensitive substring (ground truth is the gist)
    exp_cur = str(expected.get("curricula", "")).strip().lower()
    got_cur = str(got.get("curricula", "")).strip().lower()
    res["curricula"] = exp_cur == got_cur or (exp_cur and exp_cur in got_cur) or (not exp_cur and not got_cur)
    # location — case-insensitive substring
    exp_loc = str(expected.get("location", "")).strip().lower()
    got_loc = str(got.get("location", "")).strip().lower()
    res["location"] = exp_loc == got_loc or (exp_loc and exp_loc in got_loc) or (not exp_loc and not got_loc)
    # time — case-insensitive, normalize whitespace, strip ":00" padding, bare-number match
    def _norm_time(t):
        s = str(t or "").strip().lower().replace(" ", "")
        s = re.sub(r":00(?=[ap]m|$)", "", s)
        return s
    exp_time = _norm_time(expected.get("time", ""))
    got_time = _norm_time(got.get("time", ""))
    if not exp_time and not got_time:
        res["time"] = True
    elif exp_time and got_time:
        bare_exp = re.sub(r"[ap]m$", "", exp_time)
        bare_got = re.sub(r"[ap]m$", "", got_time)
        res["time"] = exp_time == got_time or bare_exp == bare_got or exp_time in got_time or got_time in exp_time
    else:
        res["time"] = False
    # core pass: students + subject + duration + date (same as Hermes eval)
    res["core_passed"] = all(res[k] for k in ("students", "subject", "duration", "date"))
    # full pass: core + teachers + curricula + location + time
    res["passed"] = res["core_passed"] and all(res[k] for k in ("teachers", "curricula", "location", "time"))
    return res

SCORED_FIELDS = ["students", "teachers", "subject", "curricula", "duration", "location", "date", "time"]

### Run + report
def run_eval(cases, model, run_date=None, limit=None, verbose=False):
    run_date = run_date or datetime.now(PACIFIC).date()
    results = []
    for i, c in enumerate(cases[:limit or len(cases)], 1):
        try:
            got = extract_lesson.extract_lesson(c["transcript"], model=model, verbose=verbose)
            score = score_case(c["expected"], got, run_date)
        except Exception as exc:
            got = {}
            score = {"passed": False, "core_passed": False, "errors": [str(exc)]}
            for k in SCORED_FIELDS:
                score[k] = False
        results.append({"i": i, "case": c, "got": got, "score": score})
    return results
def format_report(results):
    lines = []
    passed = core_passed = 0
    fields = {k: 0 for k in SCORED_FIELDS}
    for r in results:
        s = r["score"]
        passed += 1 if s["passed"] else 0
        core_passed += 1 if s.get("core_passed") else 0
        for k in fields:
            fields[k] += 1 if s.get(k) else 0
        miss = [k for k in SCORED_FIELDS if not s.get(k)]
        tag = "PASS" if s["passed"] else ("CORE" if s.get("core_passed") else "FAIL")
        suffix = f"  (miss: {','.join(miss)})" if miss else ""
        if s.get("errors"):
            suffix = f"  [error: {s['errors'][0]}]"
        lines.append(f"  Case {r['i']}: {tag}{suffix}")
        if miss and not s.get("errors"):
            lines.append(f"     expected {json.dumps(r['case']['expected'])}")
            lines.append(f"     got      {json.dumps(r['got'])}")
    n = len(results) or 1
    lines.append("")
    lines.append(f"  Full pass {passed}/{len(results)}  |  Core pass (students+subject+duration+date) {core_passed}/{len(results)}")
    lines.append("  Per-field: " + ", ".join(f"{k} {v}/{len(results)}" for k, v in fields.items()))
    return "\n".join(lines)

### CLI
def main():
    ap = argparse.ArgumentParser(description="Lesson-logger extraction eval via OpenAI structured output.")
    ap.add_argument("--model", default=extract_lesson.DEFAULT_MODEL, help=f"OpenAI model (default: {extract_lesson.DEFAULT_MODEL}).")
    ap.add_argument("--limit", type=int, default=None, help="Run only the first N cases.")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()
    cases = parse_cases(open(CASES_MD).read())
    print(f"Loaded {len(cases)} cases; model={args.model}; method=structured-output")
    print(format_report(run_eval(cases, model=args.model, limit=args.limit, verbose=args.verbose)))
if __name__ == "__main__":
    main()
