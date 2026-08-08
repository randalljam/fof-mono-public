file: 2026-07-09_holodeck-plan.md
title: Holodeck — AI coding control center for fof-mono
last-updated: 2026-07-09_2210
ai: Claude Code - Fable 5 (fable5-w-codex orchestration)
session: `holodeck control center build`

# Holodeck — AI coding control center

A local dashboard ("holodeck") that aggregates the state of all parallel AI-coding work in fof-mono into one place: worktrees/branches, apps, specs (OpenSpec), skills, core, recent AI sessions (Claude Code / Cursor / Codex), and deploy surfaces. The primary product is the **information aggregation layer** (JSON snapshot); the web UI is a skin over it and can be redesigned later without touching collectors.


## Why
Randy runs 10+ worktrees with 17 branches in parallel across Cursor, Claude Code, and Codex. Today, answering "what's the state of everything?" means walking worktrees, reading READMEs for dev-server commands, and remembering which agent session was doing what. The holodeck answers it in one page.


## Architecture
- **Location:** `apps/holodeck/`
- **Aggregation:** `collect.py` CLI runs modular collectors (`collectors/` package), writes `apps/holodeck/data/snapshot.json` (gitignored via the root `data/` rule — session content stays out of git).
- **Server:** FastAPI (`server.py`) on port **8790** — serves the static frontend, `GET /api/snapshot`, `POST /api/refresh` (re-runs collectors, optionally per layer), `GET /api/sessions/{tool}/{id}` (lazy message preview).
- **Frontend:** `web/` — vanilla HTML/CSS/JS single page, dark styling adapted from `plans/2026-07-01_repo-snapshot-oss-discovery/index.html` (OSS-discovery worktree).
- **Curated registry:** `apps/holodeck/registry.yaml` — per-app dev command, port, URL, deploy targets. Auto-collection covers git facts; the registry covers human knowledge (which command, which URL). Merged into the apps layer.
- **Run:** `.venv/bin/python3 apps/holodeck/collect.py && .venv/bin/uvicorn apps.holodeck.server:app --port 8790` → http://127.0.0.1:8790

### Layers (snapshot.json `layers` keys)
| Layer | Source |
|-------|--------|
| `worktrees` | `git worktree list --porcelain`, per-worktree status/ahead-behind/dirty |
| `branches` | `git for-each-ref` + ahead/behind vs origin/main + `gh pr list` + `plans/git/branch-map.md` ledger |
| `apps` | filesystem scan of `apps/` + `registry.yaml` merge + git activity per path |
| `core` | `core/*.py` modules + git activity |
| `skills` | `skills/`, `.claude/skills/`, `.claude/commands/`, `agents/hermes/skills/` |
| `specs` | `apps/*/openspec/` scanned **across all worktrees** (changes + tasks.md progress + archive) |
| `sessions` | Claude Code `~/.claude/projects/*.jsonl`; Cursor globalStorage `cursorDiskKV` (`composerData:`/`bubbleId:`); Codex `~/.codex/sessions/` + `session_index.jsonl` |
| `deploy` | `fly.toml`, `.chalice/config.json`, Webflow assets, chalice deploy composite log |

### Key design points
- Collectors degrade gracefully: any failing collector records `{"error": ...}` for its layer and the rest proceed; `gh`/network optional.
- Sessions are filtered to cwd paths under known worktrees/checkouts of this repo; only first/last user-message previews (truncated) are stored in the snapshot; full bodies are fetched lazily by the server on demand.
- Cursor DB (4.7 GB) is opened read-only (`file:...?mode=ro`) and queried by key prefix — never full-scanned into memory.
- OpenSpec state comes from folder shape: active change = dir under `openspec/changes/`, archived = under `changes/archive/YYYY-MM-DD-*`; progress = `- [x]` / `- [ ]` counts in `tasks.md`.

### Build execution
Fable 5 (this session) planned and specs'd; implementation delegated to Codex (`codex exec -s workspace-write -m gpt-5.5 -c model_reasoning_effort=xhigh`) in two parallel, file-disjoint tasks:
1. **Backend** — `collectors/`, `collect.py`, `server.py`, `tests/` (spec: `2026-07-09_backend-spec.md`)
2. **Frontend** — `web/` static UI against the documented API contract (spec: `2026-07-09_frontend-spec.md`)
Fable 5 reviews both, fixes/tightens, runs tests, verifies end-to-end, commits stepwise.

### Later ideas (not this pass)
- Live deploy status (`fly status`, `chalice url`) behind an explicit "probe" button
- Launch dev servers from the dashboard (needs a permission story)
- Session search across tools; token/cost rollups from Codex `token_count` events
- Auto-refresh daemon via `core/cron` launchd helpers
