file: 2026-06-03_bring-over_math-quiz.md
title: Bring-over plan — math-quiz repo into fof-mono
last-updated: 2026-06-04_0900
ai: Claude Code (Opus)
session: `math-quiz bring-over`

## Purpose
Bring the external `math-quiz` repo (developed by CT with AI-assisted PR reviews) into `fof-mono` as a NEW app at `apps/math-quiz/` (kebab-case, per naming conventions). The older snapshot at `apps/math_quiz/` (snake_case, from corpus-tools pare-down) stays as-is — it's a deprecated predecessor.


## Branch strategy
- **SOURCE** (`math-quiz`): branch `export/to-fof-mono` off `main`. Reorganize kept files into fof-mono target paths, commit, leave FROZEN. Never PR or merge back into source main.
- **TARGET** (`fof-mono`): branch `import/from-math-quiz` off `main`. All copying, gitignore changes, doc updates happen here. Never push to main. PR only with explicit approval.


## Current state

### Source repo (math-quiz)
- 47 commits, 3 contributors (CT, ct-user, Randy True)
- Single project: browser-based math quiz for kids (HTML/CSS/JS frontend + Python analysis backend)
- Latest code includes PR #5 (fluency-tracker merge): `math_fluency.html`, `math_fluency.js`, `math_utils.js`, plus updated `math_quiz.js`, `math_analysis.js/html`, `math_quiz.css`
- CT's AI-assisted PR reviews are documented in 8 `code_review_*.md` files

### Existing fof-mono snapshot (apps/math_quiz/) — DELETED
- Was brought over in the initial commit from corpus-tools pare-down
- Was older/deprecated — missing fluency-tracker files, outdated code, contained `compare_o1/` (9 files from corpus-tools, not in source repo)
- **Deleted entirely** as part of this bring-over — fully superseded by `apps/math-quiz/`


## Decisions (confirmed by Randy)
1. **Sounds (2 MP3s, 58KB total)**: REPO — small, needed at runtime. Requires gitignore exception since `*.mp3` is globally ignored.
2. **compare_o1/ in old apps/math_quiz/**: KEEP as-is (part of deprecated snapshot, untouched).
3. **Code review markdown files (8 files)**: REPO — keep as documentation of CT's work and development progression.
4. **math-quiz.db (28KB)**: REPO — keep tracked. Small, no sensitive data. The `math-quiz_data/` folder in the new app is small (~0.3 MB with WAV files correctly untracked).
5. **Session JSON PII**: OK to keep tracked (child first names as usernames, already tracked in old snapshot). However: session JSONs will go to S3 — do NOT bring session data from the source repo into fof-mono's git tree. The old `apps/math_quiz/` already has them and will be cleaned up later.
6. **Target folder**: `apps/math-quiz/` (kebab-case) — NEW folder, not overwriting the old `apps/math_quiz/`.


## Flags
- **Secrets/API keys**: NONE detected. No rotation needed.
- **PII**: Session JSON files contain child first names as usernames. Low sensitivity; not `[S3-BUCKET]`-level. Session JSONs go to S3, not into fof-mono git.
- **Large/bulk data**: 6 WAV files (~11 MB total, speech recordings) + all session JSON files (~400KB total) → S3.
- **Vendored deps**: `sql-wasm.js` (48KB) + `sql-wasm.wasm` (639KB) — SQLite WASM runtime. Keep in repo (<1MB, needed at runtime).
- **Build artifacts**: None.
- **No dependency files**: No package.json, requirements.txt. Python deps are stdlib. JS deps via CDN.


## Per-item disposition

### Source code → REPO (at `apps/math-quiz/`)

| Source path | Disposition | Target path in fof-mono | Notes |
|---|---|---|---|
| `math_quiz.html` | REPO | `apps/math-quiz/math_quiz.html` | Main quiz page |
| `math_quiz.js` | REPO | `apps/math-quiz/math_quiz.js` | 70KB — latest with fluency features |
| `math_quiz.css` | REPO | `apps/math-quiz/math_quiz.css` | 9KB — latest |
| `math_quiz.py` | REPO | `apps/math-quiz/math_quiz.py` | 21KB Python quiz helper |
| `math_analysis.html` | REPO | `apps/math-quiz/math_analysis.html` | 16KB — latest |
| `math_analysis.js` | REPO | `apps/math-quiz/math_analysis.js` | 46KB — latest |
| `math_analysis.py` | REPO | `apps/math-quiz/math_analysis.py` | 15KB Python analysis |
| `math_fluency.html` | REPO | `apps/math-quiz/math_fluency.html` | 24KB — from fluency-tracker PR |
| `math_fluency.js` | REPO | `apps/math-quiz/math_fluency.js` | 49KB — from fluency-tracker PR |
| `math_utils.js` | REPO | `apps/math-quiz/math_utils.js` | 10KB — shared utility |
| `math_quiz.ipynb` | REPO | `apps/math-quiz/math_quiz.ipynb` | 20KB Jupyter notebook |
| `math_quiz_0626.css` | REPO | `apps/math-quiz/math_quiz_0626.css` | Alternate CSS variant |
| `math_quiz_0653.css` | REPO | `apps/math-quiz/math_quiz_0653.css` | Alternate CSS variant |
| `sql-wasm.js` | REPO | `apps/math-quiz/sql-wasm.js` | Vendored SQLite WASM (48KB) |
| `sql-wasm.wasm` | REPO | `apps/math-quiz/sql-wasm.wasm` | Vendored SQLite WASM binary (639KB) |

### Sounds → REPO (at `apps/math-quiz/sounds/`, with gitignore exception)

| Source path | Disposition | Target path | Notes |
|---|---|---|---|
| `sounds/old-horn-honking-ballhupe.mp3` | REPO | `apps/math-quiz/sounds/old-horn-honking-ballhupe.mp3` | 28 KB — UI sound effect |
| `sounds/vibration-springs-vibrate.mp3` | REPO | `apps/math-quiz/sounds/vibration-springs-vibrate.mp3` | 30 KB — UI sound effect |

Requires gitignore exception: `!apps/math-quiz/sounds/*.mp3`

### SQLite database + data folder → GITIGNORE-LOCAL

The entire `math-quiz_data/` folder (including `import_db/math-quiz.db`) is gitignored. The data folder will be dealt with later when working on math-quiz alongside the Minecraft Mathquest mod. Session JSON files generated during testing go here and are safely gitignored.

| Source path | Disposition | Target path | Notes |
|---|---|---|---|
| `math-quiz_data/import_db/math-quiz.db` | GITIGNORE-LOCAL | `apps/math-quiz/math-quiz_data/import_db/math-quiz.db` | 28KB, gitignored |

### Session data (JSON) + audio recordings → S3 ([S3-FILES-BUCKET])

Session JSON files and WAV recordings are NOT brought into fof-mono's git tree. They go to S3 only.

| Source path | Disposition | S3 key ([S3-FILES-BUCKET]) | Notes |
|---|---|---|---|
| `math-quiz_data/*.json` (~38 root files) | S3 | `apps/math-quiz/math-quiz_data/*.json` | Session performance data |
| `math-quiz_data/import_db/*.json` (9 files) | S3 | `apps/math-quiz/math-quiz_data/import_db/*.json` | Imported session data |
| `math-quiz_data/2025-01-21_K1/*.json` (6 files) | S3 | `apps/math-quiz/math-quiz_data/2025-01-21_K1/*.json` | Session data |
| `math-quiz_data/2025-01-21_K1/sw_with_math_quiz/*/meta.json` (6 files) | S3 | (same path pattern) | Recording metadata |
| `math-quiz_data/2025-01-21_K1/sw_with_math_quiz/*/output.wav` (6 files) | S3 | (same path pattern) | ~11 MB total speech recordings |
| `math-quiz_data/before presets/*.json` (3 files) | S3 | (same path pattern) | Early test data |
| `math-quiz_data/buggy/*.json` (1 file) | S3 | (same path pattern) | Debug session |

S3 keys follow the 1:1 repo-path convention: `s3://[S3-FILES-BUCKET]/apps/math-quiz/math-quiz_data/...`. Note: the S3 key uses the NEW `math-quiz` path (kebab-case), not the old `math_quiz`.

### Documentation & code reviews → REPO (at `apps/math-quiz/`)

| Source path | Disposition | Target path | Notes |
|---|---|---|---|
| `PLAN_math_quiz.md` | REPO | `apps/math-quiz/PLAN_math_quiz.md` | Feature roadmap |
| `combined_math_quiz.md` | REPO | `apps/math-quiz/combined_math_quiz.md` | 76KB consolidated reference |
| `CODE_REVIEW.md` | REPO | `apps/math-quiz/CODE_REVIEW.md` | 3.2KB code review summary |
| `LICENSE.md` | REPO | `apps/math-quiz/LICENSE.md` | 1.1KB license |
| `0to9_75problems.txt` | REPO | `apps/math-quiz/0to9_75problems.txt` | 449B problem set |
| `code_review_duplicate_handling_fluency_features.md` | REPO | `apps/math-quiz/code_review_duplicate_handling_fluency_features.md` | 29KB — CT's PR review docs |
| `code_review_flag_features_completion.md` | REPO | `apps/math-quiz/code_review_flag_features_completion.md` | PR review doc |
| `code_review_flag_filter.md` | REPO | `apps/math-quiz/code_review_flag_filter.md` | PR review doc |
| `code_review_flag_filter_2.md` | REPO | `apps/math-quiz/code_review_flag_filter_2.md` | PR review doc |
| `code_review_fluency_tracker_refactor.md` | REPO | `apps/math-quiz/code_review_fluency_tracker_refactor.md` | PR review doc |
| `code_review_fluency_tracking.md` | REPO | `apps/math-quiz/code_review_fluency_tracking.md` | PR review doc |
| `code_review_idk_display_fix.md` | REPO | `apps/math-quiz/code_review_idk_display_fix.md` | PR review doc |
| `code_review_small_changes.md` | REPO | `apps/math-quiz/code_review_small_changes.md` | PR review doc |

### DISCARD (not brought over)

| Source path | Disposition | Notes |
|---|---|---|
| `README_external - COPY FROM CORPUS-TOOLS.md` | DISCARD | Legacy reference copy; name says it's a copy |
| `README_internal - COPY FROM CORPUS-TOOLS.md` | DISCARD | Legacy reference copy; name says it's a copy |
| `scratch.md` | DISCARD | Empty file |
| `settings COPY TO USER SETTINGS.json` | DISCARD | VS Code user settings template; not project code |
| `ai_threads/2025-10-24_cursor RT_understand structure.md` | DISCARD | Cursor chat transcript |
| `ai_threads/2025-10-27_chatgpt_kickoff thread.md` | DISCARD | ChatGPT chat transcript |
| `.vscode/settings.json` | DISCARD | VS Code workspace settings — fof-mono has its own |
| `.vscode/cspell.json` | DISCARD | Spell checker config |
| `.vscode/tasks.json` | DISCARD | VS Code tasks |
| `.vscode/snippets_corpus-tools.code-snippets` | DISCARD | Code snippets for the old repo |
| `.gitignore` | DISCARD | Source's gitignore only covers .DS_Store; fof-mono has comprehensive gitignore |

### Existing fof-mono `apps/math_quiz/` → DELETED

The deprecated `apps/math_quiz/` (snake_case, 82 files including session JSONs and compare_o1/) was deleted entirely. Fully superseded by the new `apps/math-quiz/` import.


## Export branch layout (source repo)
On `export/to-fof-mono` in math-quiz, reorganize kept files into their fof-mono target paths:

```
apps/math-quiz/
  math_quiz.html
  math_quiz.js
  math_quiz.css
  math_quiz.py
  math_analysis.html
  math_analysis.js
  math_analysis.py
  math_fluency.html
  math_fluency.js
  math_utils.js
  math_quiz.ipynb
  math_quiz_0626.css
  math_quiz_0653.css
  sql-wasm.js
  sql-wasm.wasm
  PLAN_math_quiz.md
  combined_math_quiz.md
  CODE_REVIEW.md
  LICENSE.md
  0to9_75problems.txt
  code_review_duplicate_handling_fluency_features.md
  code_review_flag_features_completion.md
  code_review_flag_filter.md
  code_review_flag_filter_2.md
  code_review_fluency_tracker_refactor.md
  code_review_fluency_tracking.md
  code_review_idk_display_fix.md
  code_review_small_changes.md
  sounds/
    old-horn-honking-ballhupe.mp3
    vibration-springs-vibrate.mp3
  math-quiz_data/
    import_db/
      math-quiz.db
```

Items NOT on the export branch: `.vscode/`, `ai_threads/`, `README_*.md`, `scratch.md`, `settings COPY TO USER SETTINGS.json`, `.gitignore`, all session JSON files, all `output.wav` files.


## fof-mono changes (import branch)

### 1. Create `apps/math-quiz/` with source code
New folder (kebab-case). Copy all REPO-disposition files from the export branch layout.

### 2. Gitignore exception for sounds
Add to fof-mono `.gitignore`:
```
# math-quiz: small UI sound effects, keep in repo despite global *.mp3 rule
!apps/math-quiz/sounds/*.mp3
```

### 3. S3 setup for session data + audio — DEFERRED
S3 upload of math-quiz session data (JSON files, WAV recordings) is deferred. Will be handled later when digging into the math-quiz app alongside the Minecraft Mathquest mod (which also writes math quiz JSON data). At that point, the overall math quiz data strategy (from multiple apps) will be decided together.

When ready, follow the general guide at `bring-over-s3-upload-guide.md`.

### 4. Update AGENTS.md
- Directory guide: add `apps/math-quiz/` entry (math quiz web app, imported from external math-quiz repo)
- Update the old `math_quiz` note to say "deprecated — superseded by `apps/math-quiz/`"

### 5. Update PROJECTS.md
Update the Math quiz project index entry:
- Primary folder: `apps/math-quiz/` (was `apps/math_quiz/`)
- Add note: imported from external `math-quiz` repo on 2026-06-03
- Note legacy snapshot at `apps/math_quiz/` (deprecated)

### 6. Per-app AGENTS.md
Not needed — the app is simple enough to inherit root AGENTS.md.

### 7. Dependencies
All Python deps used by math-quiz are already in fof-mono's `dependencies/requirements_2024-09-26_add_CURRENT.txt`:
- `pygame>=2.6.1` — math_quiz.py (comment: "added 10-11-2024 for math_quiz.py")
- `pyttsx3>=2.98` — math_quiz.py (comment: "added 10-11-2024 for math_quiz.py")
- `matplotlib==3.9.2` — math_analysis.py
- `seaborn==0.13.2` — math_analysis.py (comment: "added 9-26-2024 for math_analysis.py")
- `pandas` (via seaborn/matplotlib deps)
- `numpy` (via matplotlib/seaborn deps)

No new dependencies needed. JavaScript deps are all via CDN (blueimp-md5, jszip, canvas-confetti).

### 8. Tests
No tests exist in the source repo. No tests to retarget.

### 9. Known code path issues
`math_analysis.py` has hardcoded paths referencing the old corpus-tools layout:
- `projects/math_quiz/math-quiz_data/import_db/math-quiz.db` — should be `apps/math-quiz/math-quiz_data/import_db/math-quiz.db`
- `math_quiz.py` has a conditional import: `from primary.fileops import get_current_datetime_filefriendly` — `primary` was renamed to `core` in fof-mono

These are non-blocking: the Python scripts are standalone local analysis tools, not part of the web app. Fix them when actively working on math-quiz Python analysis.


## Execution checklist (Phase 4)

- [x] Source `export/to-fof-mono` branch: reorganize REPO-disposition files into `apps/math-quiz/` layout
- [x] Source `export/to-fof-mono` branch: commit (f1fea1f) and leave FROZEN
- [x] fof-mono `import/from-math-quiz` branch: create `apps/math-quiz/` with files from export layout
- [x] fof-mono: add gitignore exception for sounds MP3s
- [x] fof-mono: create `apps/math-quiz/README.md`
- [x] fof-mono: update AGENTS.md directory guide
- [x] fof-mono: update PROJECTS.md entry
- [x] fof-mono: create general S3 upload guide (`bring-over-s3-upload-guide.md`)
- [x] fof-mono: rename `math_quiz_data/` → `math-quiz_data/`, `math_quiz.db` → `math-quiz.db`
- [x] fof-mono: gitignore `apps/math-quiz/math-quiz_data/` (entire data folder)
- [x] fof-mono: update code references for renamed data folder/db
- [x] fof-mono: basic functional test of quiz app
- [x] fof-mono: update bring-over playbook with data hygiene rules
- [deferred] S3 upload of math-quiz session data + audio — deferred until math quiz data strategy is decided alongside Minecraft Mathquest integration
- [x] fof-mono: add prioritized cleanup next steps to bring-over plan
- [x] fof-mono: delete deprecated `apps/math_quiz/` (82 files, fully superseded)
- [x] fof-mono: open PR (approved by Randy)


## S3 upload — DEFERRED

S3 upload of math-quiz session data and audio recordings is deferred entirely. The data will be addressed later when:
1. Digging into the math-quiz app for active development
2. Integrating with the Minecraft Mathquest mod (which also writes math quiz JSON data)
3. Deciding an overall data strategy for math quiz data across multiple apps

When ready, follow the general guide at `bring-over-s3-upload-guide.md` and use ONLY `core/s3_archive.py` for uploads.

The current state is acceptable:
- `apps/math-quiz/math-quiz_data/` is entirely gitignored — the db and any test session JSONs stay local
- Session JSON files and WAV recordings from the source repo were NOT brought into fof-mono (correctly excluded)
- The old `apps/math_quiz/` (from corpus-tools carryover) has been deleted entirely — no longer a cleanup concern


## Basic functional test

Before opening the PR, verify the quiz app works correctly in a browser. Open `apps/math-quiz/math_quiz.html` in a browser (File → Open or `open apps/math-quiz/math_quiz.html` on macOS).

### Test steps

1. [x] **Page loads**: Confirm the quiz page renders without console errors (check browser DevTools → Console).
_only `Unsafe attempt to load URL` error - Your log shows the app initialized correctly; the last line is a file-protocol + browser security issue, not a failed import or script error (see cursor thread)._
2. [x] **Start a quiz**: Enter a name (e.g. "Test"), select default settings (addition, numbers 0-9), click Start.
3. [x] **Answer problems**: Answer 3-5 problems — try a mix of correct and intentionally wrong answers.
4. [x] **Sound effects**: Confirm the correct/incorrect sound effects play (horn honk for wrong, spring for correct — or vice versa). If no sound, check that the browser allows audio and that `sounds/*.mp3` files are present.
5. [x] **Session completes**: After the set number of problems, confirm the summary screen shows: total problems, correct count, average response time.
6. [x] **Session data saved (localStorage)**: On the post-quiz screen, confirm the console lists a new `math_session_<name>_<timestamp>.json` key (or check DevTools → Application → Local Storage for the same origin). The browser does not write to `apps/math-quiz/math-quiz_data/` automatically — that folder is for downloaded or imported files only (gitignored).
7. [x] **Download session data and verify**: Click **Download This Session Data**, save the file, open the JSON, and confirm it contains `user`, `session`, and a `problems` array with attempt records.
_created `math-quiz_data` folder in the files save dialog and now see it in the cursor explorer view._
8. [x] **Analysis dashboard**: Click `Go to Analysis`. Confirm it loads without errors.
9. [x] **Fluency tracker**: Click `Go to Fluency Tracker`. Confirm it loads and can display session data (it reads from browser localStorage / imported data, not the repo data folder unless you load files in).

Optional (cleanest): run python3 -m http.server 8765 in apps/math-quiz/ and use http://localhost:8765/math_quiz.html so quiz and analysis share one origin reliably.

### Pass criteria
Steps 1-5 pass = the core quiz works. Steps 6-7 confirm session capture and export. Steps 8-9 are secondary (fluency tracker and analysis may need accumulated data to be fully useful).

### Code changes made for fixing local navigation

Functional testing exposed two problems: **Go To Analysis** from `file://` sent users to the live Focus on Foundations site (empty localStorage), and after wiring shared navigation helpers the quiz page threw `useLocalMathQuizPages is not defined` because it did not load `math_utils.js`.

- **`math_utils.js`**: Added `useLocalMathQuizPages()` (`file://`, `localhost`, `127.0.0.1`) and `getMathQuizSessionStorageKeys()`; `importJsonDataToDb()` logs how many sessions were imported for the current origin.
- **`math_quiz.html`**: Load `math_utils.js` before `math_quiz.js` so quiz navigation can call the helper.
- **`math_quiz.js`**, **`math_analysis.js`**, **`math_fluency.js`**: Replaced hostname-only checks with `useLocalMathQuizPages()` for links between quiz, analysis, and fluency (relative local HTML instead of production URLs when testing locally).
- **`math_analysis.js`**: Empty-storage hint under Session Data Management; fixed ProblemAttempts count logging (`stmt.step()` before `getAsObject()`, kept `AS count`).

Analysis still reads sessions from **localStorage** (or **Load Session Files**), not automatically from `math-quiz_data/` on disk. Old sessions in the heatmap are expected if they remain in browser storage for that origin.


## Prioritized next steps (cleanup / problems only)

These are known issues and technical debt — not features. Ordered by impact.

### P1 — Hardcoded production URLs (Webflow hosting dependency)

All three JS files (`math_quiz.js`, `math_analysis.js`, `math_fluency.js`) hardcode `https://www.focusonfoundations.org/math-*` as the production navigation targets. The `useLocalMathQuizPages()` helper handles the local/production toggle correctly, but the production URLs themselves are scattered as string literals (6 occurrences across 3 files). Problems:
- Changing hosting (away from Webflow) requires find-and-replace across all JS files.
- The HTML files have Webflow deployment comments (`🚀 WEBFLOW MISSION`, `🎭 WEBFLOW STAGE`) baked into the markup (`math_analysis.html`).

**Fix**: Extract the production base URL into a single config constant (e.g. `MATH_QUIZ_BASE_URL` in `math_utils.js`). Remove or update the Webflow deployment comments when hosting changes.

### P2 — Python import path: `from primary.fileops`

`math_quiz.py:179` imports `from primary.fileops import get_current_datetime_filefriendly`. The `primary` package was renamed to `core` in fof-mono. This will fail if `math_quiz.py` is run from the fof-mono tree.

**Fix**: Change to `from core.fileops import get_current_datetime_filefriendly`.

### P3 — Notebook stale imports

`math_quiz.ipynb` likely has the same `from primary.fileops` import and possibly other stale paths from the source repo. Not verified cell-by-cell.

**Fix**: Audit and update all import paths in the notebook to use `core.*`.

### P4 — `combined_math_quiz.md` may be stale

The 76KB consolidated reference doc was generated at a point in time. Code snippets embedded in it may not match the current JS/HTML after the fluency-tracker merge and the local-navigation refactor.

**Fix**: Regenerate or clearly mark it as a historical snapshot (not a live reference). Low urgency — it's documentation of CT's development, not a source of truth.

### ~~P5 — Deprecated `apps/math_quiz/` cleanup~~ DONE

Deleted entirely in this PR. The old snake_case snapshot (82 files including session JSONs, compare_o1/, outdated code) was fully superseded by the new `apps/math-quiz/` import.

### P6 — No automated tests

No unit or integration tests exist for any of the JS or Python code. The functional test above is manual.

**Fix**: Add at minimum a smoke test for `math_quiz.py` and `math_analysis.py` (Python is easier to test). JS testing would require a test runner setup (not urgent for a local-first app).

