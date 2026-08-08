# Proposal: iteration-2-interactive

## Why
User feedback round 1 (2026-07-11): the holodeck must become an interactive work-management surface, not a read-only report. Worktree cards are the primary place Randy manages parallel AI-coding work, and the dashboard must let him record next steps, mark what was just done and its review status, reorder and deactivate worktrees, and view/edit OpenSpec files in place.

## What Changes
- Add a persistent, gitignored user state store (`data/state.json`) with next-steps queue and per-worktree card state, exposed via new state APIs.
- Add a safe file read API and an allowlisted file write API (OpenSpec markdown/config + registry.yaml).
- Worktrees gain `apps_touched`; apps gain concrete `kind` fallback plus `stage`/`spec_stage` registry passthrough; specs gain file paths for drawer viewing.
- Server auto-collects on startup when the snapshot is stale (>30 min).
- Dashboard: one-row clickable stat tiles, next-steps panel, worktree-keyed latest activity, collapsible/editable/reorderable worktree cards, expandable app cards with stage pills and worktree chips, overhauled specs section with clickable file rows, file drawer with edit/save, AI Sessions rename.

## Non-Goals
- Editing arbitrary repo files from the UI (write surface is deliberately OpenSpec + registry only).
- Skills / AI Sessions / Deploy section redesigns (deferred to a later feedback round).

## Impact
- `apps/holodeck/state.py` (new), `server.py`, `collectors/{apps,worktrees,specs,core}.py`, `tests/`, `web/*`, `registry.yaml`.
