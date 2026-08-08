file: apps/education/lesson-logger/dashboard/2026-06-09_dashboard-build-v1-kickoff.md
title: Dashboard Build v1 Kickoff
last-updated: 2026-06-09_1500

Build instructions for the lesson-logger dashboard v1 prototype.

## What to build

Read the design spec first — it has everything:
`apps/education/lesson-logger/dashboard/2026-06-08_starter-dashboard-design-spec.md`

Stack (decided in the spec): FastAPI + Jinja templates + HTMX + Tailwind/DaisyUI + Chart.js.
Read from the existing SQLite DB. Basic Auth with two users (credentials from env vars, not
hardcoded). Dashboard-owned preferences in a separate SQLite file.


## Synthetic dev database

A ready-to-use dev database with 194 realistic entries is already committed at:
`apps/education/lesson-logger/lessons_dev.db`

It has two students (Fran: ~153 entries, daily learner; Zap: ~41 entries, weekly + co-op),
teachers (TL, Randy, self, Ms. Rivera), all 8 subjects with curricula, ~4 months of
data. Use this as the data source for local development — point the dashboard at it.

The DB schema is a single `entries` table — see `apps/education/lesson-logger/scripts/lessons_db.py`
for the column layout. List fields (`students`, `teachers`) are JSON arrays; query with
`json_each()`. The field contract is in `apps/education/lesson-logger/references/lesson-schema.md`.


## Dashboard code location

All dashboard code goes in `apps/education/lesson-logger/dashboard/`. Read the dashboard
AGENTS.md at `apps/education/lesson-logger/dashboard/AGENTS.md` for conventions and
ownership boundaries.


## Local dev

The dashboard must be runnable locally in a browser. Provide a simple `python3 ...` or
script command that starts the FastAPI dev server pointing at `lessons_dev.db`. Keep
dependencies minimal — FastAPI, uvicorn, Jinja2, and whatever Tailwind/DaisyUI needs.
Add a `requirements.txt` in the dashboard folder.


## What NOT to do

- Don't modify anything in `apps/education/lesson-logger/scripts/` — that's the extraction
  pipeline and is read-only from the dashboard's perspective.
- Don't add fake mastery, sentiment, or AI-generated insights — the spec explicitly excludes
  these.
- Don't deploy to Fly.io yet — local only for now.
- Don't over-engineer auth — Basic Auth with env vars is fine for v1.


## Acceptance criteria

The spec's Section 13 has the full list. The short version: load the dev DB, show a
student-level weekly view with summary cards, subject time chart, daily consistency,
curricula breakdown, and recent lessons list. Support Week/Month/School Year toggle.
Secondary filters in a drawer. Mobile-friendly.

Build it, commit your work, and push. Then tell me exactly how to run it locally.
