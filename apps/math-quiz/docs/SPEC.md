file: apps/math-quiz/docs/SPEC.md
title: Math Quiz — Integrated Specification (canonical, living)
last-updated: 2026-06-16_0844
ai: Claude Code (cloud) — Opus
session: `math quiz goal`


## Purpose of this document (read first)
This is the **single, canonical, living specification** for the entire math-quiz application — the
integration of all work to date (Randy's original quiz, CT/CT's fluency + analysis + flags, and
the recent assess/practice + anchor + SQLite direction). It describes **what the app is and why** —
definitions, design principles, data model, and behavior contracts that should stay true over time.

**What goes here (SPEC):** durable definitions and decisions — the fluency rubric, the
accuracy-vs-fluency principle, the fact/segmentation model, modes, mastery, storage model, modality,
data policy. If it's a "what is true / what must hold" statement, it belongs here.

**What goes in `PLAN.md` instead:** sequenced, status-tracked **work items** — phases, tasks, tests,
and the decision log with dates. If it's a "do this next / in this order / done?" statement, it
belongs in the plan.

**Relationship to the dated docs:** the dated design docs in this folder
(`2026-06-14_adaptive-and-profiles-goal.md`, `2026-06-15_assess-practice-modes-spec-and-plan.md`,
`2026-06-15_guinea-pig-findings.md`, `2026-06-11_math-quiz-review.md`,
`single_digit_addition_segmentation.md`) are **historical sources** — point-in-time captures kept for
provenance. This SPEC distills and supersedes their "what is true" content; when they conflict, this
SPEC wins. Keep `last-updated` current when you materially edit.


## 1. What the app is
A browser-based tool that (a) **assesses** a learner's per-fact arithmetic fluency and (b) **delivers
targeted practice** at that state. Vanilla HTML/CSS/JS, no build step. Runs locally on a laptop,
phone, or tablet over local Wi-Fi; production surface is Webflow custom-code blocks.

Three legacy surfaces fold into one integrated product:
- **Quiz** (`math_quiz.html`) — collects attempts (problem, answer, correctness, response time, flags).
- **Fluency tracker** (`math_fluency.html`) — per-fact status with manual overrides.
- **Analysis** (`math_analysis.html`) — response-time heatmap, per-problem drill-down, flag review.
Plus the recent **anchor** surface (`anchor.html`) — keypad-first fast-fluency demonstration — and the
DOM-free **engine** (`engine/`, `simulation/`) that will power adaptive selection across all of it.


## 2. Core principle: fluency ≠ accuracy
This is the most important design decision and must hold everywhere.
- **Accuracy** = is the answer correct? (correct / not).
- **Fluency** = the answer is **correct AND immediate AND effortless** — retrieved cold, with **no
  cognitive load** and **no intermediate strategy** (e.g. a fluent solver does *not* compute `8 × 6`
  as `8 × 5 + 8`; they just know it). The best behavioral proxy is **immediacy** (low response time).
- **Accuracy is table stakes, not the headline metric.** The goal is to move learners *past* "gets
  them all correct" to "knows them cold." So the app's primary signal is **automaticity (speed)**, with
  accuracy as the **floor** of the rubric, not the target.
- **The app is not designed around accuracy.** A high-level design rule: **auto-submit accepts an
  answer only once the typed value equals the correct answer's digit count and (on auto-accept) is
  correct** — so the entry mechanism itself is oriented around fluent, correct entry, not around
  catching wrong answers. Wrong/early entries are still **labeled** (we keep the apparatus to back
  into accuracy when a learner is genuinely missing facts), but accuracy is not what the product
  optimizes.


## 3. The fluency rubric: red → yellow → green → blue
A stoplight-plus rubric, the canonical scale for fluency. It applies at **three levels** (see §4).

| Status | Meaning | Behavioral signature |
|---|---|---|
| **red** | Really doesn't know it. | Makes errors, or so effortful/slow it's effectively not known. **Accuracy floor:** below the accuracy threshold ⇒ red regardless of speed. |
| **yellow** | Kind of knows it — **not fluent**. | Accurate on nearly all (only the odd slip / fat-finger), but slow/effortful; may use intermediate strategies; may forget sometimes. **Definitely needs practice.** |
| **green** | **Fluent or near-fluent**, but not yet enough data to call it permanent. | Fast + correct recently; worth following up — collect more data, keep practicing toward blue. |
| **blue** | **Permanent — "in ice."** Known cold; very unlikely to be lost. | Green sustained across enough sessions that we classify it solid. (Doesn't mean they can *never* answer it >2 s once — only that we've concluded they know it cold.) |
| *nodata* | Not yet observed. | No attempts in scope — distinct from red. |

Notes:
- The **red↔yellow boundary is accuracy** ("makes errors" vs "accurate but slow"). The
  **yellow↔green↔blue gradient is automaticity** (speed + durability).
- **Thresholds are adjustable and level-appropriate**, not a single fixed 2 s rule. 2 s is a relevant
  default for adults; developing learners warrant a higher "fast" bar (e.g. ~3.5–4 s) — set per
  learner/level (see the G1/G2 finding in §10).
- **Code reconciliation (for PLAN):** the current `evaluateFluencyStatus` emits
  `nodata / gray / red / yellow / green / blue`, where `gray` = low accuracy and `red` = very slow
  (median ≥ `redMs`). The canonical rubric folds **low-accuracy (`gray`) into red** and treats the
  red/yellow/green/blue gradient by the meanings above. Aligning the code's status names/semantics and
  making `greenMs`/`redMs`/`minAccuracy` level-configurable is a PLAN task (Phase A), not a change of
  this definition.


## 4. Three levels of evaluation
The same rubric is computed and reported at three granularities, per operation:
1. **Operation** — e.g. all single-digit addition, or all single-digit multiplication.
2. **Category within an operation** — the segmentation buckets (§5): Add-Zero, Add-One, Add-Two,
   Doubles, Tough-21, Sneaky-Six (and the eventual ×/− equivalents).
3. **Individual problem** — a single fact (e.g. `8 × 6`), with its full **longitudinal history** across
   sessions (every attempt: time, correctness, flags).
Aggregate statistics roll **up** (problem → category → operation) and the UI must let an operator
**drill down** the same path, with **filters** by flag and by recency / date / session range.


## 5. The fact model
- **Operations in scope:** `+`, `−`, `×` (division/exponent deferred).
- **Fact key:** `(operation, num1, num2)`, order significant; canonical `problem_text` is
  `5 + 3` / `5 * 3` (display symbols `×` `÷` are presentation-only).
- **Single-digit addition segmentation** (source: `single_digit_addition_segmentation.md` →
  `engine/addition_segmentation.mjs`) — 55 unique facts (each commutative pair counted once) partition
  into five non-overlapping categories by the smaller addend, plus a named hard subset:

  | Category | Count | Pattern |
  |---|---:|---|
  | Add Zero | 10 | `n + 0` |
  | Add One | 9 | `n + 1` (from `1+1`) |
  | Add Two | 8 | `n + 2` (from `2+2`) |
  | Doubles | 7 | `n + n`, `3+3`…`9+9` |
  | Tough 21 | 21 | remaining non-doubles, addends 3–9 |
  | **Sneaky Six** | 6 | subset of Tough 21, both addends ≥ 6 (`7+6,8+6,9+6,8+7,9+7,9+8`) |

- **Orientation:** each fact has an *ascending* form (`3+4`) and a *complement* (`4+3`); doubles are
  symmetric.
- **Easy vs hard:** a fact is **hard** iff `max(num1, num2) ≥ 6`, else easy. The selector weights hard
  facts `3×`. The same segmentation approach is expected to be **reused for multiplication** (and an
  analogous one for subtraction).


## 6. Two modes: assess and practice
Mode is a **first-class, logged** flag (`ModeEvents`), not an implicit selector side effect.
- **assess** — form/revise the fluency estimate fast: broad, hard-weighted coverage; a curated,
  predetermined hard-first order; truncate when a conclusion fires.
- **practice** — deliver value once an estimate exists: **batches** (default 10) with a configurable
  **known:unknown mix** (default 50/50), reassessing between batches rather than per problem; concentrate
  on surfaced weak/slow facts.
- **Cold start** is assess with no prior.

**Glitch tolerance (assess):** we infer mental state from behavior. A single isolated slip never drops
the fluent hypothesis; only a confirmed cluster does. **Warm-up discard:** the first ~2 problems are
excluded (interface settling).

**Re-ask policy (assess) — see PLAN Phase B for specifics:** a **wrong/skipped** first attempt may be
re-delivered once to confirm vs. fat-finger; a **correct-but-slow** attempt is **not** re-asked in
assess (the slow time already *is* the automaticity signal) — speeding it up is a **practice** goal.
This keeps assess sessions ≈ one pass over the in-scope facts instead of ~2×.


## 7. Mastery determinations
- **Predictive (fast/short)** — infer mastery from a partial, hard-weighted sample (overall + hard-fact
  coverage gates, all sampled facts green, accuracy floor met). This is the anchor's "you look fluent —
  stop here or continue to 100%?" prompt.
- **Thorough (complete/certified)** — every in-scope fact attempted, correct, within the (adjustable)
  mastery time. Glitch-tolerant: a momentary slip is re-tried, not an automatic fail.

**Anchor use case:** a genuinely fluent person (adult *or* child) demonstrates full single-digit
fluency in ~2 minutes. Purpose: a fast new-user/demo path **and** a fast re-confirmation as learners
progress — applied to whole operations, to categories, and to individual problems. (This is *not* a
speed-competitor mode; the bar is "knows it cold," not "fastest possible.")


## 8. Storage model (canonical = per-user SQLite)

### 8a. File naming + local folders (anchor / `math-flu` files, updated 2026-06-25)
SQLite files use the **`math-flu`** prefix (the `anchor` name stays only on the HTML/JS files).
Per-person files live under local `_data/` source folders the user picks at run time — **`real`**
(real learner data), **`test`** (test trials), or a custom folder. In local worktrees `_data/`
is a symlink into `_LOCAL_FILES`, so every local worktree sees the same learner files:
- **Single-session file** (a brand-new file with exactly one session):
  `math-flu_<name>_<YYYY-MM-DD>_<HHMMSS>.sqlite` — date **and** time.
- **Multi-session file** (a file that has had a second session appended): the **time is dropped**;
  it keeps the **date of the initial session**: `math-flu_<name>_<YYYY-MM-DD>[_<suffix>].sqlite`.
  An optional free-text `_<suffix>` after the date is **allowed** on multi-session files (reserved
  provision — e.g. a label).
- **Append rule:** adding a session to a single-session file renames it to the multi-session form
  (drop the time, keep the date). Adding to an already-multi-session file **keeps the target's
  existing filename** (handles programmatic combines where the new session's time may precede the
  file's date). The lookup picks the **most recent** matching file by the date in its name.
- **`test` destination runs** are organized into a dated subfolder `test_<YYYY-MM-DD>_<HHMMSS>[_<desc>]/`
  (the short test description is appended to the folder name); the run is seeded from the selected
  source folder's most-recent file for that person (see §8b).

### 8b. Continue / Start New + load-back (unified flow, decided 2026-06-20)
The anchor page and the dev server share one per-user lifecycle: pick a user, auto-load their
latest file, run, and save back — with an explicit restart path.
- **Source of truth = the local `_data/` per-person file** on the laptop running
  `tools/dev_server.py`. The browser's IndexedDB store is a **cache / working copy**, overwritten
  by the server file on load; the page only ever uploads the single finished session, so the two
  cannot diverge. Reads (list, latest, append target, seed) come from local `_data/`; **S3 stores
  immutable single-session archives and automatic append snapshots**, not the live working file.
  If the dev server is unreachable a run can still be taken and is filed on the next retry, and
  the page falls back to this device's cache.
- **Source folder + destination.** The page picks a **source folder** — a subfolder of `_data/`
  (`real`, `test`, or any custom folder the user created; listed via `GET /api/data-folders`) — and
  a **destination**: `source` accumulates the run into the source folder (the learner's growing
  file), or `test` writes a seeded trial into a dated `_data/test/test_<stamp>[_desc]/` subfolder
  **without touching the source**. Defaults: source `real`, destination `source`. The
  test-description field shows only when destination is `test`.
- **Continue latest (default).** On name entry (the Source folder selector sits directly under the
  name; the name field is a datalist of the known learners) the page GETs
  `/api/latest-user-db?folder=<source>&user=` and hydrates the cache with the returned file (showing
  the filename + session count). The server selects the lineage the learner **most recently added
  to** — by local file modification time, robust across same-day lineages whose multi-session names
  dropped their time — not merely the filename date (`anchor_store.pick_latest`). **Continue requires
  an existing source file**: with none, the page shows an error and blocks Start, and the server
  refuses the save (`ok:false, error:"no-continue-file"`) — the first file for a learner is the
  explicit **Start New**. A `test` destination under Continue seeds from that same latest file and
  appends, producing a multi-session trial (not a lone single-session file).
- **Start New.** A "Start new file" control sends `forceNew` on save; the server skips the
  latest-file lookup and writes a fresh single-session file (a new lineage). The first session's
  date is retained in the filename, so intentional restarts are supported.
- **Same-day lineages.** Repeated Start New + append on one day can produce several lineages
  sharing a date; the single→multi rename takes a `_2` / `_3` … suffix (the §8a suffix provision)
  so they never overwrite each other, and "Continue latest" follows recency to the right one
  (`anchor_store.next_multi_name`).
- The analysis page loads a `.sqlite` by manual pick and saves a person file with the same
  `math-flu_<name>_<date>` naming, preserving a loaded file's date so re-saving keeps the same
  filename. Shared client I/O (base64 ↔ bytes, the latest-DB load) lives in `engine/sqlite_io.mjs`.

### 8c. Automatic S3/local backups (updated 2026-06-25)
Local `_data/` is the working store. Every finished run is archived as one immutable single-session
file under `_data/_single-session-sqlite-files/` and best-effort uploaded to
`s3://[S3-BUCKET]/math-quiz/single-sessions/`. When a Continue append modifies an existing source
file, the dev server also copies the pre-change accumulated file to
`/Users/randytrue/Documents/Code/_BACKUP/math-quiz/sqlite-snapshots/`, then best-effort uploads
that snapshot to `s3://[S3-BUCKET]/math-quiz/_backup-s3/`. Start New creates a new accumulated file
and does not need a pre-change snapshot. S3 backup failure does **not** fail the local save; the UI
reports that the single-session archive or snapshot stayed local but S3 failed. The old manual
"Also upload to Amazon S3" live-file upload checkbox was removed.

### 8d. Ingesting drops from other apps (`math-quest`, decided 2026-06-20)
Other applications can deposit single-session `.sqlite` files into the shared drop folder
(`_data/_single-session-sqlite-files/`, the same folder the anchor archive uses) and have them
accumulated into per-person files exactly as a finished anchor run is — create / Continue-latest
append / single→multi rename — but **triggered out-of-band** rather than by the browser. The first
such producer is the **MathQuest** Minecraft mod (prefix **`math-quest`**).
- **General, prefix-parameterized core.** All of `anchor_store.py`'s naming/append helpers take a
  `prefix=` (default `math-flu`); `anchor_store.accumulate(dest_dir, name, stamp, src_path, prefix=…)`
  is the file-level create/append/rename used by both the dev server and the ingest tool.
- **Ingest tool: `tools/ingest_drop_folder.py`.** Scans the drop folder for files named
  `<SOURCE_PREFIX>_*.sqlite` (`SOURCE_PREFIX="math-quest"`; `""` matches **any** `.sqlite`), derives
  the learner + start timestamp from the filename (or, failing that, the file's `Sessions.user_name`
  / `start_time`), and accumulates each into `_data/<DEST_FOLDER>/` as
  `<OUTPUT_PREFIX>_<name>_<date>…sqlite`. The shared prefix means the tool ignores the anchor's own
  `math-flu_*` files sitting in the same folder.
- **Test-vs-live is one constant.** `DEST_FOLDER` defaults to `test` (`TEST_DEST`) for trials; flip it
  to `tlkids` (`LIVE_DEST`) — or pass `--dest tlkids` — to ingest real learner data. `--dry-run`
  previews; `--prefix`/`--output-prefix`/`--drop`/`--data-dir` override the constants.
- **Idempotent + non-destructive.** A per-`(output-prefix, destination)` JSON ledger
  (`_data/_ingest-ledgers/`) skips unchanged files on rerun; `append_session` dedups by `session_id`
  as the safety net (so `--force` reprocesses without duplicating). Source drops are **never moved or
  deleted**. Local dev only — never deployed.

### 8e. Internal problem lists — "Use internal" stored-list queue (decided 2026-06-21)
A learner's per-person file can carry **internal problem lists** (`ProblemLists` /
`ProblemListItems`, managed by `tools/problem_list_store.py`) that the anchor page runs directly
— a coach-authored queue of assignments stored *in the file itself*, distinct from the `.txt`
files under `problem-lists/`.
- **Ordering.** Each list has a `list_order` indexed **1..N, contiguous, no gaps**, defining the
  run order. "Use internal" runs the **top of the queue** (lowest `list_order`), one list per quiz.
- **retain (default keep).** New schema columns on `ProblemLists`: `retain` (default `1` = keep),
  `times_used`, `last_used_at`. When a run that used a list is **filed to the source folder**, the
  server **consumes** it: `retain=1` → bump `times_used`/`last_used_at` and keep it; `retain=0` →
  delete it (and its items) and **reindex** the rest back to a contiguous 1..N — so it pops off the
  queue and the next list moves to the top. A consumed run leaves a normal session behind (the
  problems were answered), so the work is preserved as data even when the list is removed.
- **Trigger + scope.** Consumption happens only when the run is filed to **destination `source`**
  (a full finish *or* a partial Quit & Save); **Quit & Abandon** files nothing and consumes
  nothing, and a **test-destination** trial never mutates the source file's lists.
- **Flow.** On Continue-latest load, `GET /api/latest-user-db` returns the learner's
  `problemLists` (ordered, with `retain`/`times_used` and each item's `num1/operation/num2`); the
  page shows them in a box (top flagged "runs next") and enables a **"Use internal"** problem
  source. Start runs the top list (shared expander `engine/problem_list.mjs`) and sends
  `consumedProblemListId`; `POST /api/save-run` pops it after appending. With no internal lists the
  option is disabled and Start is blocked with a clear message. Manage lists with
  `tools/problem_list_store.py` (`add-from-txt --consume`, `set-retain`, `reindex`, `consume`,
  `show`).

### 8f. Problem-list editor — manual editing + generator (decided 2026-06-21)
A shared, collapsible **problem-list editor** lives on both the anchor and analysis pages
(`engine/problem_list_panel.mjs`), for manually authoring the internal lists "Use internal" runs.
- **Server-authoritative, keyed by folder+user.** All edits go through the dev server
  (`GET /api/problem-lists?folder=&user=` to read; `POST /api/problem-lists {action,…}` to mutate),
  operating on that learner's **latest per-person file** — the same file the quiz appends to and
  "Use internal" runs, so there is one source of truth and no divergence. Needs the dev server
  running; on the analysis page that means opening via **Load for analysis** (`?folder=&user=`).
- **Layout + auto-save.** Lists render as **cards left-to-right in queue order** (lowest
  `list_order` first), each an editable textarea (one `a + b` per line) plus rename, retain toggle,
  **◀ ▶ reorder**, and delete. Edits **auto-save**: the textarea is debounced (~0.7s) and flushed on
  blur (`save-items`, lenient — blank clears, an unparseable line is rejected with the file
  unchanged); rename/retain/reorder/create/delete save immediately. Reorder + delete re-index the
  queue to a contiguous 1..N (§8e).
- **Generator.** A "Generate" tool builds a new list from a **problem count + a per-category
  percentage mix** (`engine/list_generator.mjs`: Add 0/1/2, Doubles, Tough rest, Hardest 6 — the
  six buckets partition the 55 unique 0–9 facts), then saves it as a new list (`create`).
- **Store CRUD** backing the actions: `replace_list_items`, `rename_list`, `reorder_lists`,
  `delete_list` (unconditional, ignores retain), `create_list` (allows an empty card) in
  `tools/problem_list_store.py`. Editing requires an existing file (created by a quiz / Start New).

### Tables + persistence
- **Canonical store: one SQLite database per learner.** Tables: `Users`, `Sessions`,
  `ProblemAttempts` (every trial: operands, answer, correctness, `response_time_ms`, flags, mode,
  timestamp), `WarmupAttempts`, `ModeEvents`. Computed **in-memory** (sql.js) for speed; auto-persisted
  to **IndexedDB** keyed by username; manual `.sqlite` export/import as the cross-device escape hatch.
- **Evaluation is not persisted** — fluency/rubric status is **recomputed** from raw attempts, so the
  algorithm/thresholds can change and old captures re-score (`engine/reevaluate.mjs`, static re-eval).
- **Per-run capture files** (`anchor_<name>_<timestamp>.sqlite`) are **immutable capture / transport
  artifacts** (one trial), distinct from the canonical per-user DB. They merge into the per-user DB via
  `tools/combine_sqlite.py`. Canonical workflow: **capture → combine → re-evaluate**.
- **JSON is retired as the math-quiz store (Q3).** The old session-JSON path (`localStorage` +
  download) is replaced by the SQLite store for this app. JSON is **retained only as an interchange
  format** for other producers of the same shape (the Minecraft mod, future games), gated by the
  write-mode switch (`sqlite-only` dev default | `json+sqlite` | `json-only`). An importer ingests
  legacy session JSON into the per-user DB so history is not lost.


## 9. Modality (Q4 — to be captured)
Record, per session (and where relevant per attempt), a structured **modality** record so
presentation/input trade-offs can be analyzed from data:
- **device** (e.g. iPad / iPhone / laptop), **presentation** (read-aloud TTS on/off),
  **input method** (on-screen keypad / physical keyboard / mouse / ASR), **keypad mode** (standard /
  big-number keys), **auto-submit** on/off.
- **Direction:** touchscreen + on-screen keypad for real learners — it isolates *knowledge* from
  mouse/keyboard dexterity and is far easier for a child than typing. (Deferred idea: record session
  audio synchronized to the problem timeline for glitch-vs-real annotation.)


## 10. Real-learner calibration (G1, G2)
The first two real-kid runs are canonical evidence behind the rubric/threshold rules:
- Both are **highly accurate but not sub-2 s** (G1 96% correct addition; G2 99% correct
  multiplication) — they *know* the facts but answer in ~2.5–4 s. At a fixed 2 s bar they are
  mislabeled "not fluent" almost everywhere; at ~4 s they look 57% / 71% fast.
- Confirms: accuracy and automaticity are different (the rubric encodes this — they're **yellow/green**,
  not red); thresholds must be **level-appropriate**; non-addition operations need **curated plans**
  (G2's multiplication ran the full 55-fact marathon for lack of one). G1/G2 become **simulation
  profiles** and regression cases.


## 11. Data / repository policy (Q5)
- **The repo stores source code, not data.** Real learner captures (JSON/SQLite) are **never** committed
  while they're throwaway trials; they live locally and in S3 (`[S3-BUCKET]` — PII bucket).
- **Only a few small, anonymized, canonical fixtures** may be committed — as named test cases (e.g.
  G1/G2-derived, ~tens of KB each), kept under a dedicated fixtures path and capped in number. The goal
  is to generalize to representative fixtures so agents rarely need real captures.
- **Cloud-agent S3 access** (when real captures *are* needed) is an infra capability with two
  independent requirements — credentials **and** network egress — specified as a task in PLAN Phase G.


## 12. Testing posture
DOM-free engine code in `engine/` / `simulation/`; tests in `tests/`; real browser functions exercised
in a Node vm via `tests/load_app.mjs`; deterministic seeds. E2E via Playwright (hermetic — CDN libs
served from `tests/node_modules`). No criterion or existing test is weakened to pass. A change is "done"
only when `cd apps/math-quiz/tests && npm run test:all` exits 0 with its new tests included.
