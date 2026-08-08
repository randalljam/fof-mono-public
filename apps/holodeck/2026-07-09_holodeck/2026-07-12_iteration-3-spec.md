file: 2026-07-12_iteration-3-spec.md
title: Holodeck iteration 3 — dev-cycle tracker, branches section, session tooltips
last-updated: 2026-07-12_0550
ai: Claude Code - Fable 5 (fable5-w-codex orchestration)
session: `holodeck control center build`

# Holodeck iteration 3 — build spec

User feedback round 2 (2026-07-12). Two parallel, file-disjoint tasks. Baselines: `2026-07-09_backend-spec.md`, `2026-07-11_iteration-2-spec.md` remain authoritative where not amended.

**PRESERVE recent work from other sessions** (commits 33ae6d6..2d0ed79): worktree title-bar colors (`worktree-colors.yaml`, `title_bar` field), Cursor-open detection (`cursor-closed` card dimming), codex workspace integration, and `tests/test_web.py` smoke tests. Extend, never regress. Read the current code first.

Core concept this round: the user runs an **iterative dev cycle** per worktree — voice-dictate a prompt → submit via some harness → wait (2–30 min) → AI responds with commits + a summary → read it → decide (test / follow-up prompt / more features). The worktree cards must show where each worktree is in that cycle, manually set for now (auto-detection later).


## Shared contract A — state fields (extends iteration-2 state store)
Worktree state gains three fields (keep the old next_step/last_done/last_done_status/notes fields valid in the store — the UI stops showing the first three, but do not break existing data):
- `submitted_via`: one of `cursor | claude-cli | claude-app | codex-cli | codex-app` or null
- `submitted_at`: ISO string or null (client-supplied)
- `ai_responded`: bool (default false)
Validation in `state.py` mirrors existing patterns; unknown values → 400 via the existing PUT route.

## Shared contract B — branch commits API
`GET /api/branch-commits?branch=<name>&skip=<int>&limit=<int>` (skip default 0; limit default 20, max 100):
- Branch must exist in the current snapshot's branches layer (404 otherwise — this is also the injection guard; never pass unvalidated input to git).
- Resolve ref: try `refs/heads/<branch>`, then `refs/remotes/origin/<branch>` via `git rev-parse --verify --quiet`.
- Run `git log <ref> --skip=<skip> -n <limit+1>` with a null-byte/record-separator format capturing sha (short), author, date (ISO), and FULL message (`%B` — subject plus body).
- Return `{"branch": str, "commits": [{"sha", "author", "date", "subject", "body"}], "has_more": bool}` where subject = first line, body = rest (may be empty), has_more = an extra row was fetched.
- Pure parse function separated from the git call, unit-tested with fixture output.

## Shared contract C — branch parent info
Each branches-layer entry gains:
- `parent`: `{"name": str, "source": "ledger" | "assumed", "fork_base": "short sha or null"}`
  - If the branch-map ledger has a Parent: name = that (strip `origin/`), source = "ledger", fork_base = ledger fork-base short sha if recorded, else computed.
  - Else: name = "main", source = "assumed", fork_base = `git merge-base origin/main <tip>` (short sha; null on failure). Skip for main itself (parent = null).
- Keep the existing `ledger` field for compatibility, but the UI's separate Ledger column goes away (parent column replaces it).


## Task 1 — backend (owns: apps/holodeck/server.py, state.py, collectors/, collect.py, tests/, README.md)
1. Contracts A, B, C.
2. Tests: submitted_via validation (accept each enum value + null, reject junk), branch-commits log parsing (multi-commit fixture incl. multi-line bodies), parent derivation (ledger vs assumed), plus keep all existing tests green.
3. README: one line for the new endpoint and the cycle-tracker state fields.
4. Style rules as before (no type hints, no blank lines between functions, `###` section headers).

## Task 2 — frontend (owns: apps/holodeck/web/ only)

**Section restructure** — nav and page order become: `00 Overview, 01 Worktrees, 02 Branches, 03 Apps, 04 Core, 05 Skills, 06 Specs, 07 AI Sessions, 08 Deploy`. Branches moves OUT of the worktrees section into its own section; Core splits out of Apps into its own section (same table, its own heading/anchor). Update `tests`-relevant ids carefully (test_web.py checks some ids — keep `worktree-cards`, `branches-table`, etc. or update that test file is NOT yours — keep existing ids stable and add new section wrappers around them).

**Section ledes → tooltips.** Remove the muted description paragraph under every section heading; put that text in a `title` attribute on the section heading instead (hover shows it). Applies to all sections.

**Overview panels.** Remove the three panels (Next steps, Needs attention, Latest activity). Replace with TWO half-width panels (grid 1fr 1fr ≥1000px, stacked below):
- **Status** (left): the dev-cycle rollup. One row per worktree that has `submitted_at` set, ordered by submitted_at desc: worktree name chip in its title-bar color (click → its card), submitted-via pill, then either `waiting for AI response · <elapsed>` (gold, when ai_responded is false) or `AI responded · <elapsed since submitted>` (green check). Below those, dim one-liners for active worktrees with no cycle state ("no cycle state — set Submitted via on the card"). Empty state: explain the Submitted-via pulldown.
- **Latest activity** (right): keep the existing worktree-keyed feed as-is.
- The next-steps queue UI is REMOVED from the overview for now (the API and stored data stay; do not delete state).

**Worktree cards — interaction changes:**
1. Expand/collapse triggers ONLY on the title bar or the chevron. Clicks anywhere else in the card never toggle expansion (remove the whole-card click handler).
2. Replace the next-step / just-done / review-status row with the **cycle tracker**:
   - A labeled pulldown `Submitted via` with options: `—` (none), `Cursor`, `Claude CLI`, `Claude app`, `Codex CLI`, `Codex app` (values: cursor, claude-cli, claude-app, codex-cli, codex-app).
   - On selection: PUT `{submitted_via, submitted_at: <now ISO>, ai_responded: false}`; on `—`: PUT all three null/false.
   - When submitted_at is set, show a status line: `waiting for AI response · 17m` (compact relative format, same helper as elsewhere) with a checkbox labeled `AI responded` at the end; checking it PUTs `{ai_responded: true}` and the line becomes `AI responded · <elapsed>` with the check.
3. Below the cycle tracker, show the **last three sessions** for the worktree (was one), compact rows: tool dot + tool name + relative time. Hovering the tool-name part shows a styled tooltip (custom positioned div, not `title`) with the session title and the last user message preview (~400 chars, from the snapshot's `last_user`). Clicking the row opens the existing right-side session drawer for that session.
4. The branch name inside the card body links to that branch's row in the new Branches section (scroll + brief highlight flash on the row).
5. Keep: colors, active toggle, drag/move-to-top ordering, notes in expanded view, cursor-open dimming.

**Branches section:**
- Columns: `Branch | Parent | Tip commit | Date | Ahead / Behind | Worktree | PR` (the Ledger column is gone; "Tip" header renamed "Tip commit").
- Branch cell: when the branch has a worktree, render the name in that worktree's title-bar background color (readable — use the color as text color; fall back to default ink when too dark is fine, keep it simple).
- Parent cell: parent name (mono); if `parent.source === "assumed"` show it muted with an `(assumed)` hint; fork_base short sha as a small muted suffix, with `title` tooltip "fork point on <parent>". Clicking the parent name scrolls to that branch's row if it's in the table.
- Clicking a branch name opens a right-side **commits drawer** (reuse the drawer pattern): fetches `/api/branch-commits?branch=...&limit=20`, renders each commit as sha (mono, muted) + date + full message (subject bold, body pre-wrap), with a `Load more` button at the bottom while `has_more` (passes growing `skip`). Sample mode: show a small read-only notice instead of fetching.
- Row highlight: an `id` per branch row so worktree-card links can target it.

**Sample data**: extend `sample-state.json` (cycle fields on 2-3 worktrees in different states) and `sample-snapshot.json` (parent fields on branches) so `?src=sample` exercises the status box, cycle tracker, and branches columns. Do NOT fetch branch commits in sample mode.

**Keep** all iteration-2 quality rules: no innerHTML with data, null-safe, no external resources, escape session text (tooltips included — textContent only).

## Acceptance
Backend: all tests green; `/api/branch-commits` returns 20 full-message commits + has_more for a real branch and 404s an unknown branch; branches layer shows ledger parent for a ledger branch and assumed-main parent with fork_base for others.
Frontend: sections renumbered with ledes as tooltips; status box reflects sample cycle states; pulldown → waiting line → checkbox flow round-trips against the live API; card expansion only via title/chevron; session tooltips + drawer open from card rows; branches table shows colored names, parent, tip commit; commits drawer loads and pages.
Both: report files changed, verification, deviations.
