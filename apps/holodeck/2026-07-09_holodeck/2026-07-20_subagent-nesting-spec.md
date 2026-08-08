file: 2026-07-20_subagent-nesting-spec.md
title: Holodeck — nest Codex subagents under their parent session
last-updated: 2026-07-20_1030
ai: Claude Code - Fable 5 (fable5-w-codex orchestration)
session: `holodeck control center build`

# Nest Codex subagents under parent — build spec (branch feature/holodeck-commits)

Codex subagent sessions (entrypoint `codex-subagent`, origin `delegated`, e.g. "Codex Auto Review") are now hidden from the AI Sessions list. Instead of just hiding them, attach each to its parent operator session and show them under the parent as a "Subagents" expander (alongside "Full response"). Keep tests green; style: no type hints, no blank lines between functions, `### ` headers.

## Parent linkage (backend — turns/db.py + a linker)
- A subagent session is one with `origin='delegated'` AND entrypoint/tool indicating codex machinery (tool='codex' and label/interface machinery, or the session's stored interface is a subagent). Use the existing `codex_session_is_delegated` signal; treat delegated codex sessions as subagent candidates.
- Match each subagent to a PARENT = the operator session (origin='operator') on the SAME worktree (or same project path) whose time window contains the subagent: `parent.started <= subagent.started` and `parent.last_activity >= subagent.started` (fall back to nearest-earlier operator session on that worktree within 2h). Prefer codex operator parents; else any operator session on that worktree.
- Store the link: add nullable `parent_session_id` column to `sessions` (migrate: ADD COLUMN when missing). Compute it during ingest (a post-pass after all sessions are ingested) so both parent and child exist. Unmatched subagents keep parent_session_id NULL (still hidden from the list).

## API (server.py + db.py)
- `GET /api/turns/subagents?session=<parent_id>` → list of that parent's subagents: `[{id, label, started, last_activity, instruction, recap}]` where `instruction` = the subagent's first user exchange user_text (trimmed, <=400 chars) and `recap` = the subagent's last assistant response text (trimmed, <=800 chars). Reuse existing exchange queries. Cap 20.
- Do not expose reasoning/tools (already trimmed at ingest).

## Frontend (web/)
- In the session drawer for an OPERATOR session, after the turns view and before/near the "All messages" details, add a collapsed `<details>` "Subagents (N)" that lazy-fetches `/api/turns/subagents?session=<id>` on open and renders each subagent as: label + relative time, its instruction (muted) and recap (prose). N comes from a count in the snapshot session object (add `subagent_count` to the snapshot cloud/codex session items when parent_session_id links exist) OR fetch-on-open and hide the expander when empty.
- Keep delegated subagents OUT of the top-level list (unchanged). Null-safe, escape text.

## Snapshot wiring
- The snapshot session items for operator sessions gain `subagent_count` (int) so the frontend knows whether to show the expander without an extra call. Compute from turns.db parent_session_id grouping in the sessions collector's cloud/local merge (best-effort; 0 when none).

## Tests
- Parent-linkage: a delegated codex subagent within an operator session's time window on the same worktree links to it; outside the window / different worktree → NULL.
- subagents API returns trimmed instruction + recap; empty for a session with no subagents.
- Keep existing tests green.

## Acceptance
- The "Codex Auto Review" subagents no longer appear as top-level rows (already true) AND appear under their parent operator session's drawer in a "Subagents" expander with a one-line instruction + recap each.
- All tests green. Report files changed, verification, deviations.
