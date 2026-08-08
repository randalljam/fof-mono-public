file: 2026-07-11_applet-interaction-logging.md
title: Applet interaction logging — SQLite session capture
last-updated: 2026-07-11_2145
ai: Claude Code - Fable 5
session: `Logic Gates applet + interaction logging`

Design and conventions for capturing learner interactions in the `/applets/` teaching pages (Logic Gates first) as **single-session SQLite files**, following the math-quiz data conventions (`apps/math-quiz/docs/2026-06-20_minecraft-mod-single-session-sqlite-spec.md`, `tools/dev_server.py`, `math_utils.js createTables()`).


## What gets recorded
Three levels, all timed relative to session start (`t_ms`, integer milliseconds):
1. **Raw clicks** — every click/tap inside the applet (capture-phase listener on the applet root): timestamp, current step, and a best-effort target label (aria-label, text content, or tag).
2. **Semantic events** — step enters/leaves, switch toggles, reveals, quiz answers, checks, mute/replay, start, start-over.
3. **Quiz outcomes** — per attempt: which quiz, round, what was asked, what was given, correct or not, attempt index within the round (tries), and time since the round was presented.

Per-screen time comes from step enter/leave pairs (`StepVisits`).


## Data flow
```
LogicGates.jsx  ──logEvent()──▶  sessionStorage buffer  ──flush──▶  POST /api/save-session  ──▶  _data/applet-sessions/<file>.sqlite
                (applet-telemetry.js)                        (tools/telemetry_server.py, localhost only)
```
- **Buffer**: `sessionStorage` key `applet-telemetry:<applet>` — survives reloads within the tab; the whole buffer is sent on every flush (idempotent server rewrite, no partial-append bookkeeping).
- **Flush triggers**: step change, every 25 buffered events, `visibilitychange → hidden`, and `pagehide` (via `navigator.sendBeacon`).
- **Server absent** (normal for the deployed static site): fetch fails silently, telemetry keeps buffering, retries on the next flush trigger. The applet must never break or slow down because logging is off.
- **Server present** (local dev): rewrites the session's `.sqlite` file atomically (tmp + `os.replace`) on every flush.


## File naming and location
Same stamp convention as math-quiz single-session files (`math-flu_K1_2026-06-20_103814.sqlite`):
```
apps/focusonfoundations/web/_data/applet-sessions/<applet>_<user>_<YYYY-MM-DD>_<HHMMSS>.sqlite
```
- `<applet>` — e.g. `logic-gates`.
- `<user>` — from the `?user=` query param, sanitized to `[a-zA-Z0-9_-]`, default `anon`.
- `<YYYY-MM-DD>_<HHMMSS>` — session **start**, local clock, 24-hour, no colon. Must match `Sessions.start_time` stamp.
- One file = one session (one press of ▶). Start-over stays in the same session (it is an event, not a new session).
- `_data/` is gitignored repo-wide (`**/_data` rule). Never commit learner data.


## Schema
Naming follows math-quiz: TitleCase tables, snake_case columns, `*_ms` integer durations, `is_correct` 0/1, ISO-ish local wall times as TEXT.

```sql
CREATE TABLE Users (
  name TEXT PRIMARY KEY
);
CREATE TABLE Sessions (
  session_id TEXT PRIMARY KEY,          -- "<applet>_<user>_<stamp>", equals filename minus .sqlite
  session_filename TEXT,
  applet TEXT,
  user_name TEXT,
  start_time TEXT,                      -- "YYYY-MM-DD HH:MM:SS" local
  end_time TEXT,                        -- last event's wall time
  duration_ms INTEGER,                  -- last event t_ms
  user_agent TEXT,
  total_clicks INTEGER,
  total_quiz_attempts INTEGER,
  FOREIGN KEY (user_name) REFERENCES Users(name)
);
CREATE TABLE Events (                    -- raw truth: every click + semantic event
  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT,
  t_ms INTEGER,                          -- ms since session start
  kind TEXT,                             -- 'click','step-enter','step-leave','toggle','reveal',
                                         -- 'quiz-attempt','nav','mute','replay','start','start-over',...
  step INTEGER,                          -- step index when the event fired (NULL if n/a)
  target TEXT,                           -- best-effort label of what was touched
  detail_json TEXT,                      -- kind-specific payload (inputs, answers, ...)
  FOREIGN KEY (session_id) REFERENCES Sessions(session_id)
);
CREATE TABLE StepVisits (                -- derived from step-enter/step-leave events
  visit_id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT,
  step INTEGER,
  enter_t_ms INTEGER,
  leave_t_ms INTEGER,                    -- NULL if the session ended on this step
  duration_ms INTEGER,                   -- NULL if leave unknown
  FOREIGN KEY (session_id) REFERENCES Sessions(session_id)
);
CREATE TABLE QuizAttempts (              -- derived from 'quiz-attempt' events
  attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT,
  quiz TEXT,                             -- 'NOT','OR','AND','XOR','mystery','half-adder','ripple'
  round INTEGER,
  attempt_index INTEGER,                 -- 1-based try count within the round
  prompt TEXT,                           -- what was shown (inputs / target sum / hidden gate)
  given TEXT,                            -- the learner's answer
  is_correct INTEGER,
  t_ms INTEGER,                          -- when the attempt happened
  response_time_ms INTEGER,              -- t_ms minus the round's presentation t_ms
  FOREIGN KEY (session_id) REFERENCES Sessions(session_id)
);
```
`StepVisits` and `QuizAttempts` are **derived server-side** from `Events` on every flush; `Events` is the source of truth. Re-deriving from a captured file must give the same rows.


## Components
- **`web/src/lib/applet-telemetry.js`** — SSR-safe client library (no deps): session start, `logEvent`, quiz-attempt helper, click-capture attachment, buffering, flush policy. Applet-agnostic; Logic Gates is the first consumer.
- **`web/tools/telemetry_server.py`** — stdlib-only local receiver (http.server + sqlite3 + json), default port **8787**, CORS echoes the request Origin (sendBeacon sends credentials, which forbids a wildcard; localhost-only tool, never deploy — same posture as math-quiz `tools/dev_server.py`). `POST /api/save-session` with the full event payload; `GET /api/health`. Run with the repo venv: `../../../.venv/bin/python3 tools/telemetry_server.py` from `web/` (npm script `telemetry`).
- **`web/src/components/applets/LogicGates.jsx`** — instrumented at the semantic points; raw clicks come from the capture listener.
- **`web/tools/telemetry_report.py`** — developer digest of a captured session file (step timeline, per-step time, quiz tries/outcomes, activity; `--events` for the raw timeline).
- **`web/docs/2026-07-12_applet-session-llm-analysis.md`** — data dictionary + prompt to hand a session file to an AI for a student-understanding assessment.

Shared-core note: the Python side is intentionally small and app-local. If a third consumer appears (math-quiz refactor, another applet family), promote the event→schema derivation into `core/` then — not before.
