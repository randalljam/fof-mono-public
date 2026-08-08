file: 2026-07-09_frontend-spec.md
title: Holodeck frontend spec — web dashboard UI
last-updated: 2026-07-09_2215
ai: Claude Code - Fable 5
session: `holodeck control center build`

# Holodeck frontend — build spec

You are building the web UI for "holodeck", a local AI-coding control center for this monorepo. A separate backend task (running in parallel) provides a FastAPI server on port 8790 and a JSON snapshot API. You build ONLY the static frontend against the contract below. Context: `plans/2026-07-09_holodeck/2026-07-09_holodeck-plan.md`; full layer schemas: `plans/2026-07-09_holodeck/2026-07-09_backend-spec.md` (read the "Layer schemas" section — it is the authoritative data contract).


## File ownership — write ONLY these paths
- `apps/holodeck/web/index.html`
- `apps/holodeck/web/app.js`
- `apps/holodeck/web/style.css`
- `apps/holodeck/web/sample-snapshot.json`

Do NOT touch anything else (no server.py, no collectors, no registry.yaml — those belong to the parallel backend task). Do NOT run `git commit`/`push`. No external CDNs, fonts, or libraries — fully self-contained vanilla HTML/CSS/JS (ES modules fine).


## Data access
- `GET /api/snapshot` → `{generated_at, repo_root, layer_meta: {<layer>: {generated_at, took_s, error}}, layers: {worktrees, branches, apps, core, skills, specs, sessions, deploy}}`
- `POST /api/refresh` (body `{"layers": [..]}` or `{}`) → `{ok, took_s, stdout_tail}`; 409 if already refreshing
- `GET /api/sessions/{tool}/{id}` → `{messages: [{role, text, ts}]}`
- Standalone dev: if the URL has `?src=sample`, fetch `sample-snapshot.json` (relative) instead of the API and disable refresh. Also fall back to a visible error panel (not a blank page) if the API is unreachable or returns 404.
- `sample-snapshot.json`: realistic representative data conforming to the schema — ~4 worktrees, ~8 branches (one with an open PR, one merged), ~8 apps (mix of web/cli/chalice, one with port collision, some unregistered/no-readme), 3 core modules, ~6 skills across sources, 1 spec store with an active change (tasks 3/7) and one archived, ~9 sessions across the three tools, ~6 deploy entries, and one layer_meta error (e.g. sessions) to exercise the warning UI.

## Visual design
Adapt the styling of `/Users/randytrue/Documents/Code/claude-repo-analysis-oss-discovery-iiu2a6/plans/2026-07-01_repo-snapshot-oss-discovery/index.html` — read that file and reuse its look: same CSS variables (`--bg:#0d1117`, `--panel:#161d29`, `--border:#243040`, `--ink:#e6edf3`, `--muted:#9aa7b6`, `--accent:#58a6ff`, `--accent2:#7ee787`, `--gold:#f0c674`, `--pink:#ff7b9c`, `--violet:#bc8cff`, `--teal:#39d3c3`, `--red:#ff6b6b`), same fonts (system sans + ui-monospace), sticky left sidebar nav with numbered navlinks, `.stat` tiles, `.card` grids with hover lift, `.pill`/`.tag` chips, `.filterbar` with `.fbtn` buttons + search input, table styling, `.callout` boxes. Layout: `grid-template-columns: 250px 1fr`, max-width 1400px, responsive collapse under 880px. Title/brand: `holo<span accent>deck</span>`, subtitle "fof-mono control center".

Tool identity colors (used consistently for session badges and dots): Claude Code = `--accent2` (green), Cursor = `--accent` (blue), Codex = `--violet`.


## Views (sidebar sections)
Single page, all sections rendered from the snapshot; sidebar navlinks scroll to sections and highlight on scroll (IntersectionObserver).

**Top bar (sticky, above content):** "snapshot generated <relative time>" + a Refresh button (POST /api/refresh, spinner while running, re-fetch snapshot after; show stdout_tail on failure). If any `layer_meta[*].error` — an amber warning strip listing the failing layers. If snapshot missing → full-page hint showing the collect command.

**00 Overview**
- Stat tiles: worktrees, dirty worktrees, branches ahead of main, open PRs, active spec changes, apps, sessions last 48h.
- "Needs attention" panel — computed client-side, each item a one-liner with a colored dot and a link to its section:
  - worktree dirty or with unpushed commits (gold)
  - worktree/branch behind origin/main by >10 (violet)
  - worktree missing on disk (red)
  - two apps sharing the same port (pink)
  - active spec change with 0 tasks done (teal)
  - layer errors (red)
  - If nothing: "All quiet on the holodeck." in muted text.
- "Latest activity" mini-feed: 8 most recent items merged from sessions (by last_activity) and worktree last commits, each with tool/branch chip + relative time.

**01 Worktrees & Branches**
- Worktree cards: branch name (mono, prominent), path (click-to-copy), ahead/behind badges (`↑n ↓n`, gold when ahead, violet when behind), dirty/untracked counts, last commit subject + relative date, PR pill if that branch has one (OPEN green / MERGED violet / CLOSED red / DRAFT muted), latest session for that worktree (tool dot + title + relative time) — match sessions by `worktree` field.
- Branches table below (branches without a worktree included): name, tip subject, date, ahead/behind, worktree?, PR, ledger parent/purpose if present.

**02 Apps & Core**
- Filter bar: All / by `kind` / by tag chips + free-text search (name, purpose, slug).
- App cards: name + kind pill + tags, purpose, `dev_command` in a mono block with a copy button, port badge + `local_url` as a real link, `test_command` copy line if present, deploy pills (fly/chalice/webflow), notes in italic muted, flags row (no-readme ⚠, no-tests, openspec ✓, unregistered = dashed border), last activity ("3 commits in 30d · last 2d ago").
- Core subsection: compact table of modules — name, description, commits_30d, last commit relative date.

**03 Specs**
- One card per spec store: app name + branch/worktree pill; active changes each with a progress bar (`tasks_done/tasks_total`, teal fill), artifact chips (proposal/design/tasks/deltas); archived changes in a collapsed `<details>` list with dates; spec_domains as tags. Empty state: explain OpenSpec is trialed on autolearner (feature/openspec-skills branch) and stores appear here once scanned.

**04 Skills**
- Grouped by category; each skill: name (mono), description, source pill (shared / claude-skill / claude-command / hermes). Count per category in the group header.

**05 Sessions**
- Filter bar: All / Claude Code / Cursor / Codex + search over title/first_user.
- Rows (table or list): tool dot + name, title (fallback: first_user truncated), project shortened to worktree dir name, branch chip, messages count, relative last-activity. Click a row → slide-over panel (right side, ~560px, dark panel, ESC/backdrop closes) that fetches `/api/sessions/{tool}/{id}` and renders the message list — user messages accent-bordered, assistant muted; show a spinner and an error state.

**06 Deploy**
- Grouped by kind: Fly.io / AWS Chalice / Webflow / S3. Each entry: name (mono), owning app link (scroll to its card), command with copy button, url as link, config_path muted, last_deploy if known. Callout at top: "Webflow → AWS migration in progress (feature/web-site-transcript-pages)".


## Behaviors & quality bar
- Relative-time helper ("2h ago", "3d ago"); absolute ISO on hover via `title`.
- Copy-to-clipboard helper with a brief "copied" flash on the button.
- All rendering null-safe: every schema field can be null/missing — never render "undefined"/"null" or throw; omit gracefully.
- No horizontal page scroll; long mono strings wrap or scroll within their own block.
- Keep it fast: render from one snapshot object, no per-row fetches except the session slide-over.
- Escape all user/session text before inserting into the DOM (use textContent, never innerHTML with data).

## Acceptance
1. Opening `web/index.html` via the server (or any static server with `?src=sample`) renders all 7 sections from sample-snapshot.json with no console errors.
2. Filters, search, copy buttons, refresh flow, and the session slide-over work.
3. Null-heavy data renders cleanly (delete random fields from sample data to check).
4. Self-contained: zero external network requests.

When done, print a report: files created, how you verified (which checks you ran with `?src=sample`), any deviations from this spec and why.
