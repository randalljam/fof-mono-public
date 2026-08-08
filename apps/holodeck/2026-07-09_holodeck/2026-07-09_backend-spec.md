file: 2026-07-09_backend-spec.md
title: Holodeck backend spec — collectors, collect.py, server, tests
last-updated: 2026-07-09_2215
ai: Claude Code - Fable 5
session: `holodeck control center build`

# Holodeck backend — build spec

You are building the aggregation backend for "holodeck", a local AI-coding control center for this monorepo (fof-mono). It aggregates the state of parallel work — git worktrees/branches, apps, OpenSpec specs, skills, recent AI chat sessions (Claude Code / Cursor / Codex), deploy surfaces — into one JSON snapshot served by a small FastAPI app. Read `plans/2026-07-09_holodeck/2026-07-09_holodeck-plan.md` for context.


## File ownership — write ONLY these paths
- `apps/holodeck/collect.py`
- `apps/holodeck/collectors/` (new package: `__init__.py` + one module per collector)
- `apps/holodeck/server.py`
- `apps/holodeck/tests/` (pytest tests + fixture files)
- `apps/holodeck/README.md`
- `apps/holodeck/data/` will be created at runtime by collect.py (it is gitignored by the root `data/` rule — do NOT add source code there)

Do NOT modify `apps/holodeck/registry.yaml` (already authored), any file outside `apps/holodeck/`, or `.gitignore`. Do NOT run `git commit`, `git push`, or any branch operation. Do NOT add new pip dependencies — allowed imports: Python 3.12 stdlib (incl. `sqlite3`, `tomllib`, `json`, `subprocess`, `pathlib`, `datetime`), `yaml` (pyyaml), `fastapi`, `uvicorn`, `pytest`. Interpreter: `.venv/bin/python3` from repo root.


## Repo Python style (mandatory)
- NO type hints in function definitions.
- NO blank lines between functions — functions immediately adjacent.
- Exactly ONE blank line before section comment headers: `### Section Name`.
- Docstrings are fine. Keep modules readable with `### section` groupings.


## Snapshot contract
`collect.py` writes `apps/holodeck/data/snapshot.json`:

```json
{
  "generated_at": "ISO-8601 local time with offset",
  "repo_root": "/abs/path/of/this/checkout",
  "layer_meta": {"<layer>": {"generated_at": "...", "took_s": 1.2, "error": null}},
  "layers": {
    "worktrees": [], "branches": [], "apps": [], "core": [],
    "skills": [], "specs": [], "sessions": [], "deploy": []
  }
}
```

A failing collector must NOT abort the run: catch exceptions, set `layer_meta[layer].error` to the message, set the layer to `[]`, continue.

### CLI
- `.venv/bin/python3 apps/holodeck/collect.py` — run all collectors, write snapshot.
- `--layer <name>` (repeatable) — refresh only those layers, merging into the existing snapshot file (other layers and their layer_meta preserved).
- `--list` — print layer names.
- Print a one-line summary per layer (count, seconds, error if any).

### Layer schemas

**worktrees** — from `git worktree list --porcelain` run at the repo root (captures ALL worktrees of this repo, including ones outside ~/Documents/Code, e.g. `~/.codex/worktrees/0013/fof-mono`):
```json
{"path": str, "branch": str, "head": "short sha", "is_current": bool,
 "missing": bool,
 "last_commit": {"sha": str, "subject": str, "date": "ISO", "author": str},
 "dirty": int, "untracked": int,
 "ahead_main": int, "behind_main": int,
 "upstream": "origin/x or null", "unpushed": int_or_null}
```
- dirty/untracked from `git -C <path> status --porcelain` (untracked = `??` lines; dirty = the rest).
- ahead/behind vs `origin/main`: `git -C <path> rev-list --left-right --count origin/main...HEAD` → behind_main, ahead_main.
- unpushed: `git -C <path> rev-list --count @{upstream}..HEAD` (null if no upstream).
- missing=true if the worktree dir doesn't exist (still listed by git; skip the per-dir commands).

**branches** — all branches, local and remote (deduped by short name, `origin/` stripped; skip HEAD pointer):
```json
{"name": str, "tip": "short sha", "subject": str, "date": "ISO", "author": str,
 "local": bool, "remote": bool, "worktree": str_or_null,
 "ahead_main": int, "behind_main": int,
 "pr": {"number": int, "title": str, "state": "OPEN|MERGED|CLOSED", "is_draft": bool, "url": str, "updated_at": "ISO"} or null,
 "ledger": {"parent": str, "fork_base": str, "purpose": str} or null}
```
- Use `git for-each-ref` with a format string over `refs/heads` and `refs/remotes/origin`.
- PRs: `gh pr list --state all --limit 60 --json number,title,state,isDraft,headRefName,url,updatedAt` with a 15s timeout; on any failure set every `pr` to null and record a note in layer_meta error (but keep the branch data — a gh failure must not empty the layer).
- ledger: parse `plans/git/branch-map.md` — sections start `## <branch-name>`, bullets like `- **Parent:** \`origin/main\``, `- **Fork-base:** \`sha\``, `- **Purpose:** text`. Best-effort; missing file → all null.

**apps** — union of: entries in `apps/holodeck/registry.yaml` (key `apps`, each has `slug`) and auto-discovered app dirs. Auto-discovery: first-level dirs under `apps/`, and for umbrella dirs `minecraft`, `family`, `games`, `qrag`, `education`, `transcription` also their second-level dirs (an umbrella dir that has registered/discovered children is not itself an app). Registry fields pass through verbatim (`name, purpose, kind, dev_command, port, local_url, test_command, deploy, notes, tags`). Computed fields:
```json
{"slug": "path relative to apps/", "path": "apps/<slug>", "registered": bool,
 "has_readme": bool, "has_tests": bool, "has_agents_md": bool, "openspec": bool,
 "last_commit_date": "ISO or null", "commits_30d": int}
```
- has_readme: any README*.md at the app root (case-insensitive). has_tests: a `tests/` dir or `test_*.py` / `*.test.mjs` files anywhere in the app (limit search depth 3). openspec: `openspec/` dir exists at app root in THIS checkout.
- git activity: `git log -1 --format=%cI -- <path>` and `git rev-list --count --since=30.days HEAD -- <path>`.

**core** — for each `core/*.py` (skip `__init__.py`) plus `core/cron`:
```json
{"module": str, "description": str_or_null, "last_commit_date": "ISO or null", "commits_30d": int}
```
- description: first `#` comment line or first docstring line in the file's first 10 lines, else null.

**skills** —
```json
{"category": str, "name": str, "description": str_or_null, "path": str,
 "source": "shared|claude-skill|claude-command|hermes"}
```
- shared: `skills/<category>/<name>/README.md` — description from the first non-header, non-`file:`/`title:` content line, or a `description:` header line if present.
- claude-skill: `.claude/skills/<name>/SKILL.md` (description from frontmatter `description:`); claude-command: `.claude/commands/<name>.md` (category "commands"); hermes: `agents/hermes/skills/<cat>/<name>/SKILL.md`.

**specs** — OpenSpec stores scanned ACROSS ALL WORKTREES (iterate the worktrees layer's existing paths; skip missing). For each worktree, glob `apps/*/openspec/` and `apps/*/*/openspec/`:
```json
{"worktree": str, "branch": str, "app": "slug relative to apps/", "store_path": str,
 "spec_domains": [str],
 "changes": [{"name": str, "artifacts": [str], "tasks_total": int, "tasks_done": int}],
 "archived": [{"name": str, "date": "YYYY-MM-DD or null"}]}
```
- spec_domains: subdir names of `openspec/specs/`. changes: subdirs of `openspec/changes/` except `archive`; artifacts = which of proposal.md, design.md, tasks.md exist plus spec delta dirs under `specs/`; tasks counted from `tasks.md`: done = lines matching `- [x]`, total = done + `- [ ]`. archived: subdirs of `changes/archive/`, date parsed from a leading `YYYY-MM-DD-` prefix.
- Dedupe stores that appear identically in multiple worktrees on the same branch? No — report each (worktree, store) pair; the UI groups.

**sessions** — most recent sessions per tool, FILTERED to this repo: keep a session only if its project/cwd path matches one of the worktree paths (prefix match) or `/Users/randytrue/Documents/Code/fof-mono`. Cap 40 per tool, sorted by last_activity desc. Common shape:
```json
{"tool": "claude-code|cursor|codex", "id": str, "title": str_or_null,
 "project": "abs path", "worktree": "matched worktree path or null", "branch": str_or_null,
 "started": "ISO or null", "last_activity": "ISO or null", "messages": int_or_null,
 "first_user": "str <=240 chars or null", "last_user": "str <=240 chars or null",
 "source_path": "abs path to the session file, or cursor composerId"}
```
Extraction recipes (validated on this machine):
- **Claude Code**: `~/.claude/projects/<slug>/<sessionId>.jsonl` (JSON Lines). Only consider files with mtime in the last 30 days, newest 40 by mtime. The first lines are config stubs with null cwd — the authoritative `cwd`, `gitBranch`, `timestamp` fields live on `user`/`assistant` lines. Title: last line with `.type=="ai-title"` → `.title`. first_user/last_user: first/last `.type=="user"` line's `message.content` (string, or list of blocks → join text parts). Skip user messages that start with `<` (injected context like `<system-reminder>` / `<command-message>`) when picking first/last real message; fall back to the raw first/last if all are injected. messages = count of user+assistant lines. last_activity = max timestamp (fallback: file mtime). For files >20 MB, parse only the first 200 and last 400 lines (title/last-user live near the end) and use mtime.
- **Cursor**: sqlite `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb` opened READ-ONLY via URI `file:...?mode=ro` (`sqlite3.connect(uri, uri=True, timeout=5)`). `SELECT key, value FROM cursorDiskKV WHERE key LIKE 'composerData:%'`. Each value is JSON: id=`composerId`, title=`name`, project=`workspaceIdentifier.uri.path` (may need `fsPath` fallback; skip entries without it), started=`createdAt` (epoch ms), last_activity=`lastUpdatedAt` (epoch ms), messages=len(`fullConversationHeadersOnly`). Filter to repo paths FIRST, then for only the 15 most recent fetch first/last user message: headers with `type==1` are user; fetch `bubbleId:<composerId>:<bubbleId>` rows and read `.text` (may be empty — walk to the next user header until non-empty). branch: null. The DB is 4.7 GB — never SELECT without the key-prefix WHERE clause.
- **Codex**: `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` — line 1 is `type=="session_meta"`; its `payload` has `id`/`session_id`, `timestamp` (start), `cwd`, `git.branch`, `originator`. Titles come from `~/.codex/session_index.jsonl` (`{id, thread_name, updated_at}` per line) joined by id. Consider only files from the last 30 days (walk the dated dirs), newest 40 by mtime. first_user/last_user: lines with `.type=="response_item"` and `.payload.role=="user"`, text at `.payload.content[0].text`; skip texts starting with `<` (injected context). last_activity = file mtime.

**deploy** — union of registry `deploy` entries (carry `app_slug` = registry slug) and auto-discovered:
```json
{"surface": str, "kind": "fly|chalice|webflow|s3", "app_slug": str_or_null,
 "name": str, "command": str_or_null, "url": str_or_null,
 "config_path": str_or_null, "last_deploy": str_or_null}
```
- fly: glob `apps/**/fly.toml` (depth ≤4) → parse with tomllib, `app` key.
- chalice: glob `apps/**/.chalice/config.json` and `web-shared/aws_chalice/*/.chalice/config.json` → `app_name`, stages.
- last_deploy: best-effort parse of `web-shared/aws_chalice/chalicelib_mirror_deploy_composite_log.md` — find the most recent date-like heading/line mentioning the app name; null if unsure.
- Dedupe against registry entries by (kind, name) — registry wins (it has command/url).


## Server — `apps/holodeck/server.py`
FastAPI app named `app`, run as `.venv/bin/uvicorn apps.holodeck.server:app --port 8790` from repo root (also support `python3 apps/holodeck/server.py` via `uvicorn.run` main guard, port 8790).
- `GET /` → `web/index.html`; mount `apps/holodeck/web` as static at `/static` (the web dir may not exist yet — guard with a friendly 200 text if missing).
- `GET /api/snapshot` → contents of data/snapshot.json; if missing, JSON `{"error": "no snapshot — run collect.py or POST /api/refresh"}` with status 404.
- `POST /api/refresh` body `{"layers": ["sessions", ...]}` (or empty/no body = all) → runs collect.py as a subprocess with the same interpreter (`sys.executable`), returns `{"ok": bool, "took_s": float, "stdout_tail": str}`. Concurrency guard: reject with 409 if a refresh is already running (simple module-level lock).
- `GET /api/sessions/{tool}/{session_id}` → lazy full-ish detail for one session: `{"messages": [{"role": "user|assistant", "text": "<=2000 chars", "ts": iso_or_null}]}` capped at 200 messages. Look up `source_path`/id from the snapshot's sessions layer. claude-code/codex: re-read the JSONL; cursor: fetch bubbles by `fullConversationHeadersOnly` order (skip empty texts). Path safety: resolve and require the source_path to be under `~/.claude/projects`, `~/.codex/sessions`, or be a cursor composerId — never accept arbitrary paths from the URL.

CORS: not needed (same origin). No auth (localhost tool).


## Structure for testability
Split every collector into pure parse functions (take strings/dicts, return dicts) and thin gather functions (do subprocess/file/sqlite I/O). Tests target the pure functions with fixture data — no git, no network, no real home-dir access in tests.

Required tests (pytest, `apps/holodeck/tests/`, fixtures inline or in `apps/holodeck/tests/fixtures/`):
1. worktree porcelain parsing (multi-worktree fixture incl. detached/missing)
2. branch-map.md ledger parsing
3. tasks.md checkbox counting (incl. nested lists, `- [X]` uppercase)
4. registry merge: registered + unregistered apps, umbrella second-level discovery
5. Claude Code JSONL parsing: fixture with config stubs, ai-title, injected `<system-reminder>` user line skipped for first_user
6. Codex session_meta + user-message extraction fixture
7. Cursor composerData row → session dict (pure function on parsed JSON)
8. fly.toml + chalice config parsing
9. snapshot merge logic for `--layer` partial refresh
Run them: `.venv/bin/python3 -m pytest apps/holodeck/tests -q` — must pass.


## README — `apps/holodeck/README.md`
Short: what holodeck is, run commands (collect, serve, port 8790, URL), layer list, how registry.yaml works, test command. Follow repo markdown rules: two blank lines before `##` headings, no blank line after a heading, no semantic line wrapping.


## Acceptance
1. `.venv/bin/python3 apps/holodeck/collect.py` completes with all 8 layers non-erroring on this machine and prints per-layer counts.
2. `--layer sessions` refreshes just that layer, preserving the rest.
3. Server starts; `/api/snapshot` returns the snapshot; `/api/refresh` re-collects; a session detail endpoint returns messages for a real recent Claude Code session.
4. All pytest tests pass.
5. Style rules respected (no type hints, no blank lines between functions, `###` section headers).

When done, print a report: files created, layer counts from a real collect run, test results, any deviations from this spec and why.
