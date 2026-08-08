file: 2026-07-17_operator-turns-spec.md
title: Holodeck operator turns — operator/delegated split, waiting states, turn titles, sessions redesign
last-updated: 2026-07-17_0416
ai: Claude Code - Fable 5 (fable5-w-codex orchestration)
session: `holodeck control center build`

# Holodeck operator turns — build spec (branch feature/holodeck-commits)

User feedback 2026-07-17 (early morning, verbatim notes appended to `apps/holodeck/AI-SESSIONS.md` by Randy). Two parallel, file-disjoint tasks. Preserve all existing behavior not named here.

## THE FOUNDING INSIGHT (get this right)
The whole system rests on: **Randy never reads code and rarely reads plans. The only two human interaction points are (1) a voice-dictated intent prompt to a top-level agent, and (2) Randy trying the app / reviewing the response and dictating feedback.** Therefore:
- A **turn** (the unit everything organizes around) = Randy's prompt → the top-level agent's full response. That, and ONLY that, is a *primary/operator* exchange.
- Agent-to-agent traffic (Codex delegations from the fable5-w-codex skill, subagent runs, auto-review bots) is **machinery inside a turn** — it must NEVER be presented as a peer of Randy's turns. Yesterday's build wrongly surfaced Codex delegation prompts as "primary" exchanges.
- The dashboard's job is to serve the loop: intent → wait → response ready → Randy reviews/tests → feedback. "Whose turn is it?" (waiting-on-AI vs waiting-on-Randy) is the single most important live signal.

## 1 — Operator vs delegated (backend)
- `sessions` and `exchanges` gain `origin`: `operator` | `delegated` (DB column, default operator; snapshot sessions layer gains the same field).
- A session is `delegated` when ANY of: codex `originator` is `Claude Code` or a plugin-companion originator; the session's first real user message matches an executor preamble (starts with "You are the implementation executor", "You are the implementation", or contains "Do not commit or push." within the first 400 chars — tune in one function `looks_delegated(...)` in labels.py or ingest.py with unit tests); the session label already maps to `Codex CLI (fable5-w-codex)`. Cursor sessions are always operator. Claude Code local CLI sessions are operator.
- Codex CLI sessions launched by an agent via `codex exec` currently label as `Codex CLI (Cursor)` — when `looks_delegated` fires on such a session, ALSO relabel to `Codex CLI (fable5-w-codex) - <model> <effort>`.
- `kind` (primary/quick/info) is only meaningful for operator exchanges; delegated exchanges keep kind but every API result and digest priority treats origin first.
- `/api/turns` default: operator exchanges only; `&include=delegated` returns all. Digest CLI/auto-digest: operator only.

## 2 — Waiting state per worktree (backend + frontend)
- Backend: extend the turns DB/API with a per-branch (and per-worktree) **latest-turn status**: for the most recent operator exchange of the most recently active operator session matched to each worktree/branch: `{state: "waiting-on-ai" | "your-turn", since: ts, exchange_id, session_id, session_label, turn_title, recap}`.
  - `waiting-on-ai`: the exchange has a user_ts but no (or still-growing) response — i.e. last message in the session is the user's, OR the session file mtime is fresh (<3 min) with assistant output still appending. Practical rule: last message role == user → waiting-on-ai (since user_ts); else → your-turn (since response_end_ts).
  - Expose as `GET /api/turns/status` → one row per worktree with an active operator session in the last 14 days.
- Frontend Status panel redesign (this REPLACES the current Status rows; keep manual next-steps display when present, appended below the narrative line):
  - Row per worktree: worktree chip (identity color) + **checked-out branch pill** (short name — strip `feature/` prefix; e.g. `holodeck-commits`) + state badge: `WAITING ON AI` (gold, subtle pulse) or `YOUR TURN` (green) + elapsed since + the **turn title** (from digest, else user-preview) + session label + time.
  - Hover on the row → tooltip with the digest recap (or last-user preview). Click → opens the session drawer (turns view). A small `⇣` affordance scrolls to that session's row in 07 AI Sessions. Keep each card's existing "open in Cursor" as the window-opening path.
  - Manual worktree next steps still render (smaller, under the narrative line) when set.

## 3 — Turn titles (backend + frontend)
- Digest JSON gains `"title"`: a 3-7 word name for the turn as work (e.g. "Turns database build", "Session labels + digest drawer", "Overview status redesign 2") — named for WHAT WAS BUILT/CHANGED, never a transcription snippet. Add to the digest prompt; store in a new `title` column on digests (migrate table if exists: ALTER TABLE ADD COLUMN when missing).
- Wherever a session/exchange renders a title: prefer digest title of its latest primary exchange → else session ai-title → else truncated first_user. AI Sessions rows, Status rows, drawer headers all use this.

## 4 — Digest model + auto-digest (backend)
- Model: switch Anthropic digest model to `claude-sonnet-5` (user decision — quality over cost; keep OpenAI fallback as-is). Model name in ONE constant.
- Auto-digest: after every turns refresh (`POST /api/turns/refresh` and `turns_cli.py build` unless `--no-digest`), automatically digest undigested OPERATOR exchanges from the last 48 hours (cap 25 per run, newest first, primary before quick before info) in a background thread (server) / inline (CLI). Missing key → clean skip. This reverses the old no-auto rule per explicit user instruction 2026-07-17.
- Keep `--digest --limit N` for manual/backfill runs.

## 5 — AI Sessions section redesign (frontend)
- Columns become: `Session | Worktree/Branch | Messages | When`.
  - `Session`: tool dot + title (per §3 precedence) with the session label as a second muted line (or suffix) — label stays visible.
  - `Worktree/Branch`: ONE pill showing the short branch name (strip `feature/` etc. prefix) colored with the WORKTREE'S identity color (title_bar background as text/border color) — the colors are how Randy keeps work mentally organized; they must carry into this section. Sessions with no matched worktree show the project dir name muted.
  - `When`: relative time AND absolute `YYYY-MM-DD HH:MM` (muted, mono, side by side).
- Row click keeps opening the drawer (turns view first).
- Delegated sessions: hidden by default behind a filter chip `machinery` (off by default; when on, delegated rows render dimmed with a `delegated` tag). The tool filter chips stay.

## 6 — Roadmap notes (either task may write, single file apps/holodeck/ROADMAP.md — append, don't rewrite)
Append three items: (a) work-mode input (head-down vs casual; 1-screen vs 2-screen) shaping what the overview emphasizes; (b) revisit branch naming — `feature/` prefix carries no information for this workflow, consider dropping prefixes for work branches; (c) two-screen mode: holodeck on one screen driving/opening Cursor windows on the other (deep-link/open-in-Cursor from Status rows).

## Task split
- **Task 1 backend** (owns apps/holodeck/turns/, turns_cli.py, collectors/sessions.py, server.py, tests/, README.md): §1, §2 backend, §3 backend, §4. Tests: looks_delegated cases (codex originator, executor preamble, cursor never), relabel to fable5-w-codex, waiting-state derivation (last-role user vs assistant), digest title parsing + column migration, auto-digest selection window (operator-only, 48h, cap). Keep 83+ green. Style rules unchanged.
- **Task 2 frontend** (owns apps/holodeck/web/ only): §2 frontend, §3 display precedence, §5, sample data updates (sample-turns.json gains titles + a status payload sample file `sample-turn-status.json`; sample sessions get origin fields). Null-safe, escape everything, keep ids stable.

## Acceptance
- The Codex delegation sessions from 2026-07-16 are origin=delegated, relabeled `Codex CLI (fable5-w-codex) - GPT 5.5 xhigh`, absent from default /api/turns and from AI Sessions unless `machinery` filter is on.
- /api/turns/status shows this worktree with branch `holodeck-commits`, state derived correctly, and a digest-derived turn title.
- Status panel shows chip + short-branch pill + WAITING ON AI / YOUR TURN + title; hover recap; click opens drawer.
- AI Sessions shows colored worktree/branch pills, dual timestamps, digest titles.
- Digest model constant is claude-sonnet-5; refresh auto-digests recent operator exchanges.
- All tests green; both tasks report files changed, verification, deviations.
