file: 2026-07-17_cloud-session-access-findings.md
title: Cloud AI-coding session access — findings and implementation paths
last-updated: 2026-07-17_0530
ai: Claude Code - Fable 5 (fable5-w-codex orchestration)
session: `holodeck control center build`

# Cloud AI-coding session access — the complete picture (2026-07-17)

Goal: get full transcripts of cloud AI-coding sessions (Claude Code cloud VM, Codex cloud) into holodeck's turns DB, since the whole operator-turns model breaks if these interaction points are invisible. Findings from local-machine forensics + a verified web-research sweep (15 adversarially-verified claims).


## Executive summary
| Platform | Best access path | Status |
|----------|------------------|--------|
| **Codex cloud** | `codex cloud list` / `diff` / `status` (official CLI) | ✅ **Verified working on this machine** |
| **Codex local** | `~/.codex/sessions/*.jsonl` | ✅ already ingested |
| **Claude Code CLI/local-desktop** | `~/.claude/projects/*.jsonl` + app `claude-code-sessions/*/local_*.json` | ✅ CLI ingested; app JSON is an easy add |
| **Claude Code cloud VM** | private `claude.ai/api/organizations/{org}/...` (cookie auth) | ⚠️ endpoint for *chats* verified; *code-session* endpoint needs discovery |


## Codex cloud — SOLVED (official CLI)
`codex cloud` (EXPERIMENTAL, present in codex-cli 0.144.2) subcommands: `list`, `status`, `diff`, `apply`, `exec`.
- `codex cloud list --limit 20 [--cursor <c>] [--env <id>]` → tasks with URL, `[READY]` status, repo, date, diff availability. Verified: returned a real task (`task_e_...`, "Set up virtual machine in Codex app", learnbox). Auth = existing Codex CLI login (no extra setup).
- `codex cloud diff <task>` → unified diff; `codex cloud status <task>` → status.
- Underlying API is `chatgpt.com/backend-api/...` with the CLI's stored token; the CLI is the clean supported entry.
- **Caveat:** `list`/`diff` expose task metadata + code diffs. Full prompt/response *transcript* may need `status` or a direct backend-api call — verify when building. Diffs+metadata already correlate to commits (the core need).

## Claude Code cloud VM — private API (needs one discovery step)
- **NOT in any local cache** on this machine: searched `~/.claude/projects`, `~/.claude/sessions`, the claude.ai IndexedDB (1 stale key), and `Claude-3p/` (empty enterprise stub). Cloud VM transcripts live server-side and stream to the app on demand.
- **Private REST API** (verified from the Claude-Conversation-Exporter extension source):
  - list: `GET https://claude.ai/api/organizations/{orgId}/chat_conversations`
  - content: `GET https://claude.ai/api/organizations/{orgId}/chat_conversations/{id}?tree=True&rendering_mode=messages&render_all_tools=true`
  - auth: browser session cookie (`credentials: 'include'`) + orgId from `claude.ai/settings/account`.
- **Open question:** those endpoints are proven for claude.ai **chat** conversations. Claude's own docs say cloud/web *code* sessions keep history separate from CLI. Whether code cloud sessions appear under `chat_conversations` or a distinct endpoint is UNVERIFIED. Community exporters cover chats, not code sessions.
- **Discovery plan:** use the `claude-in-chrome` browser skill to open a claude.ai/code cloud session and capture the actual network request the page fires — that reveals the exact endpoint + params. Then build a cookie-authed poller.
- `/export` (official) only dumps the *current* CLI session; not bulk cloud.

## Desktop-app local caches (surveyed)
- **ChatGPT app** `~/Library/Application Support/com.openai.chat/conversations-v3-<userId>/`: **84 conversation `.data` files, AES-encrypted at rest** (entropy 8.00/8.00; key in macOS login Keychain). Decryptable in principle but superseded by the `codex cloud` CLI path — skip.
- **Claude app** `~/Library/Application Support/Claude/claude-code-sessions/*/local_*.json`: **readable** local-mode Code sessions (title/model/cwd) NOT yet ingested — easy holodeck win. `local-agent-mode-sessions/` similar.
- Codex `codex-taskItems-v2-*` / `codex-environments-*` stores exist but are empty (folded into main store after the mid-July rebrand).

## Product-change context (mid-July 2026)
- Codex docs 308-redirect from developers.openai.com → learn.chatgpt.com (Codex folded into ChatGPT branding). CLI `codex cloud`/`resume` intact.
- Claude Code v2.1.212: `/resume` picker includes sessions deleted from the list; 30-day local transcript cleanup can delete old local history (argues for regular sweeps).

## Recommended implementation (priority order)
1. **Codex cloud collector** — shell `codex cloud list` (+ `--cursor` paging) + per-task `diff`/`status`; ingest as cloud sessions/exchanges in turns.db; correlate diffs→commits. Official, robust.
2. **Claude app local-JSON collector** — ingest `claude-code-sessions/*/local_*.json`; trivial, widens coverage today.
3. **Claude cloud poller** — browser-skill endpoint discovery, then cookie-authed poller against the confirmed endpoint; store org id + cookie handling. ToS-gray (private API) — get explicit sign-off before building.
4. **Skip** the encrypted ChatGPT `.data` decryptor — CLI path supersedes it.

## Risk / ToS notes
- Codex cloud CLI: first-party, supported. Lowest risk.
- Claude private API + browser cookies: undocumented, cookie may rotate, ToS-gray. Fragile; isolate behind one collector with clear failure handling.


## UPDATE 2026-07-18 — full APIs verified via browser + curl
### Claude cloud (claude.ai/v1/code) — VERIFIED
- List: `GET https://claude.ai/v1/code/sessions?statuses=active&statuses=paused&limit=50` (header `anthropic-version: 2023-06-01`).
- Detail: `GET /v1/code/sessions/{id}`; Transcript: `GET /v1/code/sessions/{id}/events?limit=500&sort_order=asc&cursor=<next_cursor>` → `{data:[{event_type,payload,created_at}], next_cursor}`; user/assistant events match CLI message shape.
- Auth: httpOnly `sessionKey` cookie (NOT JS-readable; only via DevTools). No local file/token reuse (Claude CLI creds are in Keychain "Claude Code-credentials", not a readable file). → user pastes sessionKey into `.env` as CLAUDE_AI_SESSION_KEY. IDs come back as `cse_...` (also work on the events path).
### Codex cloud (chatgpt.com wham) — VERIFIED, NO USER ACTION
- Auth: Bearer = `~/.codex/auth.json` → `tokens.access_token` (the Codex CLI's own token; reuse at runtime). 401 → refresh via `codex login`/`codex cloud`.
- List: `GET https://chatgpt.com/backend-api/wham/tasks/list?limit=50&task_filter=current`.
- Detail: `GET .../wham/tasks/{id}`; Transcript: `GET .../wham/tasks/{id}/turns` → `{turn_mapping:{<id>:{turn:{role, input_items|output_items ...content[].text}}}, current_turn_id}`. Assistant turns carry `direct_push_pushed_commit_sha` + `branch_name` → EXACT commit correlation. Confirmed HTTP 200 from plain curl with the auth.json token.
### SuperWhisper (voice source) — LOCATED (pinned, privacy-sensitive)
- `~/Documents/superwhisper/recordings/<epoch>/meta.json` — 26,508 recordings. Fields: `result` (transcript), `datetime`, `duration`, `modeName`, `languageModelName`, `prompt`, `promptContext`, `applicationContextEnabled`, `speakers`, `segments`.
- Many are PERSONAL/sensitive — must stay private and separate from coding. Design later: ingest only coding-mode recordings (filter by `modeName`/app context), never bulk-index personal ones. Most coding transcripts are already captured in the pasted prompt, so this is a supplementary raw source.
