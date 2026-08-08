#!/usr/bin/env python3
# Offline tests for the lesson-logger extraction-eval harness: fixture parsing
# and scoring (no live model call — the asker is stubbed).
import importlib.util
import json
import os
from datetime import date

_SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "agents", "hermes", "skills", "education", "lesson-logger", "eval", "run_extraction_eval.py",
)
def _load():
    spec = importlib.util.spec_from_file_location("run_extraction_eval", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
def test_parse_cases_loads_ten():
    mod = _load()
    cases = mod.parse_cases(open(mod.CASES_MD).read())
    assert len(cases) == 10, len(cases)
    assert cases[0]["expected"]["subject"] == "Math"
    assert cases[4]["expected"]["students"] == ["Kid1", "Mia"]
def test_oracle_asker_all_pass():
    mod = _load()
    cases = mod.parse_cases(open(mod.CASES_MD).read())
    run_date = date(2026, 6, 6)
    def oracle(prompt):
        for c in cases:
            if c["transcript"][:18] in prompt:
                return "```json\n" + json.dumps(c["expected"]) + "\n```"
        return "{}"
    results = mod.run_eval(cases, oracle, run_date=run_date)
    bad = [r["i"] for r in results if not r["score"]["passed"]]
    assert bad == [], bad
def test_scoring_catches_wrong_subject():
    mod = _load()
    run_date = date(2026, 6, 6)
    s = mod.score_case(
        {"students": ["Kid1"], "subject": "Math", "duration": 30, "date": "today"},
        {"students": ["Kid1"], "subject": "Reading", "duration": 30, "date": "today"},
        run_date,
    )
    assert s["subject"] is False and s["passed"] is False
    assert s["students"] and s["duration"] and s["date"]
def test_relative_date_resolves():
    mod = _load()
    run_date = date(2026, 6, 6)
    s = mod.score_case(
        {"students": ["Kid1"], "subject": "Music", "duration": 20, "date": "yesterday"},
        {"students": ["Kid1"], "subject": "Music", "duration": 20, "date": "2026-06-05"},
        run_date,
    )
    assert s["passed"], s
def test_bad_json_reply_is_a_failed_case():
    mod = _load()
    cases = mod.parse_cases(open(mod.CASES_MD).read())[:1]
    results = mod.run_eval(cases, lambda p: "sorry, I can't do that", run_date=date(2026, 6, 6))
    assert results[0]["score"]["passed"] is False
    assert results[0]["score"]["errors"]
if __name__ == "__main__":
    test_parse_cases_loads_ten()
    test_oracle_asker_all_pass()
    test_scoring_catches_wrong_subject()
    test_relative_date_resolves()
    test_bad_json_reply_is_a_failed_case()
    print("ok")
