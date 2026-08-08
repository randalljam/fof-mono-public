# Math Quiz

Browser-based math quiz application for kids, with fluency tracking and performance analysis.

## Run Commands Cheat Sheet
- Start (or restart) the anchor/dragon dev server from repo root: `.venv/bin/python3 apps/math-quiz/tools/dev_server.py` — if port 8907 is already in use, the script stops the old process and starts fresh
- Laptop URL (same machine running server): `http://127.0.0.1:8907/anchor.html`
- Dragon fluency game: `http://127.0.0.1:8907/dragon/index.html` (pick Kid1 or Randy at startup; Randy also gets continue vs clone Kid1's game)
- Dragon **Game Master** (parent dashboard, phone-friendly): `http://<your-laptop-LAN-IP>:8907/dragon/gm.html` — live progress/objectives + send in-game letters (defaults to Kid1/tlkids; `?user=&folder=` to switch)
- Phone/iPad URL (same Wi-Fi): `http://<your-laptop-LAN-IP>:8907/anchor.html`
- Quick LAN IP lookup on macOS: `ipconfig getifaddr en0 || ipconfig getifaddr en1`

## Components
- **math_quiz.html / .js / .css** — main quiz interface (configurable arithmetic practice, sound effects, confetti, speech input/output, problem flagging)
- **math_fluency.html / .js** — fluency tracking dashboard (per-fact speed/accuracy status, manual overrides, problem-list generator)
- **math_analysis.html / .js** — response-time heatmap and per-problem analysis dashboard (flag filtering, sorting, flag editing, session export)
- **math_utils.js** — shared JS utilities (symbol normalization, parsing, DB import, HTML escaping)
- **fluency_core.js** — shared fluency rubric and list generation (`fluencyPercent`, `generateFluencyProblemList`); used by anchor, analysis, fluency tracker, and the dragon game bridge
- **math_quiz.py / math_analysis.py** — legacy Python predecessors (CLI/pygame quiz, pandas analysis); not maintained — the web app is the active surface

## Fluency percent (app-wide metric)
Overall fluency is an integer **% of the full fact universe** that the learner is fluent at (green, or blue/permanent), recomputed from raw `ProblemAttempts` — not stored in SQLite. This is the same number the anchor page shows at end-of-quiz, the kid **Fluency feast** uses to classify facts, the analysis page's "Current fluency percentage" readout, the fluency-tracker cards, and the dragon game. Visual-practice sessions count like assess, problem-list, and targeted-practice sessions; flagged lightbulb-help attempts remain excluded.

- **JS function:** `fluencyPercent(attempts, thresholds, { numberRange: [0,9], operations: ['+'], excludeFlagged: true })` in `fluency_core.js`
- **CLI** (needs `npm install` once under `tests/` for sql.js):

```
cd apps/math-quiz/tests && npm install
node ../tools/fluency_percent.mjs _data/tlkids/math-flu_K1_2026-06-17.sqlite Kid1
node ../tools/fluency_percent.mjs _data/tlkids/math-flu_K1_2026-06-17.sqlite Kid1 --json
```

## Clone a learner's file as another user (testing)
`tools/clone_user_file.py` copies one learner's latest per-person `.sqlite` in a `_data` folder to a new file for another user, renaming the user everywhere inside (Users, Sessions, per-user config tables, and the name embedded in `session_filename`) and in the filename. The **target user's existing file(s) are deleted** — it prompts first unless `--force` is passed. The source file is never modified.

```
cd apps/math-quiz
python3 tools/clone_user_file.py tlkids Kid1 Randy            # prompts if a Randy file exists
python3 tools/clone_user_file.py tlkids Kid1 Randy --force    # deletes Randy's file without asking
```

Typical use: make your own file an exact clone of a kid's live file so you can run any mode as yourself against their data without any risk of touching their file.

## Tech stack
- **Frontend**: vanilla HTML/CSS/JS (no frameworks, no build step); SQLite in browser via sql.js
- **JS deps (CDN, pinned)**: sql.js 1.6.2, plotly 1.58.5, blueimp-md5 2.19.0, jszip 3.7.1, canvas-confetti 1.5.1. The vendored `sql-wasm.js`/`sql-wasm.wasm` are not currently loaded — kept as an offline option.
- **Data**: legacy quiz pages still use browser localStorage / downloads; the active anchor flow uses per-learner SQLite files under gitignored `_data/` (symlinked to `_LOCAL_FILES` in local worktrees). Every single-session archive mirrors to `s3://[S3-BUCKET]/math-quiz/single-sessions/`; Continue append creates external snapshots in `_BACKUP/math-quiz/sqlite-snapshots/` and best-effort mirrors those snapshots to `s3://[S3-BUCKET]/math-quiz/_backup-s3/`.

## Conventions
`problem_text` in session JSON and the DB is canonical (`5 + 3`, `5 * 3`, `5 / 3`). Display symbols (`×`, `÷`) are presentation-only; legacy files containing `&times;`/`×`/`÷` are normalized on parse. See `AGENTS.md` for the full conventions.

## Running locally
Open `math_quiz.html` in a browser for the quiz, `math_fluency.html` for fluency tracking, `math_analysis.html` for the analysis dashboard. The dashboards read sessions saved by the quiz on the same page origin, or load session JSON files via the Load Session Files control.

## Tests
Three layers, all self-contained in `tests/` (see `AGENTS.md` → Tests for details):
- **Unit (vm-based, no install):** `node --test apps/math-quiz/tests/*.test.mjs` from repo root
- **Unit (real sql.js DB) + E2E (Playwright, headless Chromium, hermetic CDN interception):** `cd apps/math-quiz/tests && npm install && npm run test:all`

## History
Originally developed in the external `math-quiz` repo (47 commits, contributors: CT, Randy True). Imported into fof-mono on 2026-06-03.

## Code reviews
A previous developer's AI-assisted PR review documentation is preserved in the `code_review_*.md` files. A thorough application review is in `2026-06-11_math-quiz-review.md`; its prioritized fixes (P1–P8) were applied on branch `review/math-quiz` in 2026-06.
