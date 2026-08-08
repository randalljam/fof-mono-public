file: apps/education/lesson-logger/README.md
title: Lesson logger — homeschool lesson capture app

**Capture homeschool lessons from natural-language voice/text input.**

Extracts structured fields from a short transcript (typically voice-dictated), validates,
and saves as a JSON session file + SQLite DB row. Designed for TL logging lessons for
Kid1, with entry primarily through the Hermes agent on Telegram.

The companion skill at `skills/education/lesson-logger/` defines the agent procedure
(extract → confirm → save). This app contains the implementation that the skill references.


## Entry point
```bash
python3 apps/education/lesson-logger/log_lesson.py \
  --transcript "Kid1 did 30 min of math" --sender TL
```
End-to-end: extracts fields via OpenAI structured output, validates, saves JSON file + DB row.
Requires `OPENAI_API_KEY` env var.


## Scripts
| File | Purpose |
|------|---------|
| `log_lesson.py` | End-to-end entry point: extract + validate + save |
| `scripts/extract_lesson.py` | OpenAI function-calling extraction (standalone) |
| `scripts/save_lesson.py` | Validate + save a confirmed lesson (JSON file + DB upsert) |
| `scripts/lessons_db.py` | SQLite store: `ingest` (backfill from files), `summary` (rollup) |
| `scripts/compare_db.py` | Download Hermes + dashboard `lessons.db` from Fly and diff entries (`--long` for full listing) |


## References
- `references/lesson-schema.md` — full field rules, JSON shape, storage layers
- `references/extractor-versions.md` — extractor version history (human+machine readable)


## Eval
- `eval/extraction-test-cases.md` — 16 hand-written transcript → ground-truth pairs
- `eval/run_extraction_eval.py` — run extraction via OpenAI structured output and score against ground truth
- `eval/run_hermes_eval.py` — run extraction through the Hermes agent and score (requires Hermes API)

Run the eval:
```bash
export OPENAI_API_KEY=...
python3 apps/education/lesson-logger/eval/run_extraction_eval.py
python3 apps/education/lesson-logger/eval/run_extraction_eval.py --model gpt-4o-mini
```
