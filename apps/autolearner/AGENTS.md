file: apps/autolearner/AGENTS.md
title: autolearner — Agent Instructions

AI mastery-practice app for the PreCalc Test 1 study guide. See `README.md` for the full architecture, run instructions, and API-key/mock-mode behavior.

- `pacing.py` and `mastery.py` are pure logic — keep them free of network calls and core imports so they stay unit-testable without keys.
- `pipeline.py` lazy-imports `core/transcribe.py` and `core/llm.py` (both require env keys at import time) and must keep its labeled mock fallbacks working keyless.
- Runtime artifacts (sessions, uploads, lesson audio) live in `apps/autolearner/data/`, which the root `.gitignore` `data/` rule excludes — never commit them and never rename that directory.
- The two web pages follow the dark repo-snapshot page style; keep new UI consistent with it.


## Tests
Run from the repo root:
```bash
.venv/bin/python3 -m unittest tests.test_autolearner -v
```
Covers pacing metrics, the multi-round mastery scheduler, and the Flask API end-to-end with pipeline services patched (no network). Add cases here when changing scheduling, assessment schema fields, or API routes.
