file: 2026-07-18_codex-transcripts-and-banner-spec.md
title: Holodeck — Codex cloud full transcripts + cloud-auth 401 banner
last-updated: 2026-07-18_0745
ai: Claude Code - Fable 5 (fable5-w-codex orchestration)
session: `holodeck control center build`

# Codex cloud full transcripts + 401 banner — build spec (branch feature/holodeck-commits)

Two file-disjoint tasks. Preserve existing behavior; keep tests green. Style: no type hints, no blank lines between functions, `### ` headers, stdlib (urllib) + existing deps only.

## Verified Codex cloud (wham) API — browser + curl confirmed 2026-07-18
Base `https://chatgpt.com`. Auth: **Bearer token from the Codex CLI's own store** — read `~/.codex/auth.json` → `tokens.access_token` (len ~1710) at runtime (like reading .env; NEVER log it). No user action needed. On HTTP 401 → token expired; skip with note "run `codex cloud list` or `codex login` to refresh", do not raise. (Refreshing via `tokens.refresh_token` is out of scope for v1.)
- **List:** `GET /backend-api/wham/tasks/list?limit=50&task_filter=current` → tasks. (Also accepts other `task_filter` values; `current` is what the UI uses. Paginate if a cursor field is present.)
- **Detail:** `GET /backend-api/wham/tasks/{task_id}`
- **Transcript:** `GET /backend-api/wham/tasks/{task_id}/turns` → `{turn_mapping:{<turn_id>:{id, turn:{...}, children, parent}}, current_turn_id}`.
  - user turn: `turn.role=="user"`, text at `turn.input_items[].content[]` where `content_type=="text"` → `.text`; `turn.created_at`, `turn.user_model_slug`.
  - assistant turn: `turn.role=="assistant"`, text at `turn.output_items[...]` (recursively find `content_type=="text"` → `.text`); rich metadata: `created_at`, `model_version`, `branch_name`, `base_commit_sha`, **`direct_push_pushed_commit_sha`** (the commit the task pushed — use for EXACT correlation), `pull_request_data`, `turn_status`, `environment`.
  - Order turns by `created_at`. `turn_mapping` is a parent/children tree; a simple created_at sort over all nodes is sufficient.

## Task 1 — backend: upgrade Codex cloud collector to full transcripts (owns turns/cloud_codex.py, turns/ingest.py, server.py, tests/, README.md)
Replace the diff-only v1 mapping with full-transcript ingestion (keep `codex cloud list` fallback for task discovery if the wham token is unavailable):
- `codex_access_token(root=None)`: read `~/.codex/auth.json` tokens.access_token; None if absent.
- `wham_get(path, token, urlopen=None)`: GET chatgpt.com + Bearer; 401 → raise a typed CloudAuthError caught by callers.
- `list_wham_tasks(token)`, `fetch_task_turns(token, task_id)`.
- `turns_to_messages(turn_mapping)`: reuse a recursive text-extractor; return ordered `[{role, text, ts}]` (user + assistant only; skip empty).
- Map each task → a `codex-cloud:` session (unchanged id scheme, tool="codex-cloud", origin="operator", label="Codex Cloud"+env, source_url=task url, model from assistant `model_version`, branch from assistant `branch_name`), then segment its messages via the shared `segment_messages` into exchanges (so a multi-turn cloud task yields multiple exchanges, like local sessions) — NOT the old single-exchange mapping.
- Correlation: link exchanges to the commit in assistant `direct_push_pushed_commit_sha` (method `codex-cloud-push`, conf 0.97) when that SHA exists in commits; else fall back to branch_name/window as before.
- If wham token/API unavailable: fall back to the existing `codex cloud list --json` metadata-only ingestion (keep that code path) so `--no-cloud` and offline still behave.
- Tests: token read (fixture auth.json), turns_to_messages (user input_items + assistant output_items text; nested; empty skipped), exact push-sha correlation, 401 → skip note, fallback-to-CLI path.

## Task 2 — cloud-auth status + 401 banner (backend server.py endpoint + frontend web/)
Backend (server.py, small; may also touch turns/cloud_codex.py + turns/cloud_claude.py for a status probe helper):
- `GET /api/cloud-status` → `{sources:[{key:"codex-cloud", state:"ok|expired|absent", detail}, {key:"claude-cloud", state, detail}]}`.
  - codex-cloud: absent if no ~/.codex/auth.json token; else do a cheap HEAD/list probe — `ok` on 200, `expired` on 401 (cache result ~60s to avoid per-request cost).
  - claude-cloud: absent if no CLAUDE_AI_SESSION_KEY; else probe `GET /v1/code/sessions?limit=1` — `ok`/`expired`.
- Never include tokens/keys in the response.
Frontend (web/ — app.js, index.html, style.css):
- On load, fetch `/api/cloud-status`. If any source is `expired` or (present-but-`absent` when the other cloud source is ok), show a dismissible amber banner near the top bar: e.g. "Claude cloud session key expired — refresh CLAUDE_AI_SESSION_KEY in .env" / "Codex cloud token expired — run `codex login`". Include the fix hint per source. Absent (never configured) shows a subtler one-line hint, not an alarm.
- Sample mode: no banner (or a static sample note). Null-safe; escape text.

## Acceptance
- `turns_cli.py build` ingests the real Codex cloud task `task_e_6a04...` as a `codex-cloud:` session whose exchanges contain the FULL user prompt ("I'm trying to get setup to use the Codex app...") and the assistant response text, correlated to any pushed commit by SHA. (Token confirmed working via curl.)
- `/api/cloud-status` reports codex-cloud ok (token present) and claude-cloud absent/ok per CLAUDE_AI_SESSION_KEY.
- Banner shows on expired/absent and hides when ok; never leaks secrets.
- All tests green. Report files changed, real ingest counts, verification, deviations.
