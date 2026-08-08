# Proposal: iteration-4-todo-and-interface

## Why
User feedback round 3 (2026-07-12): assistant recaps were being cut off in the session drawer; the waiting-for-AI cycle box didn't match how Randy actually works (he wants a per-worktree next-step checklist and a "primary AI interface" designation instead); a manual global to-do list with a durable archive was requested; and active/inactive should be the one thing that drives card dimming and ordering.

## What Changes
- Session detail messages are served untruncated (200-message cap remains); the drawer gains a jump-to-end button.
- Full-width To-do panel on the overview: add, check, drag-reorder, archive; archived items append to `data/todo-archive.md` under dated headings via new reorder/archive endpoints.
- Worktree cards: "Submitted via" becomes "Primary AI interface" (`primary_interface`, legacy value migrated); the waiting/responded UI is removed in favor of a per-worktree `steps` checklist; the Status panel shows interface pill + first open step + latest session recency per active worktree.
- The ACTIVE badge is the toggle; `deactivated_at` orders the inactive group (newest first); dimming follows inactive state instead of Cursor-open state.

## Non-Goals
- Automatic cycle detection; archived-todo browsing UI.

## Impact
- `state.py`, `server.py`, `collectors/sessions.py`, `tests/`, `web/*`.
