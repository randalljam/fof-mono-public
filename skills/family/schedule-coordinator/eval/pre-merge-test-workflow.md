file: skills/family/schedule-coordinator/eval/pre-merge-test-workflow.md
title: Pre-merge test workflow — test on Hermes before merging to main
history:
  - 2026-07-29 · Randy · Codex [family-schedule Next Week](019fae81-a036-78b1-86b4-43decd6a9564) — make the branch placeholder reusable and update first-time active-week expectations
  - 2026-06-12 · Randy · Claude Code [schedule-coordinator](https://claude.ai/code/session_01FRAdJZvkLq89hmPU6D2z6x) — rework to laptop-driven branch switch via shared hermes-branch-testing skill
  - 2026-06-12 · Randy · Claude Code [schedule-coordinator](https://claude.ai/code/session_01FRAdJZvkLq89hmPU6D2z6x) — initial workflow

**How to test the schedule-coordinator skill on Hermes before merging the PR.**

The skill under review lives on the feature branch selected for the current task (for
example, `feature/family-schedule-dashboard`). Hermes normally syncs from `main`.
The generic branch-switch mechanics (laptop-driven, via `fly ssh`) are in the shared
skill — this doc only adds the schedule-coordinator-specific steps.

**Branch switch procedure:** `skills/repo-ops/hermes-branch-testing/README.md`


## Step 1 — Switch Hermes to the feature branch
Follow hermes-branch-testing Steps 1–2 with the exact `<feature-branch>` under review:
switch the container clone from your Mac via `fly ssh console`, restart the gateway,
send `/new` in Telegram.


## Step 2 — Verify the skill loaded
In Telegram:
> What do you know about scheduling or coordinating schedules?

Hermes should match the schedule-coordinator skill and offer to help with family
schedule coordination. If not, see the troubleshooting notes in hermes-branch-testing.


## Step 3 — Run the manual test
Follow `skills/family/schedule-coordinator/eval/manual-test-procedure.md` (add a test
entry → verify save and format → test conflict detection → remove the entry → verify
clean state). Paste results into that file's § Results.

Note: if this is the very first schedule message ever, the first-time setup flow runs
(creates current and next dated files plus `horizon_family-schedule.md`, then asks about recurring items). That's
real setup, not test data — go through it, then run the test. The schedule data lives
on the Hermes volume and persists across branch switches.


## Step 4 — Switch back to main
Follow hermes-branch-testing Step 5 (checkout `main` on the container, restart, `/new`).
The schedule-coordinator skill disappears from Hermes until the PR merges — expected.


## Step 5 — Merge the PR
Create and merge the PR for `<feature-branch>` → `main`.


## Step 6 — Final confirmation on main
1. In Telegram: **"sync your skills"** (normal flow, pulls main).
2. Restart if the sync output says to.
3. Smoke test:
   > What's on my schedule this week?

   The skill should activate and read the week file created during the branch test (the
   data persisted on the volume). One quick add/remove cycle if you want a full re-check.
