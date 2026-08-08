file: apps/education/lesson-logger/NEXT-STEPS.md
title: Lesson-logger — next steps
last-updated: 2026-06-08_2230

Deferred items from the `feature/lesson-logger-structured-output` branch.

### Unit tests for non-LLM code
`save_lesson.build_entry()`, `lessons_db.upsert_entry()`/`summary()`,
`log_lesson._resolve_date()`, and the eval time normalizer are all testable without an
OpenAI key. Best written alongside dashboard work when the DB queries are being exercised
for real.

### Update AGENTS.md directory guide
`apps/education/` and `apps/education/lesson-logger/` are not mentioned in the top-level
`AGENTS.md` directory guide yet. One-line addition under the `apps/` section.

### Verify skill wrapper references
`skills/education/lesson-logger/README.md` was rewritten to point at the `apps/` entry
point. Spot-check that the bash examples and field list stay in sync if the app code
changes.
