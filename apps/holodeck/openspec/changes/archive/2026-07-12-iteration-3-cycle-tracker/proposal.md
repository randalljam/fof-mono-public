# Proposal: iteration-3-cycle-tracker

## Why
User feedback round 2 (2026-07-12): the primary thing Randy checks is where each worktree sits in his iterative dev cycle (dictate prompt → submit via a harness → wait 2–30 min → AI responds → read → test or follow up). The cards must show that cycle state (manually set for now), the overview must roll it up, and branches need first-class inspection (parent, full commit history) without leaving the holodeck.

## What Changes
- Worktree state gains `submitted_via` (cursor/claude-cli/claude-app/codex-cli/codex-app), `submitted_at`, `ai_responded`; card UI replaces next-step/just-done/review fields with a Submitted-via pulldown, waiting-for-AI elapsed line, and AI-responded checkbox.
- Overview panels reduced to Status (per-worktree cycle rollup) + Latest activity; needs-attention and next-steps panels removed (next-steps API/data retained).
- Branches becomes its own section (sections renumbered 00–08; Core split from Apps); section ledes become heading tooltips.
- Branches gain `parent` (ledger or assumed-main + fork base); table shows Parent and Tip commit, worktree-colored branch names, and a commits drawer backed by new `GET /api/branch-commits` (20 full messages a page, Load more).
- Worktree cards: expansion only via title bar/chevron; last three sessions shown with hover message tooltips and click-through to the session drawer.

## Non-Goals
- Automatic cycle-state detection (planned later).
- Deploy section redesign.

## Impact
- `state.py`, `collectors/branches.py`, `server.py`, `tests/`, `web/*`.
