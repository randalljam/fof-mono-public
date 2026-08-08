file: 2026-07-18_claude-cloud-poller-spec.md
title: Holodeck Claude cloud poller — ingest claude.ai/code cloud VM sessions
last-updated: 2026-07-18_0700
ai: Claude Code - Fable 5 (fable5-w-codex orchestration)
session: `holodeck control center build`

# Holodeck Claude cloud poller — build spec (branch feature/holodeck-commits)

Backend-only. Ingest Claude Code CLOUD VM sessions (claude.ai/code, e.g. Cataclysm env) into the turns DB via the private claude.ai API discovered by browser network capture 2026-07-18. Preserve existing behavior; keep tests green. Style: no type hints, no blank lines between functions, `### ` headers, existing deps only (stdlib `urllib` for HTTP — do NOT add requests).

## Verified API (base https://claude.ai; required header `anthropic-version: 2023-06-01`; auth = session cookie)
- **List:** `GET /v1/code/sessions?statuses=active&statuses=paused&limit=50` (repeatable `statuses` param; also accepts `completed`). Returns session summaries (id like `session_01QX...`, title, status, updated_at, repo).
- **Detail:** `GET /v1/code/sessions/{session_id}` → `{response_shape:{config:{model, effort_level, origin, sources:[{revision, url, type}], outcomes:[{git_info:{repo, branches, type}}]}, ...}}`. Gives model (`claude-opus-4-8`), branch (`sources[].revision` e.g. `refs/heads/feature/...`, and `outcomes[].git_info.branches` e.g. `claude/...`), repo (`FocusOnFoundationsNonprofit/fof-mono`), origin (`desktop_app`).
- **Events (transcript):** `GET /v1/code/sessions/{session_id}/events?limit=500&sort_order=asc[&cursor=<next_cursor>]` → `{data:[event], next_cursor, resume_cursor}`. Paginate by passing `next_cursor` until it is null/absent.
  - Event schema: `{event_id, event_type, created_at, sequence_num, source, payload}`.
  - event_type `user` → `payload.message.content` is the operator prompt (string). `payload.client_platform` = `desktop_app`.
  - event_type `assistant` → `payload.message.content` is an array of blocks (text/thinking/tool_use) — SAME shape as Claude Code CLI JSONL assistant messages.
  - event_type `result` → final `{duration_ms, modelUsage, cost, is_error}`.
  - Other types (ignore for messages): control_request, control_response, env_manager_log, rate_limit_event, system (hooks), tool_progress.

## Auth (user-supplied credential — do NOT attempt to read cookies/keychain)
- Read `CLAUDE_AI_SESSION_KEY` from repo `.env` (dotenv, same pattern as digest keys). It is the value of the `sessionKey` cookie from claude.ai. Send as header `Cookie: sessionKey=<value>` plus `anthropic-version: 2023-06-01`.
- If the var is absent → skip claude-cloud ingest with a clear note (never raise). On HTTP 401/403 → note "CLAUDE_AI_SESSION_KEY expired — refresh from claude.ai devtools" and skip. Cookie expiry is the known fragility; isolate all failures inside the collector.
- README: document how to get the key (claude.ai → devtools → Application → Cookies → `sessionKey`) and that it expires periodically.

## Module `apps/holodeck/turns/cloud_claude.py`
Pure parse functions separated from HTTP (urllib) for testability.
- `fetch_session_list(session_key, statuses=("active","paused","completed"))` → list of summaries; tolerate unknown status values (retry with fewer if 400).
- `fetch_session_detail(session_key, sid)` → parsed `{model, effort, repo, branches:[...], origin}`.
- `fetch_session_events(session_key, sid)` → concatenated `data` across all `next_cursor` pages (cap 20 pages / 10k events; log if capped).
- `events_to_messages(events)` → list of `{role, text, ts}` from `user`/`assistant` events, REUSING the existing Claude content flattener (`content_to_text` / message parsing from collectors/sessions.py — import it; do not duplicate). `result` events ignored for messages.
- `to_session(summary, detail, sid)` → session dict: `id="claude-cloud:"+sid`, `tool="claude-cloud"`, `label="Claude Code Cloud" + (" - "+PrettyModel if model)`, `interface="Claude Code App (Cloud)"`, `model=detail.model`, `origin="operator"`, `branch` = first of detail.branches that looks like a feature branch else first branch, `worktree` matched by branch→worktree path when the repo is fof-mono (reuse worktree list), `title=summary.title`, `source_url="https://claude.ai/code/"+sid`, timestamps from summary/events.
- Segmentation: reuse the SAME `segment_messages` used for local sessions (import from ingest) so cloud exchanges get identical primary/quick/info + follow-up handling.

## Wire-in
- `ingest.py`: add claude-cloud ingestion to the build pipeline, guarded by CLAUDE_AI_SESSION_KEY presence; upsert sessions/exchanges. Correlate cloud-session exchanges to commits on the session's branch(es) within a time window (reuse correlation; cloud sessions declare their branch, so also match commits whose branch equals detail.branches — high confidence 0.85 `claude-cloud-branch`).
- `turns_cli.py`: existing `--no-cloud` also skips claude-cloud. Print `claude cloud sessions: N`.
- `db.py`: `source_url` already added — reuse.
- Optional incremental cache: write raw events per session to gitignored `data/cloud_claude/<sid>.jsonl`; on rebuild, only fetch events after the cached max sequence_num (use `resume_cursor`). Keep simple — full refetch is acceptable if this adds risk; guard behind a try/except.

## Tests (fixtures from the real schema above; no network)
- `events_to_messages`: user event → user text; assistant event with block array → joined text; result/system/tool_progress ignored.
- pagination: two-page events (`next_cursor` then null) concatenated.
- `to_session`: branch selection (feature branch preferred over claude/ auto branch), label with PrettyModel, worktree match by branch, source_url.
- auth-missing → skip; 401 handling returns note not raise (mock urllib).
- correlation: cloud session on branch X links commits on branch X.

## Acceptance
- With a valid CLAUDE_AI_SESSION_KEY, `turns_cli.py build` reports `claude cloud sessions: N>0`; the known session `session_01QXMH6C9sQRi7Jz9N1gzb5b` ("Review branch commits and fix tests") ingests as a `claude-cloud:` operator session whose first user exchange contains the real voice-dictated prompt, model claude-opus-4-8, branch matched, correlated to its agent commits.
- Without the key: clean skip, local + codex-cloud ingest unaffected.
- All tests green. Report files changed, real ingest counts (if key available), verification, deviations.
