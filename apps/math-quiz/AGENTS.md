file: apps/math-quiz/AGENTS.md
title: math-quiz — Agent Instructions

Browser-based math quiz app for kids (quiz, fluency tracking, analysis dashboards). Vanilla HTML/JS/CSS, no build step. See `README.md` for components.

**Canonical source of truth — read these first:** `docs/SPEC.md` (what the app is: fluency rubric, accuracy-vs-fluency principle, fact/segmentation model, modes, mastery, storage, modality) and `docs/PLAN.md` (the living execution plan: phases, tasks, decision log, status). When a dated doc conflicts with the SPEC, the SPEC wins. The dated docs in `docs/` (`2026-06-11_math-quiz-review.md`, `2026-06-14_adaptive-and-profiles-goal.md`, `2026-06-15_assess-practice-modes-spec-and-plan.md`, `2026-06-15_guinea-pig-findings.md`, `single_digit_addition_segmentation.md`) are **historical sources** distilled into the SPEC; the screenshotted old-vs-new comparison is `docs/2026-06-16_compare-report/index.html`.


## Assess/practice engine + anchor page
An explicit assess/practice tool with a per-user SQLite store. Canonical definitions are in `docs/SPEC.md` and the sequenced work in `docs/PLAN.md` — read both before extending this area.
- **`engine/`** — DOM-free engine modules consumed by both the simulation and the live page, wired to the app's real functions by dependency injection: `write_mode.mjs` (JSON/SQLite write switch, dev default `sqlite-only`), `user_store.mjs` + `persistence.mjs` (per-user SQLite store on the existing `Users`/`Sessions`/`ProblemAttempts` schema + `ModeEvents`, IndexedDB/memory persistence, `.sqlite` export/import), `sqlite_io.mjs` (shared client I/O: base64↔bytes + `loadLatestUserDb` against `/api/latest-user-db`, used by anchor hydrate + analysis), `assess_flow.mjs` (warm-up discard, glitch re-deliver-and-confirm, predictive-mastery conclusion, and `createThoroughRun` — the glitch-tolerant continue-to-100% pass), `addition_segmentation.mjs` (segmentation categories + curated anchor plan; source of truth `single_digit_addition_segmentation.md`), `db_io.mjs` + `reevaluate.mjs` (re-processing: load raw attempts from a captured `.sqlite` and **statically** re-evaluate the fluency/mastery over them — see the spec, "re-processing"). The realism guardrail (`findSlowEasyFacts`) is shared by the live run and static re-eval. `targeted_practice.mjs` (serial targets + filler, cumulative fast-correct rings) and `visual_practice.mjs` + `ten_frame.mjs` (strategy-supported visual practice: cold probe → ten-frame teach → immediate/spaced retrieval; pure-SVG make-ten steps) drive the two practice modes — design doc `docs/2026-07-25_visual-practice-design.md`.
- **`anchor.html` / `anchor.js`** — the live fast-fluency demonstration page. Loads `math_utils.js` (pure) + sql.js (CDN); deliberately does **not** load `math_fluency.js` (it auto-bootstraps the fluency page). Run: `python3 -m http.server` then open `anchor.html`.
- **`tools/dev_server.py`** — local dev server (serves the app and does the local-folder save + automatic backups the browser can't do). It's a thin wrapper around Python's static file server that adds API endpoints, reading/writing the **local `_data/` folder** as the source of truth; in local worktrees `_data` is a symlink into `_LOCAL_FILES`. POSTs from the page (`/api/save-run` with `sourceFolder`, `destination` = `source`|`test`, optional `forceNew`) save under `_data/<folder>/…`; every raw single-session file is best-effort uploaded to `s3://[S3-BUCKET]/math-quiz/single-sessions/`, and Continue append snapshots the pre-change source file to `_BACKUP/math-quiz/sqlite-snapshots/` plus `s3://[S3-BUCKET]/math-quiz/_backup-s3/`. The page lists source folders via `GET /api/data-folders` and reads a learner's latest per-person file via `GET /api/latest-user-db?folder=<source>&user=` (Continue latest). Naming/recency/append routing lives in `tools/anchor_store.py` (`pick_latest`, `next_multi_name`, `resolve_save`); see SPEC §8a–8c. Localhost only; never deploy. (Named `dev_server`, not `anchor_*` — "anchor" is reserved for the fluent-demonstration use case, not infrastructure.)


## Running locally
A plain static server works for everything except S3 upload. From `apps/math-quiz/`:
```
python3 -m http.server 8907
```
To also save runs to `_data/` and create automatic S3/local backups, run the dev server instead (needs the repo venv for boto3/python-dotenv when S3 backup is available). From `apps/math-quiz/`:
```
python3 tools/dev_server.py
```
If boto3/dotenv aren't on your `python3`, use the repo venv: `source ../../.venv/bin/activate` first, or run `../../.venv/bin/python3 tools/dev_server.py`. Not in `apps/math-quiz/`? `cd apps/math-quiz` first. Then open `http://127.0.0.1:8907/anchor.html`.
**Why a Python file now vs. just opening the HTML before:** the page is plain HTML/JS, so a static server (`http.server`) is all it needs to *run*. But a browser page can't write to your local folders or use your `.env` AWS credentials. `dev_server.py` wraps that same static server and adds one endpoint so the page can hand off the run file for local save plus automatic snapshot backup. Use it only when you want that; otherwise the static server is fine.
- **Data / downloads:** anchor runs persist to browser IndexedDB, download as a `.sqlite` file, and (via the dev server) save to the gitignored **`_data/`** folder. Every single-session archive mirrors to `s3://[S3-BUCKET]/math-quiz/single-sessions/`; Continue append snapshots go to `_BACKUP/math-quiz/sqlite-snapshots/` and mirror to `s3://[S3-BUCKET]/math-quiz/_backup-s3/`. Never commit learner data.


## Key conventions
- `problem_text` in session JSON and the DB is canonical: `5 + 3`, `5 * 3`, `5 / 3`. Display symbols (`×`, `÷`, `&times;`) are presentation-only — render with `formatProblemTextForDisplay()`, and parse any legacy form with `parseProblemText()` (which normalizes via `normalizeOperationSymbols()`).
- Shared logic lives in `math_utils.js`, loaded by all three pages. Keep new helpers DOM-free where possible so they stay testable.
- Sessions live in browser localStorage per origin (`math_session_*.json` keys); each dashboard load rebuilds an in-memory sql.js DB from them. `ProblemAttempts` has no unique constraint — never insert a session whose `session_id` already exists (`importSessionData` guards this; replace via `deleteSessionFromDb` first if a re-import should win).
- Escape user-entered strings with `escapeHtml()` before interpolating into `innerHTML` or attribute values.
- Production deploy is copy/paste into Webflow custom-code blocks; keep files self-contained and watch size limits (`web-shared/z_count_chars_in_js.sh`).

## Tests
All test code is self-contained in `tests/` (own `package.json`; the app itself has no build step or dependencies). Three layers:

### Unit — vm-based (no install needed)
Run from repo root: `node --test apps/math-quiz/tests/*.test.mjs`
`tests/load_app.mjs` evaluates the browser scripts in a Node vm with DOM/localStorage stubs. Covers symbol normalization and parsing, problem generation, problem-list/session-JSON parsing, grading edge cases (division by zero, string answers), fluency status evaluation and permanent-status logic, generator sampling, and analysis aggregation/sorting/flag filtering.

### Unit — real database (needs `npm install` in `tests/`)
`cd apps/math-quiz/tests && npm install && npm test` (runs all unit tests)
`db_import.test.mjs` runs the actual import/query code against an in-memory sql.js engine: import, dedupe-on-reimport, delete+replace, fluency datasets from legacy-symbol rows, permanent (blue) upgrades, operation filters, quote-safe usernames. Skips cleanly when node_modules is absent. The assess/practice engine is covered by `adaptive_selector`, `simulation`, `start_state`, `write_mode`, `user_store`, `assess_flow`, `addition_segmentation`, `reevaluate` (re-processing), `targeted_practice` (targeted fluency practice), `visual_practice` + `ten_frame` (visual
practice engine + teach renderer), `teach_policy`, and `fluency_list_generator` (build a practice list of a
given length + fluency-category mix from a learner's history) test files. The dragon game is covered by `dragon_burst_session`,
`dragon_milestones`, `dragon_session_json`, `dragon_sim_learner`, `dragon_playthrough_smoke`
(the in-memory playthrough incl. story-beat cadence), `dragon_story` (story engine: phases,
beat ordering/no-repeat, quiz reactions, objectives), and `dragon_gm_state` (the Game Master
snapshot builder) test files.

### E2E — Playwright (needs `npm install` in `tests/`)
`cd apps/math-quiz/tests && npm run test:e2e` (`npm run test:all` runs everything)
Drives the real pages in headless Chromium against a local static server (`python3 -m http.server`, started automatically). **Hermetic:** all CDN libraries (sql.js, plotly, md5, jszip, confetti) are served from `tests/node_modules` via request interception — no network needed at test time, and the pinned versions match the CDN URLs in the app.
Browser resolution (`playwright.config.mjs`): a browser from `npx playwright install chromium` if present, else the npm-packaged `@sparticuz/chromium` (linux x64 — works in sandboxes where Playwright's browser CDN is blocked), else set `PLAYWRIGHT_CHROMIUM_PATH`.
Specs: `e2e/quiz.spec.mjs` (complete quiz, custom multiplication, wrong answer + override, I-don't-know flag, flag comments, end-early, auto-submit), `e2e/analysis.spec.mjs` (seeded sessions, operation/flag filters incl. legacy symbols, sorted flag editing, lossless export, quoted usernames), `e2e/fluency.spec.mjs` (dataset building, manual overrides, permanent blue status, generator → quiz → session round trip), `e2e/anchor.spec.mjs` (anchor page: fluent conclusion + per-run `.sqlite` save, default keypad digit entry, optional big-number keys, returning-user persistence), `e2e/targeted.spec.mjs` (targeted practice: prefill from per-learner defaults (incl. K2's 5/4000/30) and a stored file config, validation + whitespace normalize, **serial** targets, target-rings graphic, single-target graduation → summary, **Pause** (Continue / Continue & skip), Flag previous + Continue & insert, live progress, the filler editor auto-save, and config persisted in the save-run payload), `e2e/visual.spec.mjs` (visual practice: Kid1 defaults prefill + secure-filler editor, wrong cold probe → ten-frame teach → immediate/spaced retrieval → clear, saved `visual_practice` roles + `session_type`, and the Pass path), and `e2e/landing.spec.mjs` (kid landing: default Kid1/K2 quick-pick page, `?setup=1` / "Other…" reveal the full setup, picking a learner Continues their file and the pop-up starts Targeted practice, the internal Problem list, or a **Quick quiz** (the auto-generated 7-problem set for +, −, or ×, launched straight from the pop-up; the op buttons disable for operations the file has no set for), "ask Baba" when a mode isn't set up or no file exists).

Note: the full setup card is hidden behind the kid landing by default; pass `?setup=1` to load it directly (all setup-driving e2e navigations use this).

### Python — tools (stdlib `unittest`)
Run from repo root: `.venv/bin/python3 -m unittest discover -s apps/math-quiz/tools -p "test_*.py"` (`dev_server`'s boto3/dotenv imports are wrapped). Covers
`combine_sqlite` (schema introspection / canonical-schema selection / merge), `anchor_store`,
`problem_list_store`, `clone_user_file` (safe clone/rename and atomic replacement), `dev_server`
(source↔destination routing), **`dev_server_dragon`** (the
dragon Game Master sync store: `/api/dragon-state` snapshot save/view + the `/api/dragon-messages`
send → unread poll → mark-read cycle, JSON under `_data/<folder>/dragon-gm/`), **`targeted_store`** (the
`TargetedConfig` table + dev-server `/api/targeted-config` GET/POST and save-run persistence of the
targeted-practice config), **`quick_practice_store`** (the `QuickPracticeItems` table: the
fluency rubric port, the escalating-difficulty fill, and save-run regeneration of the 21 rows), and
**`visual_store`** (the `VisualPracticeConfig` table + dev-server persistence),
**`fluency_feast_store`** (the `FluencyFeastConfig` table + dev-server `/api/fluency-feast-config`
GET/POST — the per-file preset the kid's "Fluency feast" reads), **`clone_user_file`** (clone one
learner's latest per-person file as another user for testing — renames the user in every table +
the filename, deletes the target user's existing file with prompt/--force), and **`profile_store`** (the
`Profile` table + dev-server `/api/profile` GET/POST — per-file display flags + the fluency rubric:
`showFluencyPercent` (default on, gates the anchor end-of-quiz start→end %-fluent readout) and
`thresholds` {greenMs, redMs, windowSize, minAccuracy}, defaulting to the system rubric. The
analysis page's "Save to loaded file" button writes the rubric into the loaded learner's profile;
the anchor end-of-quiz % and the generate-by-fluency lists read it (falling back to defaults). The
dev-server problem-list/feast/profile edits target the named file (`file` param), falling back to
the user's latest lineage.

### Fluency problem-list generation rules (fluency_core.js)
`generateFluencyProblemList` enforces three system rules (not learner-configurable): (1) **easier
first** — within each fluency-status pool, facts are drawn easiest-category first
(`FLUENCY_CATEGORY_ORDER`: add-zero→hardest-six), so a learner demonstrates fluency on the easy
categories before harder ones surface; (2) a **repeat cap** — one problem appears at most
`ceil(0.15·listLength)` times (3 in 20, 2 in 10); (3) **no back-to-back duplicates** — the final
order reshuffles until no problem repeats adjacently (guaranteed even/odd-spread fallback). When a
category can't fill its allocated slots because the repeat cap limits a tiny pool, unfilled slots
**backfill** from almost → needs-practice → missing → fluent (yellow → red → nodata → green).

### Targeted-practice config persistence
Targets, the single "target filler" list, and the params (graduate-after / fast-threshold ms /
percent-target) live in the per-user SQLite file (`tools/targeted_store.py`, `TargetedConfig` table),
read/written exactly like internal problem lists: `/api/latest-user-db` returns `targetedConfig`;
`/api/targeted-config` (GET/POST) and the save-run payload write it. The anchor page prefills the
fields from the file, falling back to per-learner code defaults (`TARGETED_DEFAULTS` in `anchor.js`).
There is **no max-bursts**: a session ends only when every target graduates; Quit & save at any break
stores the partial session.

### Visual-practice sessions (ten-frames) + config persistence
A third session kind alongside assess and targeted (kid button "Targeted ten frames"): 1–5 target facts run through cold probe → optional ten-frame teach (the persistent 💡 lightbulb records a pass and opens it; a wrong answer opens it automatically) → filler-spaced delayed retrievals until `retrievalsToClear` cumulative fast-corrects (no immediate re-ask after a teach — the answer was just shown; the session ends right on the final clear, which plays a distinct completion animation). Every attempt records a `visual_practice` role (`cold-probe` | `immediate-retrieval` | `delayed-retrieval` | `filler`, plus `visual_shown` / `passed`) into `VisualPracticeAttemptRoles`; the session writes `Sessions.session_type = 'visual-practice'` and the `VisualPracticeSessions`/`VisualPracticeTargets` metadata tables. **Visual sessions count toward every fluency feed** (anchor %-readout, feast + list generators, fluency dashboard, analysis fluency overlay, quick-practice regeneration, dragon game) — same as assess/list/targeted. Per-user setup (targets / secure filler / fastMs / retrievalsToClear / hesitationMs) lives in `VisualPracticeConfig` (`tools/visual_store.py`), read/written exactly like the targeted config: `/api/latest-user-db` returns `visualConfig`; `/api/visual-config` (GET/POST) and the save-run payload write it; the anchor page prefills from the file, falling back to `VISUAL_DEFAULTS` in `anchor.js`. Design + research rationale: `docs/2026-07-25_visual-practice-design.md`.

The ten-frame teach visual is now available app-wide for teachable addition facts, not only inside Visual practice. Trigger policy is centralized in `engine/teach_policy.mjs`; that file is the only place to change when the lightbulb appears or when wrong answers auto-open the visual. Lightbulb-help attempts outside Visual practice are flagged with reason `lightbulb`, so the standard `excludeFlagged` fluency paths ignore them while keeping the audit trail visible.

### Quick-practice sets (auto-generated)
A machine-generated practice set per operation lives in the per-user SQLite file
(`tools/quick_practice_store.py`, `QuickPracticeItems` table) — **not** part of the "Use internal"
problem-list queue. Each operation (`+`, `-`, `*`) gets exactly **7 problems** = **21 rows per user**,
**regenerated after every saved quiz** from the learner's live fluency:
- **3 fluent** (status green, or blue/permanent), **3 almost** (yellow), **1 needs practice** (red).

Fluency is never stored — it is recomputed from raw `ProblemAttempts` each time (same rubric as the
dashboard: `quick_practice_store` ports `evaluateFluencyStatus` + the combined/permanent roll-up from
`fluency_core.js` / `math_fluency.js`). Regeneration is **server-side** in `dev_server.save_run`
(`_regenerate_quick_practice`), because the merged per-user file holds the full cross-session history
the rubric needs; it runs for destination `source` only (never test trials). When a bucket lacks
enough real facts (no data / highly incomplete), the missing slots are filled by an
**escalating-difficulty algorithm** over the 0–9 fact universe (easiest → fluent slots, middle →
almost, hardest → needs-practice), so a brand-new learner still gets a sensible ramp. Each row records
`slot_status` (the bucket it fills), `fact_status` (the fact's computed status, when from real data),
and `origin` (`data` | `algorithm`). Addition difficulty uses the formal segmentation
(`single_digit_addition_categorization.md` / SPEC §5); `*`/`-` use documented heuristics pending their
formal "eventual ×/− equivalents" (SPEC §5). The set is exposed on `/api/latest-user-db`
(`quickPractice`) and via the CLI (`python3 tools/quick_practice_store.py <db> <user> show|regenerate`);
external readers (e.g. the Minecraft mod) query the table directly:
`SELECT problem_text FROM QuickPracticeItems WHERE user_name=? AND operation='+' ORDER BY item_order`.
In the app, the anchor kid pop-up offers it as **Quick quiz** with +/−/× buttons that launch the
operation's 7-problem set straight away (`anchor.js` `onKidQuickQuiz` → `buildQuickPracticeConfig`,
fed by the `quickPractice` field on `/api/latest-user-db`); buttons disable for operations the loaded
file has no set for.
