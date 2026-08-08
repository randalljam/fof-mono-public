file: 2026-07-17_cloud-collectors-spec.md
title: Holodeck cloud collectors — Codex cloud ingest + Claude app enrichment
last-updated: 2026-07-17_0545
ai: Claude Code - Fable 5 (fable5-w-codex orchestration)
session: `holodeck control center build`

# Holodeck cloud collectors — build spec (branch feature/holodeck-commits)

Backend-only task (no web/ changes). Ingest cloud AI-coding sessions into the turns DB. Preserve all existing behavior; keep the 97 tests green. Style rules: no type hints, no blank lines between functions, `### ` section headers, stdlib + existing deps only.

Context: `plans/2026-07-09_holodeck/2026-07-17_cloud-session-access-findings.md`.

## File ownership — write ONLY
- `apps/holodeck/turns/cloud_codex.py` (new)
- `apps/holodeck/turns/ingest.py` (extend — call the new collector)
- `apps/holodeck/turns_cli.py` (extend — flags)
- `apps/holodeck/collectors/sessions.py` (small enrichment helper only, §3)
- `apps/holodeck/tests/test_turns.py` (add tests)
- `apps/holodeck/README.md`
Do NOT touch apps/holodeck/web/ or server.py routes beyond what's already there.

## 1 — Codex cloud collector (`cloud_codex.py`)
Shell out to the official Codex CLI (verified working, codex-cli 0.144.2). Pure parse functions separated from subprocess calls for testability.
- `list_cloud_tasks(limit=20, cursor=None)`: run `codex cloud list --limit <limit> --json [--cursor <cursor>]`, parse JSON `{tasks:[...], cursor}`. Task schema (verified): `{id, url, title, status, updated_at (ISO Z), environment_id, environment_label, summary:{files_changed,lines_added,lines_removed}, is_review, attempt_total}`. Paginate via returned `cursor` until null or a total cap (default 60). 20s timeout per call; on non-zero exit or `not logged in`, return `[]` and a note (never raise).
- `task_diff(task_id)`: `codex cloud diff <task_id>` → unified diff text (may be empty / "no diff"); 20s timeout; return "" on failure.
- `to_session_and_exchange(task, diff)`: map each cloud task to:
  - session: `id = "codex-cloud:" + task_id`, `tool="codex-cloud"`, `label = "Codex Cloud" + (" - " + environment_label if set)`, `interface="Codex Cloud"`, `model=None`, `origin="operator"` (a cloud task is Randy dispatching work), `project=None`, `worktree/branch` resolved by matching environment_label to a repo/worktree name when possible (best-effort: match environment_label against worktree basenames and app slugs; else null), `title=task.title`, `started/last_activity = updated_at`.
  - one exchange: `id = session_id + "#0"`, `idx=0`, `kind="primary"`, `user_ts = updated_at`, `user_text = task.title` (the task prompt is the operator intent; full prompt text isn't exposed by the CLI — title is the best available), `response_text = summary line + "\n\n" + diff` (cap diff at 20k chars), `response_end_ts = updated_at`, `origin="operator"`.
  - Store `task.url` — add a `source_url` column to sessions (migrate: ADD COLUMN when missing) so the UI can later deep-link.
- Correlation to commits: after ingest, link a cloud-task exchange to commits whose `subject`/`body` contains the task id or the task url, OR (fallback) commits on the matched worktree within 24h of updated_at with matching files_changed>0. Reuse the existing links table; method `codex-cloud-url` (conf 0.95) or `codex-cloud-window` (conf 0.5).
- Cloud tasks that never landed as commits stay unlinked (expected).

## 2 — Wire into ingest + CLI
- `ingest.py`: add cloud codex ingestion to the build pipeline (guarded — if `codex` binary absent or not logged in, skip with a note; must not break local ingest). Upsert sessions/exchanges via existing db helpers.
- `turns_cli.py build`: add `--no-cloud` to skip cloud ingest (default: include it). Print a `cloud tasks: N` summary line. Cloud tasks participate in auto-digest as operator exchanges (their response_text is the diff — digests will summarize the change).
- `db.py`: `source_url` column on sessions (nullable), included in upsert + `list_turns`/`get_exchange`/status payloads.

## 3 — Claude app metadata enrichment (small, sessions.py)
Most Claude desktop-app local-mode sessions (`~/Library/Application Support/Claude/claude-code-sessions/**/local_*.json`) are already in the CLI JSONL store (linked by `cliSessionId`) and are for other repos — so DO NOT create new sessions from them. Instead:
- Add `load_claude_app_metadata()`: scan those JSON files, return a dict keyed by `cliSessionId` → `{model, effort, title, permission_mode}` (skip entries with empty cliSessionId).
- In Claude session parsing, when a CLI session's id matches a `cliSessionId`, prefer the app-provided `model`/`title` when the CLI didn't yield one (enrichment only; never override a present value). Best-effort, wrapped in try/except; no-op when the app dir is absent.
- This is intentionally minimal — the app JSON adds no new in-repo sessions here.

## Tests (keep existing green)
- `list_cloud_tasks` JSON parsing (fixture with 2 tasks + cursor paging + empty/error → []).
- `to_session_and_exchange` mapping (env_label→label, diff cap, ids, origin operator).
- cloud-task→commit correlation (url match; window fallback; unmatched).
- source_url column migration + round-trip.
- claude app metadata index parsing (empty cliSessionId skipped; enrichment doesn't override present values).

## Acceptance
- `turns_cli.py build` ingests real cloud tasks (`codex cloud list` returns at least the known `task_e_6a04...` "Set up virtual machine in Codex app" / learnbox); it appears in turns.db as a `codex-cloud:` session with a primary exchange and source_url.
- `--no-cloud` skips it; local ingest unaffected either way.
- All tests green. Report files changed, real cloud-task count ingested, verification, deviations.
