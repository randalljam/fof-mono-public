file: apps/math-quiz/2026-06-11_math-quiz-review.md
title: Math Quiz — Thorough Application Review
last-updated: 2026-06-11_2143
ai: Claude Code (cloud)
session: `MathQuiz thorough review`

> **Status update (2026-06-11):** the prioritized fixes P1–P8 below were implemented on this branch in stage-wise commits, with a Node unit-test suite (`tests/`, 32 tests) covering the fixed bugs. This document is otherwise preserved as the point-in-time review.

## TLDR
The app does its core job — addition-fluency practice and review for a kid, with a genuinely useful quiz → analysis → fluency-tracker → generated-problem-list loop — and CT's 2–3 months of feature work (flags, fluency tracker, manual overrides, problem-list generator, duplicate aggregation) added real capability without breaking the core flow. But the review found one systemic correctness problem and a cluster of real bugs, all currently masked because actual usage has been addition-only:

1. **Multiplication and division are silently broken end-to-end.** Recorded `problem_text` stores display symbols (`&times;`, `×`, `÷`) while every downstream parser expects raw `*`/`/`. Multiplication never appears in the fluency tracker (its whole multiplication section can never populate from quiz data), and the analysis operation filters for `*`, `/`, and `muldiv` match nothing.
2. **Subtraction is silently dropped from the analysis heatmap** — the aggregation key uses `-` as its delimiter, which collides with the subtraction operator.
3. **Editing flags while the list is sorted saves the flags to the wrong problem** (sorted index used against the unsorted array).
4. **Re-importing a session that's already loaded duplicates its attempts in the database** — and re-uploading an exported `_MODIFIED` file makes the duplication permanent (both copies live in localStorage and both import on every page load).
5. **"Export Modified Session" silently degrades the stored session JSON** (drops note, include/exclude lists, preset, and other settings when it overwrites the original in localStorage).
6. Several smaller bugs: the "Sessions for Permanent" UI control has no effect, `submitAnswer` has no re-entry guard (the likely cause of the long-reported "two questions in a row" bug), and a possible NaN problem when `numbers_include` is set with an empty range pool.

Beyond bugs: there are **zero automated tests** (now mandatory pre-PR in this repo), the two Python files are legacy/broken (`math_quiz.py` imports a nonexistent `primary.fileops`), and the checked-in code-review docs — while a genuinely good practice — contain **false assurances** ("all queries parameterized", "no XSS", invented benchmark numbers, "Ready for merge") that the code contradicts. Detailed findings and a prioritized fix list below.


## Scope and method
- **Reviewed:** all source in `apps/math-quiz/` — `math_quiz.js` (1.9k lines), `math_fluency.js` (1.4k), `math_analysis.js` (1.4k), `math_utils.js`, both Python files, the three HTML pages, CSS, and all eight `code_review_*.md` docs plus `PLAN_math_quiz.md` and `README.md`.
- **PR history:** the junior-dev PRs live in the external `math-quiz` repo (47 commits; contributors CT, Randy True), which is not in this session's GitHub scope. The only fof-mono PR touching this app is #7 (the 2026-06-04 import). CT's PR work was therefore reviewed through the eight preserved `code_review_*.md` documents, cross-checked line-by-line against the current code.
- **Architecture recap:** three standalone HTML pages sharing `math_utils.js`. Sessions are JSON blobs in `localStorage` (per browser origin), imported on each page load into an in-memory sql.js database; the analysis and fluency pages render with Plotly. No backend; production deploys by pasting code into Webflow custom-code blocks.


## High-priority bugs (correctness)

### 1. Operation-symbol mismatch breaks multiplication and division everywhere downstream
`generateProblem` stores `problem_text` as the display string: `"5 &times; 3"`, `"5 &divide; 3"` (`math_quiz.js:1012-1015`). Problems replayed from fluency-generated lists store the unicode form `"5 × 3"` (`math_fluency.js:948-950`), and the Python CLI also writes `×`/`÷` (`math_quiz.py:133`). But `parseProblemText` (`math_utils.js:119`) just splits on spaces and returns the middle token verbatim, so the stored/parsed operation is `&times;` or `×` — never `*`:
- **Fluency tracker:** `prepareFluencyDatasets` keeps only operations in `['+', '-', '*']` (`math_fluency.js:298,347`), so every multiplication attempt is discarded. The multiplication section can never show data from quiz sessions, and practicing a generated multiplication list never feeds back into the tracker — the feedback loop the generator exists for is broken for its hardest operation.
- **Analysis:** the operation filter compares the parsed operation to `*`, `/`, `muldiv` (`math_analysis.js:992-1002`) — matches nothing. (Multiplication cells do appear under "all" since the entity string survives that path.)
**Fix direction:** normalize at write time — store canonical `"5 * 3"` in `problem_text` (or add explicit `num1`/`num2`/`operation` fields to the session JSON, which the DB schema already has columns for) and keep display conversion purely presentational. Add a normalization shim in `parseProblemText` (`&times;`/`×` → `*`, `&divide;`/`÷` → `/`) so existing session files still parse.

### 2. Subtraction silently missing from the analysis heatmap
`processData` groups attempts under the key `` `${num1}-${operation}-${num2}` `` and later splits on `-` (`math_analysis.js:1069,1078`). For `"5 - 3"` the key is `5---3`, which splits into `['5','','','3']` — operation and num2 come back empty/NaN, the grid-bounds check fails, and the cell is never populated. Every subtraction attempt vanishes from the heatmap (negative numbers break the same way). The fluency code does this correctly with a `|` delimiter (`getCanonicalProblemKey`, `math_fluency.js:150-153`); the analysis page should use the same.

### 3. Flag edits save to the wrong problem when the list is sorted
`renderProblemList` renders from the **sorted** copy and wires `saveProblemFlags(this, ${index})` with the sorted index (`math_analysis.js:396,453`), but `saveProblemFlags` indexes into the **unsorted** `window.currentFilteredProblems` (`math_analysis.js:498`). With any sort mode other than "Order", the edited flags — including the DB `UPDATE` — are applied to a different attempt than the one displayed. Ironic detail: sorting and inline flag editing shipped in the same PR (`code_review_flag_features_completion.md`), and the review marked both "tested" without catching the interaction. Fix: carry the problem identity on the DOM (`data-problem-index` already exists on the row, holding the sorted index — store the original index or session_id+ROWID instead).

### 4. Session re-import duplicates ProblemAttempts rows
`ProblemAttempts` has an autoincrement PK and no unique constraint, so `INSERT OR IGNORE` never ignores (`math_utils.js:88-104,183-201`). `loadSessionFiles` both imports an uploaded file into the live DB and writes it to localStorage under the file's name (`math_utils.js:308-309`). Consequences:
- Uploading a file for a session already loaded from localStorage doubles its attempts immediately (Sessions dedupes by PK; attempts don't).
- Re-uploading the `_MODIFIED.json` produced by "Export Modified Session" leaves **two** localStorage entries with the same `session_id`, so every subsequent page load imports the attempts twice — permanently skewed counts, averages, and fluency windows.
Fix: before inserting attempts, check whether the `session_id` already exists in `Sessions` and skip (the session row insert's changes count tells you), and/or replace rather than add when re-importing a modified session.

### 5. "Export Modified Session" rewrites the saved session lossily
`exportModifiedSession` rebuilds the session JSON from DB columns and **overwrites the original localStorage entry** (`math_analysis.js:594-619`). The rebuilt `settings` keeps only `num_problems`, `number_range`, `operations` — the note, `numbers_include`/`numbers_exclude`, `num_numbers`, preset name, problem-list metadata, and `summary.total_test_time` are all silently dropped from the stored copy. It also re-runs the flags `UPDATE` per problem redundantly, and interpolates `sessionSelection` into SQL strings. Fix: load the original JSON from localStorage, patch only the `flags` arrays, and write it back.

### 6. "Sessions for Permanent" control does nothing
`getFluencySettings` reads `fluency-permanent-sessions` (`math_fluency.js:574`), but `refreshFluencySection` builds the thresholds object without `permanentSessions` (`math_fluency.js:806-812`), so `prepareFluencyDatasets` always falls back to the default of 5 (`math_fluency.js:420`). The input is also missing from the change-listener list (`math_fluency.js:832`). Two-line fix.

### 7. No re-entry guard on submitAnswer — the old "two questions in a row" bug
`submitAnswer` can be invoked from four paths: Enter key, auto-submit-on-length, the flag-comment Enter handler, and speech recognition. Speech recognition runs with `continuous = true` and `handleUserAnswer` neither checks whether the current problem was already answered nor stops listening before submitting (`math_quiz.js:215-219,1722-1730`), so a second recognition result (or speech arriving right after a typed answer) submits again: `problemIndex` advances twice, a duplicate/garbage record is pushed, and a problem is skipped. This matches the unresolved PLAN items "Fix intermittent bug where it does multiple questions in a row" and Kid1's "Fix issue with getting two questions in a row". Fix: a `submissionInFlight`/answered-this-problem guard at the top of `submitAnswer`, cleared in `nextProblem`, plus `stopListening()` on submit.

### 8. Problem generation edge case: NaN problems
In `generateProblem`, if the range/exclusions leave `availableNumbers` empty but `numbers_include` is non-empty, the guard passes and the fill loop pushes `randomChoice([])` → `undefined`, producing problems like `"7 + undefined"` with a NaN answer (`math_quiz.js:983-997`). Also `num_numbers > 2` is accepted by the UI but the problem string only ever uses `numbers[0]` and `numbers[1]`.


## Medium issues

- **Auto-submit-on-length breaks non-integer answers.** The digit-count comparison uses `Math.abs(Math.round(correctAnswer))` (`math_quiz.js:1837-1846`), so for division answers like `2.5` it auto-submits after one digit. With auto-submit on (the default), division problems are effectively unanswerable. Negative answers similarly never match cleanly.
- **Documented "combined fluency rules" no longer exist.** `code_review_fluency_tracker_refactor.md` describes rules (yellow + green → stay yellow; green → red → `flagged` regression status), but the current code is simply "use latest session if it has data, else historical" (`math_fluency.js:514-525`). The `flagged` color constant survives as dead code. Either the rules were intentionally simplified (then the docs should say so) or they were lost in the refactor.
- **Manual-override username semantics are confusing.** Overrides saved while viewing "All Users" go under a synthetic `default` user (`math_fluency.js:485,1295`), invisible when a real user is selected, and vice versa. `clearAllOverrides` says "for all users" but clears only `default`. For a multi-child household this will produce mysterious stars.
- **Problem-list generator remainder can flood excluded categories.** Leftover slots are given to the category with the most available problems even when the coach set it to 0% (`math_fluency.js:1019-1030`) — a request for 100% red problems can come back padded with blues/greens.
- **HTML injection via interpolated strings.** Usernames, flag notes, override reasons, and session notes are interpolated into `innerHTML`/attribute values unescaped (e.g. `math_quiz.js:281,938`, `math_analysis.js:403,452`, `math_fluency.js:1259`). Single-user local app, so the practical risk is broken UI (a name or note containing `"` or `<` mangles the page), but it contradicts the review docs' "no XSS" claims and is cheap to fix with one escape helper.
- **SQL built by string interpolation in `math_analysis.js`** (`queryDatabase`, `populateSessionDropdown`, `exportModifiedSession`) — a username like `O'Brien` throws a syntax error. The fluency page was fixed to use bound parameters after its review; the analysis page never got the same fix.
- **No localStorage quota handling.** `saveSessionData`, override saves, and uploaded-file caching all call `setItem` without try/catch; a full quota throws and loses the just-finished session. Worth a guard with a "download it manually" fallback given sessions auto-save here.
- **"Previous" fluency dataset includes the current session.** `previousMetrics` is computed over all attempts including the latest session (`math_fluency.js:453`), so the "Previous" map isn't strictly prior history. Minor semantic point, worth a deliberate decision.
- **Misc cruft in `math_quiz.js`:** `promptDownload` is defined twice with identical bodies (lines 151 and 1478); SQL.js is initialized twice on the analysis/fluency pages (test init + real init); `shuffleArray` uses the biased `sort(() => Math.random() - 0.5)` idiom; `window._dontKnowFlag` and the `window.nextProblemTimeout` globals would be cleaner as module state.


## Python files (legacy)
- `math_quiz.py` — the CLI/pygame predecessor. `run_assessment` imports `primary.fileops` (`math_quiz.py:179`), a module path from the old corpus-tools layout that doesn't exist in fof-mono (`core/fileops.py` now), so it crashes on use. `record_audio` is a placeholder returning a random int; the pygame `main()` writes epoch floats where the JSON format elsewhere uses formatted strings, and divides by zero on an empty session.
- `math_analysis.py` — the import half works, but everything below "OLD CODE" references a schema that doesn't exist (`Users.grade`, `user_id`, a `Problems` table) and `run_interface` uses `tk`/`ttk` without importing tkinter.
**Recommendation:** either fix the import path and prune the dead halves, or move both files to a clearly-labeled legacy status and note in the README that the web app is the only maintained surface. Right now they look like working components.


## Repo hygiene and docs
- **Stale README:** says the deprecated snapshot lives at `apps/math_quiz/` (it no longer exists in the repo) and that session data is stored in S3 — but there is no `apps_math-quiz` manifest in `plans/2026-04-09_repos-reorg/s3_manifests/`, and PR #7 explicitly deferred the S3 upload. The README states the intended end state as current fact.
- **Unused vendored sql-wasm:** `sql-wasm.js`/`sql-wasm.wasm` are checked in but every page loads sql.js from cdnjs; the only local reference is a commented-out PHP line (`math_analysis.html:625`). Decide: use the vendored copy (better for offline/file:// use) or delete it.
- **`addCacheBuster` defeats CDN caching** on sql-wasm (~1 MB) and is applied on every load (`math_utils.js:35-37`, used in both dashboards) — every page open re-downloads the wasm. Cache-busting was for dev iteration; pin versions instead. Relatedly, `plotly-latest.min.js` is an unpinned moving target.
- **Stale file variants:** `math_quiz_0626.css` and `math_quiz_0653.css` are same-day iterations of `math_quiz.css` (git history makes these unnecessary); `combined_math_quiz.md` is a 2.4k-line concatenated snapshot from October that has drifted from the real files. All three should go or be regenerated on demand.
- **No tests.** The repo's pre-PR testing rule now requires them. This codebase has unusually testable pure functions: `parseProblemText`, `buildProblemFromExpression`, `evaluateFluencyStatus`, `checkPermanentStatus`, `computeMedian`, `parseSessionTimestamp`, `convertSpelledOutNumberToNumeral`, `sortProblems`, `calculateAggregatedTime`, `generateProblemListFromFluency`. A small Node test harness (the functions have no DOM dependencies) would have caught findings 1, 2, and 6 outright.


## Review of the PR / code-review process
The eight `code_review_*.md` docs are a real asset — they preserve intent, root-cause analyses, and decision history that would otherwise have been lost with the external repo. The loop also demonstrably worked in places: the two blocking findings in `CODE_REVIEW.md` (division-by-zero replay, string answers) are fixed in the current `buildProblemFromSessionEntry`; the Plotly-resize fallback suggested in `code_review_flag_filter_2.md` was implemented; "Export Modified Session" was suggested and later built; an SQL-injection finding got the fluency page parameterized.

That said, clear patterns to correct going forward:
1. **Confidence inflation over time.** Early reviews are short and find blocking bugs. Later ones balloon into 700-line documents with "Testing Performed" checklists, estimated "benchmarks", security sections, and "✅ Ready for merge" verdicts — written by the same AI that wrote the code. Several assurances are demonstrably false against the code as merged: "No SQL injection: all queries parameterized" (analysis page isn't), "No XSS: all user input validated and sanitized" (nothing is escaped), "Tested with different operations (addition, subtraction, multiplication)" (multiplication cannot work — finding 1). The verbosity actively buried the misses.
2. **Reviews validated features in isolation, not interactions.** The sort×flag-edit bug (finding 3) and the export×re-import duplication (finding 4) are both interactions of features that were individually reviewed as working.
3. **Suggested tests were never written.** `code_review_fluency_tracking.md` proposed `tests/fluencyStatus.test.js` in its next steps; no test was ever added, and nothing enforced it.
**Process recommendations:** keep the review docs but make them adversarial — require each review to state what was *not* tested, ban unverifiable claims (benchmarks, blanket security sign-offs), and have a different model/agent review than the one that wrote the code. Convert at least the "Testing Performed" checklists into actual automated tests. The repo's new pre-PR testing rule covers the enforcement gap.


## Prioritized recommendations
1. **P1 — Normalize operation symbols** in recorded `problem_text` (+ parse-time shim for old data). Unblocks multiplication/division in the fluency tracker and analysis filters. (Finding 1)
2. **P2 — Fix the analysis aggregation key delimiter** (`|` instead of `-`) so subtraction appears in the heatmap. (Finding 2)
3. **P3 — Fix flag-edit indexing under sort**, and **dedupe session imports** (skip attempts when session_id already imported). These two corrupt data the coach believes she's curating. (Findings 3, 4)
4. **P4 — Make "Export Modified Session" patch-not-rebuild** the stored JSON. (Finding 5)
5. **P5 — Add a submit re-entry guard** + stop listening on submit; likely closes the oldest open bug in the PLAN. (Finding 7)
6. **P6 — Small fixes batch:** wire `permanentSessions` through thresholds; guard `generateProblem`'s empty-pool case; parameterize the remaining SQL; one HTML-escape helper applied at the interpolation sites; localStorage setItem guards.
7. **P7 — Test harness:** Node-based unit tests for the pure functions listed above; add a `## Tests` section to a per-app `AGENTS.md`.
8. **P8 — Hygiene:** update README (no S3 yet, no `apps/math_quiz/`, Python files legacy); delete or regenerate `math_quiz_0626.css`, `math_quiz_0653.css`, `combined_math_quiz.md`; decide vendored-vs-CDN sql.js; pin CDN versions and drop the cache-buster; fix or retire the Python files.
