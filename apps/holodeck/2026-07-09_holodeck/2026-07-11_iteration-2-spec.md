file: 2026-07-11_iteration-2-spec.md
title: Holodeck iteration 2 — interactivity, worktree cards, stage vocabulary
last-updated: 2026-07-11_0723
ai: Claude Code - Fable 5 (fable5-w-codex orchestration)
session: `holodeck control center build`

# Holodeck iteration 2 — build spec

User feedback round 1 (2026-07-11). Two parallel, file-disjoint tasks share the contracts in this doc. Baseline: `2026-07-09_backend-spec.md` and `2026-07-09_frontend-spec.md` remain authoritative where not amended here.

Big themes: (1) the holodeck becomes **interactive** — user-editable state persisted server-side, not just reporting; (2) worktree cards become the primary work-management surface (expand/collapse, drag order, active flags, next-step/just-done fields); (3) the new PROVISIONAL registry vocabulary (`stage`, `spec_stage` — see comments in `apps/holodeck/registry.yaml`) surfaces throughout; (4) more things clickable, including viewing/editing OpenSpec files from the page.


## Shared contract A — user state store
`apps/holodeck/data/state.json` (gitignored, server-owned, atomic writes via temp file + rename):
```json
{"updated_at": "ISO",
 "next_steps": [{"id": "hex", "text": str, "done": bool, "created_at": "ISO"}],
 "worktrees": {"<branch-name>": {
    "active": bool, "order": int_or_null, "next_step": str_or_null,
    "last_done": str_or_null,
    "last_done_status": "none|needs-review|reviewed|tested",
    "notes": str_or_null}}}
```
Worktree state is keyed by **branch name** (stable across worktree moves). Missing file → empty structure, not an error. Defaults when a branch has no entry: `active=true`, everything else null/none.

## Shared contract B — new/changed API
- `GET /api/state` → the state doc (empty structure if missing).
- `PUT /api/state/worktree/{branch}` body = any subset of the worktree-state fields → shallow-merges into that branch's entry, returns the updated entry. Unknown fields → 400.
- `PUT /api/state/worktree-order` body `{"order": ["branch1", "branch2", ...]}` → sets `order` = list index for each named branch (branches not listed keep/lose order → set their order null), returns the worktrees map.
- `POST /api/next-steps` body `{"text": str}` → creates item (id = uuid4 hex[:12]), returns it.
- `PUT /api/next-steps/{id}` body subset of `{text, done}` → update, return item. 404 if unknown.
- `DELETE /api/next-steps/{id}` → `{"ok": true}`.
- `GET /api/file?path=<abs-or-repo-relative>` → `{"path": abs, "content": str, "truncated": bool}`. READ safety: resolved path must be inside repo_root OR inside one of the worktree paths recorded in the current snapshot; suffix must be one of .md .yaml .yml .json .txt .py .js .mjs .html .css .toml .sh; cap content at 200 KB (set truncated). 400/404 otherwise.
- `PUT /api/file` body `{"path": str, "content": str}` → WRITE, atomic. Same root+suffix safety AND the path must additionally match one of: contains `/openspec/` and ends with `.md` or `config.yaml`; OR ends with `apps/holodeck/registry.yaml`. Returns `{"ok": true, "path": abs}`. Anything else → 403. (This is the deliberate first write-surface: OpenSpec artifacts + the registry.)
- Startup: after app creation, if the snapshot is missing or its `generated_at` is older than 30 minutes, kick a **background thread** that runs the full collect (respecting REFRESH_LOCK; skip silently if locked). Log one line saying it started.

## Shared contract C — snapshot additions
- `worktrees[*].apps_touched`: list of app slugs this worktree's branch work touches — union of `git -C <wt> diff --name-only origin/main...HEAD -- apps/` and `git -C <wt> status --porcelain -- apps/` paths, mapped to discovered app slugs (longest-prefix match, e.g. `apps/minecraft/prism-sync/...` → `minecraft/prism-sync`). Empty list for main / clean / missing worktrees.
- `apps[*].kind` fallback for unregistered apps (never leave it absent): `.chalice/` dir → `chalice`; any `fly.toml` → `web`; any `.html` or `package.json` at root → `web`; any `.py` → `cli`; only `.md` files → `docs`; else `scripts`.
- `apps[*].stage` and `apps[*].spec_stage` already pass through from registry.yaml (PROVISIONAL vocabulary, see registry header comments: stage s0-experiment|s1-dev|s2-deployed|s3-real; spec_stage readme-only|openspec-single-spec|openspec-core|openspec-strict). Unregistered apps: omit both (frontend shows nothing).
- `specs[*].changes[*]` and `archived[*]` entries gain `"path"`: abs path of the change dir; `specs[*]` gains `"spec_files"`: list of `{domain, path}` for `specs/<domain>/spec.md` files that exist.


## Task 1 — backend (owns: apps/holodeck/server.py, apps/holodeck/collectors/, apps/holodeck/collect.py, apps/holodeck/tests/, apps/holodeck/README.md)
1. Implement contracts A, B, C. State handling in a new module `apps/holodeck/state.py` (pure helpers separated from I/O for testability).
2. `git -C` calls for apps_touched live in the worktrees collector; slug mapping helper is pure and reuses the discovered-slug list logic (import from collectors.apps).
3. Tests to add (keep the existing 9 green): state merge/defaults + next-steps CRUD helpers, worktree-order assignment, apps_touched path→slug mapping, kind fallback inference, file-path safety (read roots, write allowlist — test with tmp_path, including a rejected `../` escape and a rejected non-openspec write).
4. README: document the state file, the new endpoints (one line each), and the startup auto-refresh.
5. Style rules unchanged: no type hints, no blank lines between functions, `###` section headers, stdlib+pyyaml+fastapi/uvicorn/pytest only.

## Task 2 — frontend (owns: apps/holodeck/web/ — index.html, app.js, style.css, sample-snapshot.json, plus NEW sample-state.json)
Keep the existing visual language (CSS vars, cards, pills, filterbar). Changes:

**Top bar**
- Refresh button sits immediately to the right of the "Snapshot / generated…" text block (inline group, not pushed to the far edge).
- Status line shows relative AND absolute local time: `generated 5m ago · 2026-07-11 07:18`.

**Overview (00)**
- Brand line: `holodeck — fof-mono control center` on one line (tagline inline after the h1, muted; no separate lede paragraph).
- Exactly 5 stat tiles in one row (they must fit across on a ~1400px main column; shrink tile padding/font as needed): Worktrees (big 11, small muted subtext `3 dirty`), Branches (17, label `branches`), Open PRs, Apps, AI Sessions (count = sessions layer length, label `AI sessions`). Every tile is clickable and scrolls to its section (worktrees → #worktrees, branches → #worktrees branches table, PRs → #worktrees, apps → #apps, AI sessions → #sessions).
- Remove the "active spec changes" tile.
- Three panels under the tiles: **Next steps** (new, first), **Needs attention**, **Latest activity**. Three columns ≥1200px, stacking below.
- **Next steps panel** = editable scratchpad queue backed by the state API: text input + Add button (POST /api/next-steps, Enter submits), items listed with checkbox (PUT done — done items struck-through and sorted to bottom), text click-to-edit (PUT), small × delete (DELETE). In sample mode (`?src=sample`) load `sample-state.json`, show the list read-only with a muted "sample mode — read-only" note.
- **Latest activity** re-oriented around worktrees: each row = worktree branch name (bold mono, links to that worktree card) + platform tag (Claude Code / Cursor / Codex / git-commit, tool colors as before) + message snippet + relative time. Items with no matched worktree show the project dir name instead.

**Worktrees (01) — the core redesign**
- Cards are collapsible; collapsed by default. Click card (or a chevron) → expands to FULL WIDTH of the grid (grid-column: 1 / -1) with details; click again → collapses back. Only one needs to be expandable at a time is NOT required — allow multiple expanded.
- **Collapsed view** shows ONLY: branch name; ACTIVE/INACTIVE state; the editable trio — `next step` (prominent, gold-ish accent), `just done` (muted) with its review-status pill (none / needs-review / reviewed / tested); apps_touched chips; a small latest-session line (tool dot + relative time). NO path, NO ahead/behind, NO commit subject in collapsed view.
- **Expanded view** adds: path with copy button; ahead/behind/dirty/untracked badges; unpushed; last commit; PR pill; ledger info; recent sessions for this worktree (up to 4, clickable to the session drawer); apps_touched as links to app cards; an editable notes textarea; and the editable fields as proper inputs.
- **Editable state** (PUT /api/state/worktree/{branch} on change/blur/Enter): active toggle (switch in card corner), next_step text, last_done text, last_done_status select, notes. Inactive cards render dimmed (opacity ~.55) and sort after active ones.
- **Ordering**: drag-and-drop (HTML5 draggable, a ⠿ handle in the card header) + a "move to top" button (visible in expanded view and on hover in collapsed). Persist via PUT /api/state/worktree-order with the resulting active-card branch order. Sort: active cards by order (nulls after, then by last session/commit recency), then inactive.
- Merge state into render: `GET /api/state` fetched alongside the snapshot (sample mode: sample-state.json).
- The branches table stays below, unchanged except: PR/worktree cells clickable (worktree → scroll to card).

**Apps & Core (02)**
- Same expand/collapse pattern as worktree cards (collapsed compact, expanded full-width).
- Collapsed: name; kind pill (NEVER the word "app" — kind is always concrete now: web/cli/chalice/mod/docs/scripts/lib); `stage` pill (s0-experiment gray, s1-dev blue, s2-deployed teal, s3-real gold) and `spec_stage` pill (readme-only muted, openspec-single-spec violet outline, openspec-core violet, openspec-strict violet+bold) when present; **worktree chips** — branches whose `apps_touched` includes this slug (clickable → scroll to that worktree card); flag row (no-readme ⚠ etc.).
- Expanded: purpose, dev/test commands with copy, port/URL, deploy pills, notes, activity line, and an **OpenSpec block**: if the app has spec stores in the specs layer, list each store's spec_files, changes (with progress), archived — every file entry clickable, opening the **file drawer**.
- **File drawer** (new, generalize the session drawer pattern): opens on any spec/file link; GET /api/file, render content in a mono `<pre>` (escaped); header shows path + copy-path; if the path is writable per the PUT allowlist (client mirrors the rule: `/openspec/` + .md/config.yaml, or registry.yaml), show an Edit toggle → textarea → Save (PUT /api/file) with saved/error feedback. Read-only otherwise and in sample mode.

**Specs (03) — overhaul**
- Card per store: title = app name (links to the app card); chips: branch (→ worktree card), worktree dir name; the app's `spec_stage` pill if registered.
- Body: spec_files as clickable rows (→ file drawer); active changes with progress bars, each artifact chip clickable (→ file drawer on that file: `<change path>/proposal.md` etc.); archived in `<details>`, entries clickable too.
- Kill any dead-looking chips: everything pink/violet/gray in this section must either be a real link or plain muted text.

**AI Sessions (05)**
- Rename: nav + section header become "AI Sessions" (kicker `05 · AI worklog` can stay).

**General**
- Update `sample-snapshot.json` (add apps_touched, stage/spec_stage, specs paths/spec_files, concrete kinds) and add `sample-state.json` (a few next_steps, worktree entries with next_step/last_done/status/active variety) so `?src=sample` exercises everything read-only.
- Keep: no innerHTML with data, no external resources, null-safe rendering, no horizontal page scroll.

## Acceptance
Backend: existing 9 tests + new ones pass; `/api/state` round-trips; PUT /api/file rejects a path outside the allowlist and accepts an openspec .md under a real worktree; collect adds apps_touched (holodeck-start worktree must show `holodeck`); server auto-collects on startup when the snapshot is stale.
Frontend: `?src=sample` renders everything incl. collapsed/expanded worktree cards, editable controls disabled in sample mode; with the live API: state edits persist across reload; drag reorder persists; tiles all navigate; file drawer opens registry.yaml and an openspec file, and Edit→Save works on the openspec file.
Both: report files changed, verification performed, deviations.
