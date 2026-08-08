file: AGENTS.md
title: apps/education/lesson-logger/dashboard — Agent Instructions
last-updated: 2026-07-29_1646

**Lesson logger dashboard — per-area agent instructions.**

This is an override/supplement for work under `apps/education/lesson-logger/dashboard/`.
The **root `AGENTS.md` still fully applies** (git safety, Python style, never commit secrets).
The rules below are dashboard-specific and take precedence on conflicts within this folder.

## Branch context

- **This work lives on:** `feature/lesson-logger-dashboard`
- **Merges from:** `main` — the extraction/schema/DB/eval work was merged to main via PR #12
  (branch `feature/lesson-logger-structured-output` is deleted)
- **Hard boundary:** all dashboard code stays in this `dashboard/` folder


## Read for context (in this order)

1. `../references/lesson-schema.md` — read-only contract for lesson entry fields and DB shape
2. `../README.md` — app overview, scripts, and how extraction/save works today
3. `../scripts/lessons_db.py` — read-only reference for SQLite table layout (do not edit from here)


## What this folder owns

- Dashboard UI (HTML/JS/CSS or chosen stack)
- Local dev server / static hosting setup
- Deployment config for the dashboard (not the Hermes/Fly extraction pipeline)
- Fixture/mock DB loader for development (`../data/` mount — gitignored)
- Dashboard-specific docs and runbooks


## What this folder does NOT own

- `../scripts/` — extraction, save, DB implementation (on `main`)
- `../references/lesson-schema.md` — schema changes go through a separate branch off `main`
- `../eval/` — extraction eval
- `skills/education/lesson-logger/` — agent skill procedure


## Conventions

- Treat `../references/lesson-schema.md` as a **read-only API contract**. If the dashboard needs
  a schema change, document the requirement in a separate branch off `main`.
- Use a **fixture SQLite file** under the lesson-logger data mount for local development —
  never commit real lesson data or PII. Default local path: `../data/lessons_dev.db`
  (generate via `../scripts/generate_synthetic_data.py --out-dir ../data` when needed).
  That folder is `apps/education/lesson-logger/data` → `_LOCAL_FILES` (see
  `scripts/local_files_mounts.txt`).
- When `main` updates schema or DB layout, merge `origin/main` into this branch and update
  fixtures/adapters here — not extraction code.
- Prefer matching TL's **academic-logger v2** UX where practical
  (`tl-user.github.io/academic-logger`).


## Family schedule tab

The dashboard also serves a read-only **Family Schedule** view (`/schedule`) — rendered
markdown for this week, next week, and the horizon. Authoritative weekly markdown lives
on the Hermes volume in durable Monday-dated files written by the `schedule-coordinator`
skill; `current-week.md` and `next-week.md` are read-only aliases/caches at serving and sync
boundaries. The dashboard uses the same private-network pull pattern as the lessons DB:

- Hermes serves the files from `agents/hermes/lesson_db_server.py` at
  `/family-schedule/current-week.md`, `/family-schedule/next-week.md`, and
  `/family-schedule/horizon.md`.
- The dashboard pulls them via `sync_schedule.py` on startup and on `/internal/sync`,
  caching to `SCHEDULE_DIR` (`/data/schedule` on Fly).
- Committed sample files live in `schedule_dev/` (the `SCHEDULE_DIR` default for local runs
  and tests). Live/local runtime pulls go under the lesson-logger data mount (`../data/`:
  `schedule_live/`, `lessons_from_hermes.db`, `lessons_dev.db`, `dashboard_state.sqlite`).
- Local live review (no Fly dashboard deploy): `./sync_schedule_from_hermes.sh` pulls the
  Hermes volume files via `fly ssh sftp` into `../data/schedule_live/`. Prefer
  `./run_local.sh --live-schedule` (or `--live` for lessons DB + schedule). Do not split
  Family Schedule into a second local server — same dashboard serves `/schedule`.

Cross-app note: changing the `/family-schedule/*` route names requires updating the Hermes
server, runtime dashboard sync, and `sync_schedule_from_hermes.sh` manual pull together.


## Tests

One-time setup (this folder has its own `.venv`, separate from any repo-root venv):
```bash
cd apps/education/lesson-logger/dashboard
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
```

Run:
```bash
cd apps/education/lesson-logger/dashboard
.venv/bin/pytest test_schedule.py -v --rootdir=.
# Full dashboard regression suite when data/lessons_dev.db fixture is initialized:
.venv/bin/pytest test_dashboard.py test_schedule.py -v --rootdir=.
# Canonical routing, Hermes server, contract, rollover, and notify (from repo root):
cd ../../../..
.venv/bin/python3 -m pytest tests/test_schedule_files.py tests/test_rollover_week.py tests/test_weekly_rollover.py tests/test_schedule_skill_contract.py agents/hermes/test_lesson_db_server.py tests/test_notify_dashboard.py -v --rootdir=tests
```

`test_dashboard.py` (44 tests): date range helpers (week/month/learning year), aggregation
functions (summary cards, subject breakdown, consistency, curricula), DB queries against the
dev DB, Basic Auth (401/200), and end-to-end HTTP requests verifying rendered HTML for each
time mode, filters, student switching, empty ranges, and preferences save.

`test_schedule.py`: markdown rendering, strict Pacific current-day styling, three-card order
and responsive layout, schedule sync from Hermes (writes all three files; keeps cached
weekly copies on 404), and the `/schedule` route (auth + rendered dev files).

`agents/hermes/test_lesson_db_server.py`: current/next route and Monday-dated filename
resolution, including a year boundary.

`tests/test_notify_dashboard.py` (4 tests): the schedule→dashboard notify script — no-op
without a sync URL, POSTs with Basic Auth, lesson-env fallback, and swallows errors.

`tests/test_weekly_rollover.py`: Pacific boundary/DST guard, bootstrap preview/apply digest,
locked destination-first retry behavior, catch-up/idempotency, Horizon preservation, and
the Hermes runtime scheduler/wrapper contract.


## Merge hygiene

Periodically bring `main` into this branch:

```bash
git fetch origin
git merge origin/main
```

Use merge, not rebase, on shared/pushed branches.
