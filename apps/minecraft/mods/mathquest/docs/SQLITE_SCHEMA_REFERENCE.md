file: apps/minecraft/mods/mathquest/docs/SQLITE_SCHEMA_REFERENCE.md
title: MathQuest and Math Quiz SQLite schema reference
last-updated: 2026-06-27
updated-by: Codex (GPT-5)

**MathQuest and Math Quiz SQLite schema reference**

## Purpose
This is the current schema reference for the SQLite files MathQuest reads and
writes while integrating with the Math Quiz app.

It covers:

- Standard Math Quiz-compatible arithmetic session tables.
- MathQuest single-session export files.
- Active multi-session learner files in `_data/tlkids`.
- Internal problem list and quick-practice tables read by MathQuest.
- Written-column MathQuest SQLite files.
- The append/ingest behavior that adds a MathQuest single-session file to an
  existing active learner file.

The companion current-state document is
`apps/minecraft/mods/mathquest/docs/PROBLEM_SOURCES_AND_SESSION_INTEGRATION.md`.

## File types
| File type | Filename pattern | Primary folder | Appended into active file? |
| --- | --- | --- | --- |
| Math Quiz active learner file | `math-flu_<real-name>_<YYYY-MM-DD>[_suffix].sqlite` | `apps/math-quiz/_data/tlkids` | This is the active file. |
| Math Quiz single-session capture | `math-flu_<real-name>_<YYYY-MM-DD>_<HHMMSS>.sqlite` | `apps/math-quiz/_data/_single-session-sqlite-files` | Yes, by Math Quiz dev server or shared ingest. |
| MathQuest standard arithmetic single-session export | `mathquest_<real-name>_<YYYY-MM-DD>_<HHMMSS>.sqlite` | `apps/math-quiz/_data/_single-session-sqlite-files` | Yes, by `session_ingest.py --match-any-prefix`. |
| MathQuest written-column export | `mathquest_written_column_<real-name>_<YYYY-MM-DD_HHMMSS>.sqlite` | `apps/math-quiz/_data/_single-session-sqlite-files` | No. Separate schema. |
| Legacy MathQuest local DB | `mathquest_data.db` | `sharedDataDir` or Fabric config dir | No. Local/server operational record only. |

## Standard arithmetic schema
This schema is the common shape used by:

- Math Quiz active learner files.
- Math Quiz single-session captures.
- MathQuest standard arithmetic single-session exports.

### `Users`
```sql
CREATE TABLE Users (
  name TEXT PRIMARY KEY
);
```

| Column | Type | Meaning |
| --- | --- | --- |
| `name` | `TEXT PRIMARY KEY` | Real learner name, such as `Randy`, `K2`, or `Kid1`. |

### `Sessions`
```sql
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
```

| Column | Type | Meaning |
| --- | --- | --- |
| `session_id` | `TEXT PRIMARY KEY` | UUID string for one completed quiz session. |
| `session_filename` | `TEXT` | Filename of the single-session capture when created. |
| `user_name` | `TEXT` | Real learner name; references `Users.name`. |
| `start_time` | `TEXT` | Session start timestamp. MathQuest uses `YYYY-MM-DD_HHMMSS`. |
| `end_time` | `TEXT` | Session end timestamp. MathQuest currently uses the same timestamp as start for exported sessions. |
| `num_problems` | `INTEGER` | Planned number of problems. |
| `number_range_start` | `INTEGER` | Minimum configured/generated operand where applicable. |
| `number_range_end` | `INTEGER` | Maximum configured/generated operand where applicable. |
| `numbers_include` | `TEXT` | JSON text. MathQuest stores `["player_uuid:<uuid>"]` when a UUID is available, otherwise `[]`. |
| `numbers_exclude` | `TEXT` | JSON text, normally `[]`. |
| `num_numbers` | `INTEGER` | Number of operands, currently `2`. |
| `operations` | `TEXT` | JSON array of operation symbols, such as `["+"]`, `["*"]`, or mixed symbols. |
| `total_problems` | `INTEGER` | Count of problem rows actually exported. |
| `correct_answers` | `INTEGER` | Count of correct answers. |
| `average_response_time_ms` | `INTEGER` | Rounded average response time across attempts. |

### `ProblemAttempts`
```sql
CREATE TABLE ProblemAttempts (
  attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT,
  problem_id TEXT,
  problem_text TEXT,
  num1 INTEGER NULL,
  num2 INTEGER NULL,
  operation TEXT NULL,
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

| Column | Type | Meaning |
| --- | --- | --- |
| `attempt_id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Row id; ascending order is presentation order within a session. |
| `session_id` | `TEXT` | References `Sessions.session_id`. |
| `problem_id` | `TEXT` | Stable id within the session. MathQuest uses `1`, `2`, `3`, and so on. |
| `problem_text` | `TEXT` | Canonical displayed problem text, such as `6 + 7`. |
| `num1` | `INTEGER NULL` | First operand when known. |
| `num2` | `INTEGER NULL` | Second operand when known. |
| `operation` | `TEXT NULL` | Canonical symbol: `+`, `-`, `*`, `/`, or `^`. |
| `correct_answer` | `REAL` | Correct numeric answer. |
| `user_answer_string` | `TEXT` | Entered answer as text; empty string when unanswered. |
| `user_answer` | `REAL` | Parsed numeric answer, or `NULL` when unanswered. |
| `is_correct` | `INTEGER` | `1` for correct, `0` for incorrect. |
| `response_time_ms` | `INTEGER` | Time from presentation to submit, in milliseconds. |
| `flags_json` | `TEXT` | JSON array of flag objects, or `NULL`. MathQuest writes reason objects for skip/flag flows. |
| `presented_at` | `TEXT` | Optional timestamp. MathQuest currently writes `NULL` in standard exports. |

### `ModeEvents`
```sql
CREATE TABLE ModeEvents (
  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_name TEXT,
  session_id TEXT NULL,
  from_mode TEXT NULL,
  to_mode TEXT,
  trigger TEXT,
  timestamp TEXT
);
```

MathQuest writes one event for standard arithmetic exports:

| Column | Current MathQuest value |
| --- | --- |
| `user_name` | real learner name |
| `session_id` | exported session UUID |
| `from_mode` | `NULL` |
| `to_mode` | `assess` |
| `trigger` | `mathquest-quiz` |
| `timestamp` | ISO local date-time string |

## Internal problem-list schema

These tables live in active Math Quiz learner files, not in MathQuest's raw
single-session exports. MathQuest reads them when the quiz source is
`internal_problem_list`.

### `ProblemLists`
Current Math Quiz tooling creates and migrates this shape:

```sql
CREATE TABLE IF NOT EXISTS ProblemLists (
  problem_list_id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_name TEXT NOT NULL,
  list_order INTEGER NOT NULL DEFAULT 0,
  list_name TEXT NOT NULL,
  added_at TEXT NOT NULL,
  source TEXT,
  retain INTEGER NOT NULL DEFAULT 1,
  times_used INTEGER NOT NULL DEFAULT 0,
  last_used_at TEXT,
  FOREIGN KEY (user_name) REFERENCES Users(name)
);

CREATE INDEX IF NOT EXISTS idx_problem_lists_user_order
ON ProblemLists (user_name, list_order, problem_list_id);
```

| Column | Type | Meaning |
| --- | --- | --- |
| `problem_list_id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | List id. |
| `user_name` | `TEXT NOT NULL` | Real learner name. |
| `list_order` | `INTEGER NOT NULL DEFAULT 0` | Queue order. Lowest order is used first. |
| `list_name` | `TEXT NOT NULL` | Human label for the list. |
| `added_at` | `TEXT NOT NULL` | Creation timestamp. |
| `source` | `TEXT` | Producer/editor label. |
| `retain` | `INTEGER NOT NULL DEFAULT 1` | `1` means keep after use; `0` means consume/delete after use. |
| `times_used` | `INTEGER NOT NULL DEFAULT 0` | Incremented when retained lists are used. |
| `last_used_at` | `TEXT` | Updated when a retained list is used. |

MathQuest selection:

```sql
SELECT problem_list_id, list_order, list_name, retain
FROM ProblemLists
WHERE user_name = ?
ORDER BY list_order, problem_list_id
LIMIT 1;
```

MathQuest consumption:

- `retain = 1`: update `times_used` and `last_used_at`.
- `retain = 0`: delete row and its `ProblemListItems`, then reindex remaining
  lists for the user to contiguous `list_order` values.

### `ProblemListItems`
```sql
CREATE TABLE IF NOT EXISTS ProblemListItems (
  problem_list_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
  problem_list_id INTEGER NOT NULL,
  item_order INTEGER NOT NULL,
  problem_text TEXT NOT NULL,
  num1 INTEGER NULL,
  operation TEXT NULL,
  num2 INTEGER NULL,
  category TEXT,
  notes TEXT,
  FOREIGN KEY (problem_list_id) REFERENCES ProblemLists(problem_list_id)
);

CREATE INDEX IF NOT EXISTS idx_problem_list_items_list_order
ON ProblemListItems (problem_list_id, item_order);
```

| Column | Type | Meaning |
| --- | --- | --- |
| `problem_list_item_id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Item id. |
| `problem_list_id` | `INTEGER NOT NULL` | Parent list id. |
| `item_order` | `INTEGER NOT NULL` | Presentation order. |
| `problem_text` | `TEXT NOT NULL` | Text such as `6 + 7`. |
| `num1` | `INTEGER NULL` | First operand. |
| `operation` | `TEXT NULL` | Operation symbol. |
| `num2` | `INTEGER NULL` | Second operand. |
| `category` | `TEXT` | Optional category metadata. Useful future hook for story/progression mechanics. |
| `notes` | `TEXT` | Optional notes. Useful future hook for coach/game metadata. |

MathQuest prefers `num1`, `operation`, and `num2` when present. If they are
missing, it parses `problem_text`.

## Internal quick-practice schema
`QuickPracticeItems` lives in the active Math Quiz learner file. MathQuest reads
it when the source is `internal_quick_quiz`.

The implemented MathQuest query is:

```sql
SELECT problem_text, num1, operation, num2
FROM QuickPracticeItems
WHERE user_name = ? AND operation = ?
ORDER BY item_order;
```

Therefore MathQuest currently requires at least these columns:

| Column | Required by MathQuest | Meaning |
| --- | --- | --- |
| `user_name` | yes | Real learner name. |
| `operation` | yes | Operation symbol: `+`, `-`, or `*`. |
| `item_order` | yes | Presentation order. |
| `problem_text` | yes when operands are absent | Text such as `6 + 7`. |
| `num1` | preferred | First operand. |
| `num2` | preferred | Second operand. |

The current operating convention is seven quick-practice rows per supported
operation for each learner. MathQuest does not create, edit, or consume these
rows; it only reads them.

## Written-column schema
Written-column arithmetic is stored separately from standard arithmetic.

Filename pattern:

```text
mathquest_written_column_<real-name>_<YYYY-MM-DD_HHMMSS>.sqlite
```

### `WrittenColumnSessions`
```sql
CREATE TABLE WrittenColumnSessions (
  session_id TEXT PRIMARY KEY,
  session_filename TEXT,
  user_name TEXT,
  player_uuid TEXT,
  created_at TEXT,
  quiz_type TEXT,
  source TEXT
);
```

| Column | Meaning |
| --- | --- |
| `session_id` | UUID string for the written-column session. |
| `session_filename` | Filename written. |
| `user_name` | Real learner name. |
| `player_uuid` | Minecraft player UUID if available. |
| `created_at` | `YYYY-MM-DD_HHMMSS` timestamp. |
| `quiz_type` | `written_column_arithmetic`. |
| `source` | `mathquest`. |

### `WrittenColumnAttempts`

```sql
CREATE TABLE WrittenColumnAttempts (
  attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT,
  operation TEXT,
  factor_a INTEGER,
  factor_b INTEGER,
  correct_answer INTEGER,
  prompt_text TEXT,
  student_answer_text TEXT,
  evaluation TEXT,
  is_correct INTEGER,
  evaluator_code_accepted INTEGER,
  evaluator_notes TEXT,
  response_time_ms INTEGER,
  recorded_at TEXT,
  FOREIGN KEY (session_id) REFERENCES WrittenColumnSessions(session_id)
);
```

| Column | Meaning |
| --- | --- |
| `attempt_id` | Row id. |
| `session_id` | References `WrittenColumnSessions.session_id`. |
| `operation` | Operation name/symbol from the prompt. |
| `factor_a` | First operand. |
| `factor_b` | Second operand. |
| `correct_answer` | Numeric correct answer. |
| `prompt_text` | Prompt shown to the learner/evaluator. |
| `student_answer_text` | Evaluator-entered student answer text. |
| `evaluation` | Evaluator result, such as `correct`, `partial`, or `needs_work`. |
| `is_correct` | `1` only when `evaluation = 'correct'`; otherwise `0`. |
| `evaluator_code_accepted` | `1` when the entered evaluator code matched config; otherwise `0`. |
| `evaluator_notes` | Optional evaluator notes. |
| `response_time_ms` | Recorded response time when available. |
| `recorded_at` | ISO local date-time string. |

Written-column files are not appended to standard Math Quiz active learner files.
They need a separate downstream importer/analysis path if they become part of the
main fluency/story progression model.

## Legacy MathQuest local database
`mathquest_data.db` is MathQuest's local/server operational database. It is not
the Math Quiz learner file.

Current docs describe two main tables:

| Table | Role |
| --- | --- |
| `quiz_sessions` | Local MathQuest session metadata and reward summary. |
| `problem_attempts` | Local MathQuest answer details, including flags in current builds. |

This DB is useful for operational debugging and local history, but the Math Quiz
integration path should use the exported single-session SQLite files and active
learner files described above.

## Append and ingest semantics
The shared ingest helper is:

```text
apps/math-quiz/tools/session_ingest.py
```

MathQuest invokes it through `MathQuizSessionIngestor`. The helper depends on:

```text
apps/math-quiz/tools/anchor_store.py
```

Both files are bundled into the MathQuest jar under `mathquest-tools/` and are
extracted at runtime when a checkout copy is not available.

### Standard MathQuest command shape
```bash
python3 session_ingest.py \
  --single-session /path/to/mathquest_Randy_2026-06-27_101500.sqlite \
  --user Randy \
  --active-dir /path/to/apps/math-quiz/_data/tlkids \
  --archive-dir /path/to/apps/math-quiz/_data/_single-session-sqlite-files \
  --prefix mathquest \
  --match-any-prefix
```

### What `--match-any-prefix` means
The active file can have a different prefix from the new single-session file.

For example:

```text
single session: mathquest_Randy_2026-06-27_101500.sqlite
active target:  math-flu_Randy_2026-06-16.sqlite
```

The helper matches by exact `_<real-name>_` filename boundary and the newest date
after that name, ignoring the prefix.

### Append behavior
| Active target state | Result |
| --- | --- |
| Existing multi-session target, such as `math-flu_Randy_2026-06-16.sqlite` | Append into that file and keep its filename. |
| Existing single-session target, such as `math-flu_Randy_2026-06-16_090000.sqlite` | Copy/rename to `math-flu_Randy_2026-06-16.sqlite`, append, and remove the stale single-session target. |
| No matching active target | Create a new active file using the new prefix, such as `mathquest_Randy_2026-06-27_101500.sqlite`. |
| Session already present by `session_id` | Append is idempotent; duplicate session rows are skipped. |

When appending, `anchor_store.append_session()`:

- inserts missing `Users` rows
- inserts new `Sessions` rows by `session_id`
- copies child rows from `ProblemAttempts`, `WarmupAttempts`, and `ModeEvents`
- adds missing columns to destination tables before copying when needed
- skips a session if its `session_id` is already present

## Current source-of-truth files
| Concern | Source file |
| --- | --- |
| Math Quiz base schema | `apps/math-quiz/math_utils.js` |
| Problem-list schema and CRUD | `apps/math-quiz/tools/problem_list_store.py` |
| Shared append rules | `apps/math-quiz/tools/anchor_store.py` |
| Shared MathQuest/Math Quiz ingest CLI | `apps/math-quiz/tools/session_ingest.py` |
| Standard MathQuest export schema | `apps/minecraft/mods/mathquest/fabric/src/main/java/com/kidgames/mathquest/persistence/SessionExporter.java` |
| Written-column export schema | `apps/minecraft/mods/mathquest/fabric/src/main/java/com/kidgames/mathquest/persistence/WrittenColumnSessionExporter.java` |
| MathQuest internal problem source reads | `apps/minecraft/mods/mathquest/fabric/src/main/java/com/kidgames/mathquest/persistence/MathQuizProblemListLoader.java` |

## Notes and caveats
- The older spec at
  `apps/math-quiz/docs/2026-06-20_minecraft-mod-single-session-sqlite-spec.md`
  remains useful, but this document reflects the current MathQuest integration as
  of `1.11.11`.
- The MathQuest standard arithmetic exporter now uses real learner names, not raw
  Minecraft player names, for filenames and `Users`/`Sessions` rows.
- `QuickPracticeItems` is documented here from the perspective of what MathQuest
  currently reads. If Math Quiz formalizes or extends that table, update this file.
- Fluency/evaluation status is not stored in the standard schema. It is computed
  from raw `ProblemAttempts`.
- Future story/progression systems should prefer adding metadata through explicit
  schema extensions or existing `category`/`notes` fields rather than overloading
  `problem_text`.
