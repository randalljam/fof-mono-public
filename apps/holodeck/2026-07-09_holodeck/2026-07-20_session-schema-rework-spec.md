file: 2026-07-20_session-schema-rework-spec.md
title: Holodeck — session schema rework (platform/entrypoint/host + remote control)
last-updated: 2026-07-20_1700
ai: Claude Code - Fable 5 (fable5-w-codex orchestration)
session: `holodeck control center build`

# Session schema rework — build spec (branch feature/holodeck-commits)

Rework the normalized session object per Randy's terminology (AI-SESSIONS.md "### rework of the fields"). This propagates across 8 files + DB + frontend. Keep tests green; add new ones. Style: no type hints, no blank lines between functions, `### ` headers.

## The new field model (authoritative)
Replace `tool` with THREE orthogonal fields plus RC:
- **`platform`**: `claude` | `codex` | `cursor`. (Was `tool`. "claude-code"→"claude" — drop "code". Cloud is NOT a platform.)
- **`entrypoint`**: `cli` | `app` | `subagent`. (App covers desktop AND mobile — they sync. Drop the "-desktop"/"-cli"/tool-specific forms.)
- **`host`**: `local` | `cloud`. (Cloud VM / cloud tasks = cloud; everything else local.)
- **`remote_control`**: bool (default false). **`bridge_session_id`**: string|null.
- Keep `origin` (operator|delegated), `model`, `label`, `interface`, `title`, etc.

### Mapping from the CURRENT `tool`/`entrypoint` values
| current tool | current entrypoint | → platform | → entrypoint | → host |
|---|---|---|---|---|
| claude-code | cli | claude | cli | local |
| claude-code | claude-desktop | claude | app | local |
| claude-cloud | (n/a) | claude | app | cloud |
| cursor | cursor | cursor | app | local |
| codex | codex-cli | codex | cli | local |
| codex | codex-desktop | codex | app | local |
| codex | codex-subagent | codex | subagent | local |
| codex-cloud | (n/a) | codex | app | cloud |

Apply this mapping wherever entrypoints/tools are set (parsers) and referenced (labels, delegation, cloud, subagent, filters, queries).

## Label / interface format
- `interface` = `<Platform> <Entrypoint-title>` with qualifiers: `Claude CLI`, `Claude App`, `Codex App`, `Codex CLI`, `Cursor App`. Append ` (Cloud)` when host==cloud, ` (Remote Control)` when remote_control. (Keep the existing `(fable5-w-codex)` note for codex subagent/cli delegations if easy — optional.)
- `label` = `<interface> - <PrettyModel>` (unchanged shape). Examples: `Claude CLI - Fable 5`, `Codex App - GPT 5.6 Sol xhigh`, `Claude App (Cloud) - Opus 4.8`, `Claude CLI (Remote Control) - Fable 5`.

## Delegation detection (labels.py) — preserve behavior under new fields
Currently `codex_session_is_delegated` keys on entrypoint `codex-subagent`/`codex-cli`. Update to the new values: a session is delegated when `platform=='codex'` AND `entrypoint in ('cli','subagent')`, OR the originator/preamble/label signals already there. Claude `cli` stays operator. Cursor stays operator. (Codex `app` = operator.)

## Remote Control detection (Claude) — NEW
RC is a LOCAL Claude CLI session bridged to the app/web via `/rc`. `host` stays `local`. Detect from two on-disk sources (either sufficient; prefer JSONL):
1. **CLI JSONL** `~/.claude/projects/**/<id>.jsonl`: any line `"type":"bridge-session"` with non-empty `bridgeSessionId` → `remote_control=true`, `bridge_session_id=<that value>`. Extend `parse_claude_jsonl_lines`.
2. **Claude app index** `~/Library/Application Support/Claude/claude-code-sessions/**/local_*.json`: non-empty `bridgeSessionIds` array → `remote_control=true` for the linked `cliSessionId`. Extend the existing `load_claude_app_metadata()` (do NOT duplicate) to surface bridgeSessionIds, and apply during Claude session enrichment.
Do NOT parse `/rc` text (often not logged). Do NOT set host=cloud for RC. Cloud VM sessions (Cataclysm) are host=cloud, a different axis.
Fixtures on this machine: RC-yes `7224a4fe-…` (JSONL bridge-session, bridgeSessionId cse_01VnehJRZZYAXCLBNvufCG7p) and `fdbf0bdb-…` (app bridgeSessionIds); RC-no `47891de6-…`/`28d7b15e-…` (app cliSessionId but empty bridgeSessionIds), `18887b6a-…` (plain CLI).

## DB (turns/db.py) — migrate, don't lose data
- Rename column `tool`→`platform` (SQLite `ALTER TABLE sessions RENAME COLUMN tool TO platform` — guard: only if `tool` exists and `platform` doesn't). Add columns `host TEXT`, `remote_control INTEGER DEFAULT 0`, `bridge_session_id TEXT`. Bump SCHEMA_VERSION. Update the CREATE TABLE, upsert_session (params + ON CONFLICT), and EVERY query referencing `tool` (list_subagents `child.tool='codex'`→`child.platform='codex'`, cloud reads, etc.).
- ingest.py, cloud_claude.py, cloud_codex.py: set platform/host/remote_control on the session dicts (cloud collectors → platform per source, host='cloud'). The exchange/session ids are UNCHANGED (still `<tool-ish-prefix>:<id>` — keep the existing id scheme to avoid breaking links/dedup; e.g. claude-cloud: prefix stays as the ID prefix even though platform=claude/host=cloud — the id is opaque).

## Collectors (collectors/sessions.py)
- Parsers set platform/entrypoint/host/remote_control/bridge_session_id (via the mapping). The cloud merge (`collect_cloud_sessions_from_turns`) reads platform/host from turns.db. `dedupe_sessions_by_id`, `snapshot_session_db_id`, subagent-count queries: swap `tool`→`platform` where they filter.

## Frontend (web/app.js + index.html)
- `TOOL_META`→`PLATFORM_META` keyed by `claude`/`codex`/`cursor` (colors: claude=green/accent2, codex=violet, cursor=blue). Session rows/status/cards read `session.platform`.
- Session filter chips: `All | Claude | Codex | Cursor | machinery` (REMOVE "Claude Code Cloud"/"Codex Cloud" chips — cloud is now a host, not a platform). Filter matches `session.platform`.
- Show `host` and `remote_control` as small tags on session rows / in the drawer header (e.g. a `cloud` pill when host==cloud, an `RC` pill when remote_control). The label already encodes them, so keep tags subtle.
- Everywhere the code reads `session.tool` (status latest-activity, worktree cards, drawer, subagent origin), read `session.platform`. Keep `git-commit` handling in latest-activity (that's a pseudo-tool for commits — leave it or map to a `platform:"git"` sentinel).

## Tests
- Mapping: each old tool/entrypoint → correct platform/entrypoint/host.
- RC detection: JSONL bridge-session fixture → remote_control true + bridge_session_id; app bridgeSessionIds fixture → true; empty bridgeSessionIds → false; plain CLI → false.
- Delegation under new fields: codex+cli→delegated, codex+subagent→delegated, codex+app→operator, claude+cli→operator.
- DB migration: an existing db with a `tool` column migrates to `platform` preserving rows; new columns present.
- Label format for the examples above (incl. Cloud + Remote Control qualifiers).
- Keep ALL existing tests green (update assertions that referenced `tool`/old entrypoints to the new fields).

## Acceptance
- `turns_cli.py build` + `collect.py` produce sessions with platform/entrypoint/host/remote_control; the RC fixtures (7224a4fe, fdbf0bdb) show remote_control=true, host=local; cloud sessions show host=cloud, platform claude/codex; no session has the old `tool` field.
- Dashboard AI Sessions filters read All/Claude/Codex/Cursor; cloud + RC shown as tags; drawer/subagents still work.
- DB migrated in place (no data loss); all `tool`→`platform` queries updated.
- Full test suite green. Report files changed, verification (incl. the RC fixtures), deviations.
