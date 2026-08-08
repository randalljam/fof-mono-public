file: 2026-07-12_iteration-4-spec.md
title: Holodeck iteration 4 — full messages, to-do list, primary AI interface, active toggle
last-updated: 2026-07-12_0830
ai: Claude Code - Fable 5 (fable5-w-codex orchestration)
session: `holodeck control center build`

# Holodeck iteration 4 — build spec

User feedback round 3 (2026-07-12). Two parallel, file-disjoint tasks. Prior specs in this folder remain authoritative where not amended. PRESERVE all existing behavior not named here (worktree colors, cursor-open pill, drag ordering, commits drawer, file drawer, tests).


## 1 — Session drawer: full messages + jump to end
- Backend: remove the per-message 2,000-char cap in session detail (`MAX_DETAIL_TEXT` in collectors/sessions.py and wherever cursor/codex/claude detail readers truncate). Do NOT cut off message text at all; keep the 200-message cap. (Rationale: the assistant's final recap is the most valuable part and was being cut off.)
- Frontend: in the session drawer header, add a **down-arrow button directly below the X** (same icon-button styling, stacked vertically) that scrolls the drawer body to the very end of the thread. Long messages render fully (pre-wrap, no clamp).

## 2 — Overview to-do list (manual, with markdown archive)
A full-width panel ABOVE the Status/Latest-activity pair, titled "To-do".
- Backed by the EXISTING global next_steps state (id/text/done/created_at) — this UI returns, upgraded. Items shown = non-archived ones, in stored list order.
- Interactions: text input + Add (Enter submits); checkbox toggles done (struck-through, stays in place); **drag to reorder** (persisted); an **archive button** (⌄→ or 🗄-style small button, use text "archive") per item.
- New backend endpoints:
  - `PUT /api/next-steps-order` body `{"order": ["id1", "id2", ...]}` → reorders the stored list (unknown ids 400; ids missing from the list keep their relative order at the end). Returns the list.
  - `POST /api/next-steps/{id}/archive` → removes the item from state AND appends it to `apps/holodeck/data/todo-archive.md` (create file with heading `# Holodeck to-do archive` if missing), under a `## YYYY-MM-DD` section for today (create section if missing, newest date section at top), as `- [x|" "] <text> (added <created_at date>, archived <HH:MM>)`. Atomic write (read-modify-replace). Returns `{"ok": true}`. 404 unknown id.
- Sample mode: read-only list from sample-state.json, controls disabled.

## 3 — Worktree cards: Primary AI interface + per-worktree next steps
- **Rename** the pulldown label from "Submitted via" to **"Primary AI interface"** — semantics: the main harness currently used to work in that worktree (not per-submission). Same five options + `—`.
- State: new worktree field `primary_interface` (same enum as submitted_via, or null). MIGRATION in state normalization: if `primary_interface` is absent/null and legacy `submitted_via` is set, adopt its value. Keep accepting the legacy fields (submitted_via/submitted_at/ai_responded) in stored data without error, but the UI no longer reads or writes them, and selecting an interface PUTs only `{"primary_interface": ...}`.
- **REMOVE the waiting-for-AI-response box and the AI-responded checkbox entirely.**
- In their place: **per-worktree next steps** — a free-text input labeled `next step` at the top; pressing Enter turns the text into a checkbox item in a list directly below and clears the input for the next entry (newest item at the top of the list). Checkbox toggles done (struck-through). Small × to delete an item.
- State: new worktree field `steps`: list of `{id, text, done, created_at}` (same item shape as next_steps; validate like next_steps items; id generated client-side or server-side — simplest is client sends the full validated list via the existing worktree merge PUT with a new allowed field `steps`, server validates each item and replaces the list).
- **Overview Status panel** (data source changes since waiting-state is gone): one row per ACTIVE worktree, ordered by latest session recency: worktree name chip in its color (click → card), **primary AI interface pill** (when set), the worktree's **first unchecked next step** as text (muted "no next step" when none), and the latest session's relative time. Drop the waiting/responded rendering and the "no cycle state" hint rows.

## 4 — Active toggle drives dimming and ordering
- The ACTIVE badge on the card becomes a **toggle button**: click flips between `ACTIVE` (teal) and `INACTIVE` (muted). Remove the separate switch control if redundant — one control, the badge.
- **Dimming changes ownership**: cards gray out when INACTIVE (state), NOT when Cursor-closed. Remove the `cursor-closed` opacity/saturation dimming; keep the "open in Cursor" pill purely as information.
- New state field `deactivated_at` (ISO or null): set to now when toggled inactive (client-supplied), null when re-activated.
- **Sort**: active cards first (existing order semantics), then inactive cards ordered by `deactivated_at` DESC — so a freshly deactivated card lands at the TOP of the inactive group. The UI must re-sort immediately on toggle.

## Task split
- **Task 1 backend** (owns server.py, state.py, collectors/, tests/, README.md): items 1 (truncation), 2 (endpoints + archive file), 3 (state fields primary_interface migration + steps validation), 4 (deactivated_at). Tests: migration from submitted_via, steps list validation (reject non-list/bad items), next-steps reorder (incl. unknown id 400 and missing-id tail), archive markdown append (tmp_path: new file, existing file with today's section, item removed from state), detail text no longer truncated. Keep all existing tests green; style rules unchanged.
- **Task 2 frontend** (owns apps/holodeck/web/ only): items 1 (jump-to-end button), 2 (to-do panel with drag reorder + archive), 3 (label rename, per-worktree steps UI, Status panel rework), 4 (badge toggle, inactive dimming replacing cursor-closed dimming, auto-move on deactivate). Update sample-state.json (primary_interface, steps, deactivated_at variety) and keep test_web.py-checked ids stable. Null-safe, no innerHTML, escape all text.

## Acceptance
- A long real Claude Code session renders its final assistant recap in full; the down-arrow jumps to it.
- To-do: add/check/drag/archive round-trips; archived item appears in data/todo-archive.md under today's heading and leaves the UI.
- Worktree card shows Primary AI interface pulldown (legacy submitted_via value pre-selected via migration), next-step entry grows a checklist; no waiting/responded UI remains.
- Toggling a card INACTIVE dims it and moves it to the top of the inactive group instantly; Cursor-closed cards are no longer dimmed.
- All tests green; report files changed, verification, deviations.
