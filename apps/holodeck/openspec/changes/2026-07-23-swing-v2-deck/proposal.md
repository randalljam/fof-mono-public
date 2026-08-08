# Proposal: swing-v2-deck

## Why
Holodeck grew into nine parallel sections with no single place to stand. The operator wants one primary interface built around three levels: (1) agents — what every recent AI session is doing right now, at a glance, like a lighted control-key strip; (2) active work — the worktrees chosen for this work session, with next steps and gating state; (3) universe — everything on the radar (parked worktrees, branches without checkouts, apps) with enough "where did I leave this" context to re-enter.

## What Changes
- New per-session agent status API: `GET /api/agents` returns the latest exchange state for each recent operator session, classified into four states — `thinking` (AI working, blue), `done` (finished, green), `needs-you` (finished but waiting on operator input, yellow), `error` (stalled or failed, red). Classification lives in `turns/db.py` as pure, tested functions over the latest exchange row plus its digest.
- Frontend overhaul to a three-level primary page: **Deck** (agent light-tiles, 4-state color coded, click-through to the session drawer and Cursor focus), **Active Work** (global to-do plus active worktree cards enhanced with live turn state and recap), **Universe** (parked worktrees with resume context, branches without a checkout, and apps — each with a copy-to-clipboard `create-worktree` skill prompt when no live worktree exists).
- Former sections Branches, Core, Skills, Specs, Deploy remain rendered but demoted to a "More" nav group; AI Sessions table stays as the search/filter surface. Session, commit, and file drawers unchanged.
- Deck polls `/api/agents` on an interval; sample mode reads `sample-agents.json`.

## Non-Goals
- No collector changes; universe assembles from existing snapshot layers plus state.json.
- No automation of worktree creation from the browser — the button copies a prompt for a Cursor agent, it does not run git.
- No change to turns ingestion, digests, or cloud sync.

## Impact
- turns/db.py, server.py, state.py, web/index.html, web/app.js, web/style.css, web/sample-agents.json, tests.

## Feedback round (2026-07-23, same day)
- Deck renamed **Active AI**; all section numbers and kicker/double titles removed; section descriptions became h2 tooltips.
- Agent tiles: colored project title bar (worktree color, app slug else folder name), 3×3 grid capped at 9 with show-all, Claude/Codex/Cursor filter checkboxes (persisted).
- `needs-you` narrowed to "AI intentionally paused for user interaction" (popped question / run-command permission). Semantic response parsing (trailing questions, hand-back phrases, digest asked items, error markers) removed — answered turns are always `done`; the stale-unanswered signature reads `needs-you`/`paused`; `error` reserved for a future semantic phase. Turn badges on cards follow (waiting→THINKING, else DONE).
- Global **To-do** became its own section; work-card "next step" renamed to-do, with in-card drag reorder and an `↑` promote that moves an item to the top of the global list tagged with the project name in the worktree color (`source` field on next-step items).
- "open in Cursor" renamed **go to window**, rendered only when the worktree has an open Cursor window.
- Deferred to a later change: decoupling work cards from windows (cards created for cloud/phone sessions without a local worktree); semantic classification of responses (real error detection, question detection from tool records rather than staleness).

## Feedback round 2 (2026-07-23)
- Exchange detail restructured to land on the AI's conclusion: **Final response** first (the turn's last assistant prose message — what Claude Code renders as the closing `●` bullet, now ingested as `exchanges.response_final_text`), then the full response, then the user message — each a 3-line clamped preview with a caret to unfold. Claude Code's `✻ recap:` line (JSONL `system`/`away_summary` records, previously dropped) is ingested as `exchanges.response_recap` and shown under the final response. Schema v7; a turns rebuild populates the new columns.
- Active AI tiles are hideable: an `×` on each tile hides it (persisted locally, keyed to the turn's exchange id so a new turn on that session reappears); a `show hidden (N)` button beside the platform filters restores them. Terminology is "hide" — "close" stays reserved for closing the tool's own tab.
