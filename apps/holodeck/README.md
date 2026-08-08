**Holodeck**

Holodeck is a local backend for the fof-mono AI-coding control center. It aggregates worktrees, branches, apps, core modules, skills, OpenSpec stores, recent AI sessions, and deploy surfaces into `apps/holodeck/data/snapshot.json`, then serves that snapshot through a small FastAPI app.

The dashboard is one primary interface: **Active AI** (recent agent turns as state-lit tiles in a 3×3 grid — blue `thinking`, green `done`, yellow `needs-you`, red reserved — each tile title-barred with its project's worktree color, with Claude/Codex/Cursor filter checkboxes so big important turns stay visible above day-to-day chatter), **To-do** (the global list; items promoted from a work card carry that project's colored tag), **Active Work** (cards for worktrees marked active, with live turn badge, agent lights, per-card to-dos with reorder and promote-to-global, and a "go to window" button shown only when the worktree has an open Cursor window), and **Universe** (parked worktrees with "where I left off" context, branches without a checkout, and apps — each offering a copy-to-clipboard `create-worktree` skill prompt when no live worktree exists). Branches, Core, Skills, Specs, and Deploy remain as demoted "More" sections; the AI Sessions table stays as the search surface.


## Run
Collect a snapshot:
```bash
.venv/bin/python3 apps/holodeck/collect.py
```
Serve the API and web shell on port 8790:
```bash
.venv/bin/python3 apps/holodeck/server.py
```
Open `http://127.0.0.1:8790`. If Holodeck is already running, the launcher asks whether to kill and restart it; answer `y` instead of running `pkill` manually. You can still start with uvicorn directly when you need reload flags:
```bash
.venv/bin/uvicorn apps.holodeck.server:app --host 127.0.0.1 --port 8790
```

The web dashboard lives in `apps/holodeck/web/` (vanilla HTML/CSS/JS, no build step). For standalone frontend work without the API, serve `web/` statically and open `index.html?src=sample` to render from `sample-snapshot.json`.

Privacy: `apps/holodeck/data/` is gitignored via the root `data/` rule. `snapshot.json` includes AI-session previews; `state.json` stores user-edited next steps and per-worktree card state, and `todo-archive.md` stores archived to-do entries. Session content never enters git. The Cursor database is opened read-only; the Refresh button re-runs the collectors on demand.

AI session retrieval (Cursor SQLite, Claude Code JSONL, Codex JSONL, fields, timestamps, and what Holodeck does *not* infer): `apps/holodeck/AI-SESSIONS.md`. Consumer ChatGPT / Claude.ai chats: WIP skill only (`skills/media/consumer-chat-md/README.md`) — not live end-to-end, not in `turns.db`.


## Turns DB
The turns database correlates AI-coding exchanges with recent git commits. It lives at `apps/holodeck/data/turns.db`, which is gitignored. Rebuilds upsert stable session, exchange, commit, and link rows; digest rows are preserved across rebuilds. By default, builds ingest full Codex cloud task transcripts through the ChatGPT wham API using the Codex CLI access token in `~/.codex/auth.json`, then fall back to the older `codex cloud list --json` metadata/diff path when that token or API is unavailable. Claude Code cloud sessions are ingested from browser exports (Cloudflare blocks server-side `/v1/code` access).

**Agent rule:** backup `turns.db` before mutating it — see `apps/holodeck/AGENTS.md`.

Build or refresh the DB, including a bounded auto-digest pass for recent operator turns:
```bash
.venv/bin/python3 apps/holodeck/turns_cli.py build
```

Skip auto-digest when you only want ingestion/correlation:
```bash
.venv/bin/python3 apps/holodeck/turns_cli.py build --no-digest
```

Skip all cloud ingestion:
```bash
.venv/bin/python3 apps/holodeck/turns_cli.py build --no-cloud
```

### Cloud auth (Codex vs Claude)
These are two different systems:

| Source | How Holodeck gets it | What to do when the banner complains |
|--------|----------------------|--------------------------------------|
| **Codex cloud** | Live API via `~/.codex/auth.json` (`tokens.access_token`) | Run `codex login` (or `codex cloud list` to refresh). No manual export. |
| **Claude cloud** | Browser export only (Cloudflare blocks automation) | Use the Holodeck **Copy Claude export snippet** button, paste in the DevTools console on `https://claude.ai/code`, save `holodeck-claude-cloud-export.json` to `~/Downloads`, then hit **Refresh**. |

Claude export steps in detail:
1. In Holodeck, click **Copy Claude export snippet** (or copy `apps/holodeck/web/claude-cloud-export-snippet.js`).
2. Open `https://claude.ai/code` while logged in → DevTools → Console → paste → Enter.
3. The page downloads `holodeck-claude-cloud-export.json` into `~/Downloads`.
4. Hit **Refresh** in Holodeck. Refresh moves matching `~/Downloads/holodeck-claude-cloud*.json` / `holodeck-cc-*.json` files into `~/Documents/Code/_LOCAL_FILES/fof-mono/ai-sessions/cloud_claude/` and rebuilds the turns DB.

`/api/cloud-status` reports Claude as `ok` when an export file is already present (even though live Claude API probes get Cloudflare 403). Re-export when you want fresher Claude cloud sessions.

Legacy alternatives (usually unnecessary): `turns_cli.py cloud-claude-login` (Playwright profile at `~/.holodeck/playwright-claude`) and `CLAUDE_AI_SESSION_KEY` in `.env`. Cloudflare currently blocks those for reliable live fetch; prefer the browser export.

Codex cloud ingest reads only `tokens.access_token` from `~/.codex/auth.json` and never logs it. If the wham API returns 401, Holodeck skips Codex cloud ingest with the note to run `codex cloud list` or `codex login` to refresh the token; refresh-token handling is intentionally out of scope.

Backfill missing operator exchange digests explicitly after a build:
```bash
.venv/bin/python3 apps/holodeck/turns_cli.py build --digest --limit 3
```

Digest generation loads keys from the repo `.env`, preferring `ANTHROPIC_API_KEY_LOCAL` and falling back to `OPENAI_API_KEY_LOCAL`. Without a key, builds still ingest and correlate turns; digest generation skips with a clear message. Auto-digest covers undigested operator exchanges from the last 48 hours, capped at 25 per run. Digests are never generated by `collect.py`.

### History-purge commit hash map
After the 2026-07-22 git history rewrite, GitHub PR commit SHAs stay on the pre-purge hashes. Holodeck stores the old→new lookup in `turns.db` (`commit_hash_map`, plus `branch_tip_map`) loaded from:
- `docs/git/2026-07-22_history-purge-commit-map.tsv`
- `docs/git/2026-07-22_history-purge-branch-tip-map.tsv`

`turns_cli.py build` loads the maps and remaps any stored `commits`/`links` rows still on old SHAs. To load/remap without a full rebuild:
```bash
.venv/bin/python3 apps/holodeck/turns_cli.py load-hash-map
.venv/bin/python3 apps/holodeck/turns_cli.py resolve-sha <old-or-new-sha>
```


## API
`GET /api/snapshot` — return the latest collected snapshot.
`GET /api/branch-commits?branch=<name>&skip=<n>&limit=<n>` — return paged full-message commits for a branch present in the current snapshot.
`GET /api/commit-hash-map/resolve/{sha}?direction=to_new` — resolve a pre/post-purge commit SHA (`to_new`, `to_old`, or `either`) using the lookup table in `turns.db`.
`GET /api/agents?hours=<n>&limit=<n>` — return per-session agent status for recent operator sessions: the latest exchange of each session classified as `thinking` (unanswered, fresh), `done` (answered, or session-end command), or `needs-you` (unanswered and stale — the data signature of an AI intentionally paused for user interaction, i.e. a popped question or run-command permission request). There is deliberately no semantic parsing of response text; `error` is reserved for a future classification phase.
`GET /api/turns?branch=<name>&limit=<n>` — return newest operator exchange summaries with digests and linked commits; add `include=delegated` to include machinery/delegated exchanges.
`GET /api/turns/status` — return the latest operator turn state per active worktree/branch.
`GET /api/turns/exchange/{exchange_id}` — return full user and assistant text for one exchange.
`POST /api/turns/refresh` — rebuild the turns DB and start a recent-operator auto-digest pass in the background.
`POST /api/turns/digest/{exchange_id}` — generate one missing digest on demand.
`POST /api/refresh` — run collectors, optionally with `{"layers": ["sessions"]}`.
`GET /api/refresh/status` — whether a collect/refresh (including startup auto-refresh) currently holds the refresh lock.
`POST /api/focus` — focus the already-open Cursor window for an authorized live worktree path. This action is macOS-only and requires the fixed `X-Holodeck-Action: focus` header; see **macOS window focus** below.
`GET /api/state` — return `apps/holodeck/data/state.json`, or an empty state document if missing.
`PUT /api/state/worktree/{branch}` — shallow-merge worktree card fields for a branch, including `active`, `deactivated_at`, `primary_interface`, and per-worktree `steps`; legacy `submitted_via`, `submitted_at`, and `ai_responded` fields are still accepted.
`PUT /api/state/worktree-order` — persist branch display order from `{"order": ["branch"]}`.
`POST /api/next-steps` — create a next-step item from `{"text": "..."}`.
`PUT /api/next-steps/{id}` — update `text` and/or `done` for a next-step item.
`PUT /api/next-steps-order` — reorder global next-step items from `{"order": ["id"]}`; omitted known ids keep relative order at the end.
`POST /api/next-steps/{id}/archive` — remove a next-step item from state and append it to `apps/holodeck/data/todo-archive.md`.
`DELETE /api/next-steps/{id}` — delete a next-step item.
`GET /api/file?path=<path>` — read a small text/code file under the repo or a known worktree.
`PUT /api/file` — atomically write allowlisted OpenSpec markdown/config files, `apps/holodeck/registry.yaml`, or `apps/holodeck/worktree-colors.yaml`.

On server startup, if `snapshot.json` is missing or older than 30 minutes, the server starts one background full refresh when the refresh lock is available.


## macOS window focus
When a snapshot reports `cursor_open: true`, the `open in Cursor` pill is a button. A click asks the live operating system to find, restore, and raise the unique matching Cursor window; it never opens a closed worktree. The snapshot controls whether the button is initially rendered, but live Cursor windows are the source of truth at click time, so stale, missing, or ambiguous matches return an inline error and can be resolved by refreshing the Worktrees layer.

The focus route accepts only a Cursor target and a canonical path that matches the current output of `git worktree list`. It verifies a loopback peer and Host, same-origin browser metadata, JSON content type, and the fixed action header. Browser input cannot select a script, command, process, bundle id, or arbitrary window title. Keep Holodeck bound to `127.0.0.1`; remote-host use is unsupported.

Cursor focusing uses the reusable adapter in `apps/mac/window_activation.py` and needs macOS Accessibility permission for the app that launched Holodeck; macOS may also request Automation permission. Approve the launcher shown under System Settings → Privacy & Security → Accessibility or Automation, then retry. The adapter handles ordinary windows on other Spaces with a bounded transition/reverification loop and never reports success unless the requested standard window becomes Cursor's unique main match while Cursor is frontmost. When live worktrees share a folder basename, Holodeck omits that ambiguous title fallback and requires path evidence, failing closed if it is unavailable. Multi-root windows may use a unique `.code-workspace` title only when the live document is inside a folder parsed from that workspace file (or no usable document path is exposed). Full-screen behavior remains dependent on the user's macOS Space-switching settings.


## Layers
The snapshot layers are `worktrees`, `branches`, `apps`, `core`, `skills`, `specs`, `sessions`, and `deploy`.
List layers:
```bash
.venv/bin/python3 apps/holodeck/collect.py --list
```
Refresh one or more layers while preserving the rest of the snapshot:
```bash
.venv/bin/python3 apps/holodeck/collect.py --layer sessions --layer specs
```


## Registry
`apps/holodeck/registry.yaml` stores curated app facts such as display name, purpose, dev command, port, local URL, test command, deploy entries, notes, and tags. The collector merges registered entries with auto-discovered app directories under `apps/`; registry fields win for human-authored facts, while filesystem and git facts are computed on each run.

`apps/holodeck/worktree-colors.yaml` stores stable title-bar colors for worktree cards and for Cursor windows. Holodeck reads rules when rendering cards; `create-worktree` `apply-color` writes matching `titleBar.*` lines into each worktree's `.vscode/settings.json` when the folder slug matches a rule. Cursor open windows are detected from `windowsState.openedWindows` in Cursor's `storage.json` (not the stale `backupWorkspaces` restore list).

Branch parent and purpose come only from durable branch-lineage commits described by
`skills/repo-ops/branch-lineage-record/README.md`. Holodeck scans each branch's first-parent
history newest-first, ignores inherited records whose `Branch` differs, and validates the
newest applicable record before accepting it. A v2 record carries stable lineage and record
UUIDs across corrections and history rewrites; existing v1 records remain supported through
the documented compatibility mapping.

Only `structurally-verified` branch-start records and `evidence-validated` approved late
records project an accepted parent into the dashboard. `pending`, `invalid`, `unsupported`,
`missing`, `parent-ref-missing`, and `ref-diverged` states remain visible with their declared
facts and validation errors, but never render a declared parent as accepted truth.


## Tests
Run the Holodeck and reusable macOS activation tests:
```bash
.venv/bin/python3 -m pytest apps/holodeck/tests apps/mac/tests -q
```
The focus tests use mocked subprocesses and do not trigger macOS permission prompts. `test_web.py` checks that `app.js` parses as an ES module (catches syntax errors that blank the dashboard), required dashboard symbols exist, sample snapshot shape is valid, and basic HTTP routes respond.
