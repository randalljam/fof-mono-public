file: apps/education/lesson-logger/dashboard/README.md
title: Lesson logger dashboard

**Dashboard UI and deployment for viewing homeschool lesson entries.**

Active development on branch `feature/family-schedule-dashboard`. Reads lesson data from the
SQLite DB defined in `../references/lesson-schema.md`; uses a local (gitignored) fixture at
`../data/lessons_dev.db` (lesson-logger data mount) for development.

See `AGENTS.md` in this folder for agent instructions.


## Quick start
This app has its **own** `.venv` inside this folder — separate from any repo-root `.venv`.
Always run it with this folder's venv (`.venv/bin/...`), not a venv activated elsewhere; a
plain `uvicorn` or `.venv/bin/uvicorn` from the wrong directory is what causes
`.venv/bin/uvicorn: No such file or directory`.

**Easiest — one command (creates the venv on first run, then starts the server):**
```bash
apps/education/lesson-logger/dashboard/run_local.sh
```

**With live Hermes schedule files** (needs `flyctl` logged in; pulls into `../data/schedule_live/`):
```bash
apps/education/lesson-logger/dashboard/run_local.sh --live-schedule
# or both lessons DB + schedule:
apps/education/lesson-logger/dashboard/run_local.sh --live
```

**Manual equivalent:**
```bash
cd apps/education/lesson-logger/dashboard

# First time only: create THIS folder's venv and install deps
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Optional: pull live schedule (or use --live-schedule on run_local.sh)
./sync_schedule_from_hermes.sh ../data/schedule_live
SCHEDULE_DIR=../data/schedule_live .venv/bin/uvicorn app:app --reload --port 8000
```
Open http://localhost:8000 and log in with Basic Auth (default dev creds: `randy`/`randy`
or `tl`/`tl`). Click **Family Schedule** in the header (or open `/schedule`). Stop the
server with Ctrl+C. Default local mode uses committed samples in `schedule_dev/` — it
does **not** reach Hermes over Fly private networking.


## Configuration (env vars)
| Variable | Default | Description |
|----------|---------|-------------|
| `LESSONS_DB` | `../data/lessons_dev.db` | Path to the lessons SQLite database |
| `PREFS_DB` | `../data/dashboard_state.sqlite` | Path to the preferences database |
| `SCHEDULE_DIR` | `./schedule_dev` | Directory holding family-schedule markdown (committed samples by default; live pulls use `../data/schedule_live`) |
| `DASH_USER1` | `randy` | First user's username |
| `DASH_PASS1` | `randy` | First user's password |
| `DASH_USER2` | `tl` | Second user's username |
| `DASH_PASS2` | `tl` | Second user's password |
| `DASH_DEV_PASSWORDS` | *(none)* | When true, also allows dev logins `randy`/`randy` and `tl`/`tl` |
| `HERMES_LESSON_DB_URL` | `http://[FLY-APP-NAME].internal:8081/lesson-logger/lessons.db` | Private Fly URL for pulling a DB snapshot from Hermes |
| `HERMES_SCHEDULE_BASE_URL` | `http://[FLY-APP-NAME].internal:8081/family-schedule` | Private Fly base URL for pulling the family-schedule markdown from Hermes |


## Family Schedule tab
A read-only **Family Schedule** view lives at `/schedule` (linked from the dashboard
header; the page links back to the lesson logger). It renders cards in order **This Week,
Next Week, Horizon**. On desktop they form three columns; on mobile they stack in that
order.

Hermes stores authoritative weekly data only in durable Monday-dated
`YYYY-MM-DD_week_family-schedule.md` files. The internal server resolves the current and
following Mondays and exposes read-only `/family-schedule/current-week.md` and
`/family-schedule/next-week.md` aliases, plus `/family-schedule/horizon.md`. The dashboard
pulls all three via `sync_schedule.py` on startup and whenever Hermes calls
`/internal/sync` after a schedule edit. Local `current-week.md` and `next-week.md` files
are caches, not authoring targets. A missing remote week alias leaves any existing cached
copy in place; without a cache, the UI shows a safe missing-file message.

Local dev defaults to the three committed samples in `schedule_dev/`. To review live
Hermes files without deploying the Fly dashboard, use `./sync_schedule_from_hermes.sh`
(or `run_local.sh --live-schedule`) — that pulls the two authoritative dated week files
and Horizon via `fly ssh sftp` into `../data/schedule_live/` (lesson-logger data mount).


## Deploy to Fly.io
See `2026-06-09_fly-deploy-checklist.md` for the full deployment walkthrough.
Build plan: `/.cursor/plans/2026-06-09_direct_lesson_sync_37b245ef.plan.md`.

**Quick version:**
```bash
cd apps/education/lesson-logger/dashboard
fly apps create fof-lesson-dash --org personal
fly volumes create dashboard_data -a fof-lesson-dash -r sjc -s 1 -y
fly secrets set -a fof-lesson-dash DASH_USER1=... DASH_PASS1=... DASH_USER2=... DASH_PASS2=...
fly deploy -a fof-lesson-dash
```

Dashboard Basic Auth values may also live in the repo-root `.env` (gitignored) for
scripts/future automation. Fly uses them as secrets; never commit or paste the actual
password values into docs.


## Stack
FastAPI + Jinja2 templates + Tailwind CSS / DaisyUI + Chart.js.
User preferences stored in `../data/dashboard_state.sqlite` on the lesson-logger data mount
(auto-created). Live Hermes pulls for local review land under `../data/` as well
(`schedule_live/`, `lessons_from_hermes.db`). On Fly, the dashboard syncs `lessons.db` from Hermes over
Fly private networking on startup and when Hermes calls the authenticated `/internal/sync`
endpoint after a lesson DB write (see `sync_db.py`). Hermes serves a WAL-safe SQLite
snapshot on an internal-only endpoint; no AWS runtime credentials are required.
