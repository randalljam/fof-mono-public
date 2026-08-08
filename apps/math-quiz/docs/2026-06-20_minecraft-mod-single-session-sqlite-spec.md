file: apps/math-quiz/docs/2026-06-20_minecraft-mod-single-session-sqlite-spec.md
title: MathQuest — single-session SQLite export spec
last-updated: 2026-06-20_1430
ai: Cursor - Composer 2.5 Fast
session: `Minecraft mod SQLite session spec`

Specification for the **MathQuest** Minecraft mod (`apps/minecraft/mods/mathquest/`) to replace its legacy **session JSON** export with a **single-session SQLite file** that the math-quiz app can load, analyze, and merge. This is the interchange contract between MathQuest and math-quiz — not an implementation plan for either side.


## Summary

- **Today:** MathQuest writes `math_session_{uuid}_{username}_{timestamp}.json` via `SessionExporter.java`.
- **Target:** MathQuest writes one **SQLite database file per completed quiz**, containing **exactly one session** (one `Sessions` row and its `ProblemAttempts` rows).
- **Math-quiz intake folder:** copy or sync finished files into
  `apps/math-quiz/_data/_single-session-sqlite-files/`
  (gitignored; created automatically by `tools/dev_server.py` when the anchor page saves a run).
- **Schema source of truth:** `createTables()` in `math_utils.js` and live files under `apps/math-quiz/_data/`. The analysis page, fluency engine, and `tools/combine_sqlite.py` all read this shape.
- **JSON is retired for MathQuest** as the primary export format. The canonical session-JSON shape remains documented here only as a mental model for row mapping; MathQuest should write SQLite directly.


## File naming

Use the same **date + time stamp** convention as the anchor page (`docs/SPEC.md` §8a), with a **MathQuest-specific prefix** so producer and filename parsing stay unambiguous:

```
mathquest_<username>_<YYYY-MM-DD>_<HHMMSS>.sqlite
```

Rules:
- `<username>` — Minecraft **display name**, sanitized to `[a-zA-Z0-9_-]` (same rule as today's JSON exporter).
- `<YYYY-MM-DD>_<HHMMSS>` — session **start** time, local clock, 24-hour `HHMMSS` with no colon (e.g. `2026-06-20_143022`). Must match `Sessions.start_time`.
- One file = one quiz = one session. Do **not** append later sessions into the same file; each completed quiz gets a new file.
- Optional: embed the player UUID in `Sessions.numbers_include` or the settings note (see below) rather than in the filename. Filenames stay human-readable; UUID is metadata.

**Legacy JSON name (do not use for new work):**
`math_session_{player_uuid}_{username}_{timestamp}.json`


## Where files land

| Location | Role |
|----------|------|
| **Mod config dir** (`mathquest_sessions/` or `sharedDataDir`) | MathQuest writes the `.sqlite` file here when a quiz finishes (same place JSON went today). |
| **`apps/math-quiz/_data/_single-session-sqlite-files/`** | Math-quiz **archive of raw single-session captures**. Drop copies here for analysis or later merge into a learner's multi-session file. Not listed as a "source folder" on the anchor page — it is an intake / staging area. |
| **`apps/math-quiz/_data/<source-folder>/`** | Per-learner **accumulated** files (e.g. `tlkids/math-flu_K1_2026-06-17.sqlite`). Built by merging single-session files with `tools/combine_sqlite.py` or by the anchor dev-server append flow. |

MathQuest does not need to write directly into the monorepo path unless Randy configures `sharedDataDir` to point there. The contract is **file format + naming**; delivery can be manual copy, rsync, or a shared config directory.


## Database requirements

### Required tables

Each file MUST contain at minimum:

| Table | Rows per file |
|-------|----------------|
| `Users` | 1 — the player display name |
| `Sessions` | 1 — metadata for this quiz |
| `ProblemAttempts` | N — one row per problem, in presentation order |

Optional (omit if unused):
- `ModeEvents` — assess/practice transitions (MathQuest can log one row: `to_mode = 'assess'`, `trigger = 'mathquest-quiz'`).
- `WarmupAttempts` — keypad warm-up (not used in MathQuest today).

Do **not** add custom tables. `tools/combine_sqlite.py` ignores unknown tables but the live app expects the standard schema.

### DDL (reference)

Match `createTables()` in `math_utils.js`:

```sql
CREATE TABLE Users (
  name TEXT PRIMARY KEY
);

CREATE TABLE Sessions (
  session_id TEXT PRIMARY KEY,
  session_filename TEXT,
  user_name TEXT,
  start_time TEXT,
  end_time TEXT,
  num_problems INTEGER,
  number_range_start INTEGER,
  number_range_end INTEGER,
  numbers_include TEXT,
  numbers_exclude TEXT,
  num_numbers INTEGER,
  operations TEXT,
  total_problems INTEGER,
  correct_answers INTEGER,
  average_response_time_ms INTEGER,
  FOREIGN KEY (user_name) REFERENCES Users(name)
);

CREATE TABLE ProblemAttempts (
  attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT,
  problem_id TEXT,
  problem_text TEXT,
  num1 INTEGER,
  num2 INTEGER,
  operation TEXT,
  correct_answer REAL,
  user_answer_string TEXT,
  user_answer REAL,
  is_correct INTEGER,
  response_time_ms INTEGER,
  flags_json TEXT,
  presented_at TEXT,
  FOREIGN KEY (session_id) REFERENCES Sessions(session_id)
);
```

`presented_at` may be omitted from older anchor files; NULL is fine. New MathQuest exports should include the column (nullable) for forward compatibility.


## Row mapping (quiz → SQLite)

Map from the data MathQuest already collects in `SessionExporter.java` / `QuizManager`, aligned with the **canonical session-JSON shape** used by `importSessionData()` in `math_utils.js` (the web anchor page's `buildSessionJson()` is the reference producer).

### Users

| Column | Value |
|--------|-------|
| `name` | Minecraft display name (today's JSON `user.username` → canonical `user.name`) |

### Sessions

| Column | Value |
|--------|-------|
| `session_id` | New UUID string (same as today's `session.id`) |
| `session_filename` | The `.sqlite` filename being written (e.g. `mathquest_Steve_2026-06-20_143022.sqlite`) |
| `user_name` | Same as `Users.name` |
| `start_time` | Quiz start, `YYYY-MM-DD_HHMMSS` |
| `end_time` | Quiz end, same format |
| `num_problems` | Planned problem count (today's quiz size setting) |
| `number_range_start` | `0` for single-digit ops; set appropriately for larger ranges |
| `number_range_end` | `9` for single-digit addition/multiplication tables; match quiz config |
| `numbers_include` | JSON text array, usually `[]`. May hold metadata, e.g. `["player_uuid:550e8400-e29b-41d4-a716-446655440000"]` if you need the UUID queryable without a schema change |
| `numbers_exclude` | JSON text array, usually `[]` |
| `num_numbers` | `2` (two operands) |
| `operations` | JSON text array of canonical operator symbols: `["+"]`, `["-"]`, `["*"]`, `["/"]`, or `["^"]` for exponentiation. Map from quiz type: addition → `+`, subtraction → `-`, multiplication → `*`, division → `/`, exponentiation → `^`. |
| `total_problems` | Count of problems actually presented |
| `correct_answers` | Count where `is_correct = 1` |
| `average_response_time_ms` | Integer mean of `response_time_ms` over all problems (round to nearest ms) |

**Settings note (recommended):** the web app stores free-form session context in JSON at `session.settings.note`. SQLite has no `settings` column; encode producer metadata in a convention the analysis tools can grep:

- Store in a future optional column if added, **or**
- For now, rely on filename prefix `mathquest_` and optional UUID in `numbers_include`.

Canonical note string if you later add a `settings_json` column or ingest via JSON bridge:

```
source:mathquest-minecraft;application:MathQuest;operation:multiplication;player_uuid:<uuid>
```

### ProblemAttempts

One row per problem, **`attempt_id` ascending = presentation order** (important for combine / re-eval).

| Column | Value |
|--------|-------|
| `session_id` | Same UUID as `Sessions.session_id` |
| `problem_id` | Stable per-problem id within the session (today: 1-based integer as string, e.g. `"1"`, `"2"`) |
| `problem_text` | Canonical arithmetic text **without** `" = ?"`. Prefer ASCII operators: `5 + 3`, `7 * 8`, `12 / 3`. Multiplication: use `*` in storage if possible; the web app normalizes `x` / `×` on import, but `*` is canonical. |
| `num1`, `num2`, `operation` | Denormalized operands — **recommended** so analysis skips re-parsing. `operation` is one of `+`, `-`, `*`, `/`, `^`. |
| `correct_answer` | Numeric correct answer (REAL) |
| `user_answer_string` | What the player entered, as text; empty string if unanswered |
| `user_answer` | Parsed numeric answer, or SQL NULL if none |
| `is_correct` | `1` or `0` (SQLite integer, not boolean) |
| `response_time_ms` | Integer milliseconds from display to submit |
| `flags_json` | JSON text array of flag objects, or NULL. Empty quiz → NULL. Shape: `[{"reason":"…","label":"…","timestamp":"…","notes":"…"}]` |
| `presented_at` | ISO-8601 timestamp when the problem was shown, or NULL |

### ModeEvents (optional)

If written, one row is enough:

| Column | Value |
|--------|-------|
| `user_name` | Player name |
| `session_id` | Session UUID |
| `from_mode` | NULL |
| `to_mode` | `'assess'` |
| `trigger` | `'mathquest-quiz'` |
| `timestamp` | ISO-8601 at session start |


## Differences from today's MathQuest JSON

The current `SessionExporter.java` JSON does **not** match the canonical shape the web importer expects. When moving to SQLite, write rows that match the **canonical** layout (same as anchor), not the legacy JSON layout.

| Legacy JSON (MathQuest today) | Canonical / SQLite |
|------------------------------|-------------------|
| `user.username` | `Users.name` / `Sessions.user_name` |
| `session.operation` (string: `"addition"`) | `Sessions.operations` = JSON array of symbols, e.g. `["+"]` |
| `session.correct_count` | `Sessions.correct_answers` |
| `session.avg_response_time_ms` | `Sessions.average_response_time_ms` |
| `session.total_problems` | `Sessions.total_problems` **and** `Sessions.num_problems` |
| Flat session fields | Operand range + ops live in `Sessions` columns above |
| `problem_text` with ` x ` for multiply | Prefer `*`; `x` still parses |
| Top-level `application`, `version` | Not stored in SQLite; use filename prefix + optional note convention |

No `summary` or `settings` objects in SQLite — their fields are flattened into `Sessions` as listed.


## Single-session invariant

A file in `_single-session-sqlite-files/` MUST satisfy:

1. Exactly **one** row in `Sessions`.
2. Every `ProblemAttempts.session_id` equals that row's `session_id`.
3. Exactly **one** row in `Users`, and `Sessions.user_name` matches `Users.name`.
4. File is a valid SQLite 3 database (WAL mode optional; standard journal is fine).

The anchor dev server writes the same shape when it archives a finished run. `tools/anchor_store.append_session()` merges such files into a learner's multi-session file by `session_id` (skips duplicates).


## How math-quiz consumes these files

1. **Analysis page** (`math_analysis.html`) — "Load SQLite file" imports the file into an in-memory database for heatmaps, flags, and fluency re-evaluation.
2. **Combine tool** — merge one or more single-session files into a per-learner file:
   ```bash
   cd apps/math-quiz
   python3 tools/combine_sqlite.py multi \
     --target _data/tlkids/math-flu_Steve_2026-06-20.sqlite \
     --sources _data/_single-session-sqlite-files/mathquest_Steve_2026-06-20_090000.sqlite \
             _data/_single-session-sqlite-files/mathquest_Steve_2026-06-20_143022.sqlite
   ```
3. **Fluency** — computed at read time from `ProblemAttempts`; nothing extra is required in the export.

Evaluation (green/yellow/red status) is **never stored** in the file — only raw attempts. Changing rubric thresholds and re-running analysis stays valid.


## Java implementation notes (MathQuest)

- Use **SQLite JDBC** (already on the classpath for `QuizDatabase.java`) or the same driver the mod uses for `mathquest_data.db`.
- Create tables with the DDL above, then `INSERT` the session row and problem rows in one transaction; `commit` before closing.
- Write to a temp file in the same directory, then **atomic rename** to the final name so partial files never appear.
- **Singleplayer:** write locally under `mathquest_sessions/` (or `sharedDataDir`). **Multiplayer:** server writes after `QuizResultPayload` (same as JSON today); client does not write session SQLite in MP.
- Remove or gate the JSON export behind a legacy config flag once SQLite is verified.
- Update `SessionExporterTest.java` to assert SQLite schema + row counts instead of (or in addition to) JSON shape.
- Point code comments at this doc: `apps/math-quiz/docs/2026-06-20_minecraft-mod-single-session-sqlite-spec.md` (replaces the planned `docs/SESSION_FORMAT_SPEC.md` path referenced in `SessionExporter.java`).


## Validation checklist

Before treating an export as done, verify:

- [ ] File opens with `sqlite3` / DB Browser; three required tables present.
- [ ] `SELECT COUNT(*) FROM Sessions` → `1`.
- [ ] `SELECT COUNT(*) FROM ProblemAttempts` → matches quiz length.
- [ ] `Sessions.operations` parses as JSON array; symbols are `+ - * / ^` only.
- [ ] Sample row: `problem_text`, `num1`, `operation`, `num2`, `is_correct`, `response_time_ms` populated.
- [ ] Copy to `_data/_single-session-sqlite-files/` and load on the analysis page without errors.
- [ ] `combine_sqlite.py multi` merges into a tlkids file; session count increments by 1.


## Related docs

- `docs/SPEC.md` §8 — storage model, `math-flu_` naming, single- vs multi-session files.
- `docs/2026-06-15_assess-practice-modes-spec-and-plan.md` §7 — original JSON interchange decision (JSON now secondary).
- `math_utils.js` — `createTables()`, `importSessionData()`, `parseProblemText()`.
- `tools/anchor_store.py` — append + naming helpers used by `tools/dev_server.py`.
- `apps/minecraft/mods/mathquest/docs/OVERVIEW.md` — MathQuest persistence overview.
