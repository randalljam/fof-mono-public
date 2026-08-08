file: skills/family/schedule-coordinator/eval/manual-test-procedure.md
title: Manual end-to-end test — schedule-coordinator via Telegram
history:
  - 2026-07-29 · Randy · Codex [family-schedule Next Week](019fae81-a036-78b1-86b4-43decd6a9564) — add next-week authoring/query verification and active two-week setup expectations
  - 2026-06-12 · Randy · Claude Code [schedule-coordinator](https://claude.ai/code/session_01FRAdJZvkLq89hmPU6D2z6x) — initial test procedure

**Step-by-step manual test to verify the skill works end-to-end on Hermes via Telegram.**

The test adds a clearly-labeled test entry, verifies it, then removes it — leaving the
system in the same state as before. Run this after syncing skills but before merging to
main (or any time you want to verify the skill works).


## Prerequisites
- Skill is synced to Hermes (`sync your skills` in Telegram, restart Fly if needed)
- You're in a Telegram chat with Hermes
- If this is the very first use, the first-time setup flow will trigger automatically
  (creates current and next dated week files plus `horizon_family-schedule.md`, then asks about recurring items). That's real
  setup, not part of this test — go through it, then come back here.


## Phase 1 — Add a test entry

**Send this message in Telegram:**
> I have a test dentist appointment Thursday at 2pm, it's about 20 minutes away, I'm taking Kid1. This is a test entry.

**Expected agent response (confirm before saving):**
- Extracts: Thursday, 2:00p activity, ~20min travel each way
- Computes blocked time: ~1:40p–2:40p (or similar, depending on assumed duration)
- States childcare: TL on childcare
- Asks you to confirm

**Your response:**
> Yes, save it. Assume the appointment is 30 minutes.

**Expected:** Agent saves the entry to the current week file under Thursday, appends to
the log, and may notify TL (if notifications are active).

### What to check
The agent should confirm something like:
> Saved: Thu 1:40p–2:50p, Randy taking Kid1 to test dentist (appt 2:00–2:30p, 20min drive
> each way). TL on childcare.


## Phase 2 — Verify the entry

**Send:**
> What's on Thursday?

**Expected:** Agent reads the week file and reports Thursday's entries. The test dentist
entry should appear with the blocked time, travel, and childcare note.

**Then send:**
> Show me the raw contents of this week's schedule file.

**Expected:** Agent prints the markdown contents of the current `YYYY-MM-DD_week_family-schedule.md`. Verify:
- The Thursday section has the test entry in the correct format
- The `## Log` section has your original message and the agent's confirmation
- Entry format matches the schema (bold blocked time, who, title, childcare, location)


## Phase 2A — Verify next-week authoring and query
Choose a date in the following Monday–Sunday week and send:
> Add a test library visit next Wednesday at 10am for one hour. It's 15 minutes away and I'm taking Kid1.

**Expected:** Hermes computes the concrete Pacific date, runs the canonical resolver, shows
the blocked time and childcare implication, and asks for confirmation. After your "yes,"
the entry is written under the correct day in
`<next-Monday>_week_family-schedule.md` and logged there — not in
`horizon_family-schedule.md` or a `next-week.md` alias.

Then send:
> What's on next Wednesday?

**Expected:** The answer includes the test library visit from the next dated file. Ask to
show the raw source path and verify its basename is the following Monday. Finish by asking
Hermes to remove the clearly labeled test entry completely while preserving the test log.


## Phase 3 — Check conflict detection

**Send:**
> Actually TL also has something Thursday from 1 to 3pm.

**Expected:** Agent should flag a **childcare gap** — both parents would be out at
overlapping times. It should NOT silently save the entry. It should ask how to resolve
the conflict (reschedule, arrange a sitter, etc.).

**Your response:**
> Never mind, don't add that. That was just a test of conflict detection.

**Expected:** Agent acknowledges and doesn't save.


## Phase 4 — Remove the test entry

**Send:**
> The dentist entry from Phase 1 was a test. Please delete it completely from the
> schedule — remove the entry line, not just strikethrough. Keep the log entries (those
> are fine as a record of this test).

**Expected:** Agent removes the entry from Thursday's section (replacing with
`(nothing scheduled)` if it was the only entry). The log entries stay.

**Then verify:**
> What's on Thursday?

**Expected:** Thursday should show no entries (or only pre-existing entries if you had
some before the test).


## Phase 5 — Verify clean state

**Send:**
> Show me the raw contents of this week's schedule file one more time.

**Verify:**
- Thursday section is clean (no test entry, shows `(nothing scheduled)` or only real entries)
- Log section shows the test interaction (that's fine — the log is append-only)
- All other days are unchanged from before the test


## Results

Paste the key agent responses below after running the test:

**Phase 1 — Confirmation prompt:**
```
(paste here)
```

**Phase 1 — Save confirmation:**
```
(paste here)
```

**Phase 2 — "What's on Thursday?" response:**
```
(paste here)
```

**Phase 2 — Raw file contents (relevant section):**
```
(paste here)
```

**Phase 3 — Conflict detection response:**
```
(paste here)
```

**Phase 4 — Removal confirmation:**
```
(paste here)
```

**Phase 5 — Clean state verification:**
```
(paste here)
```

**Test passed?** [ ] Yes / [ ] No — notes:


## What this test covers

| Capability | Phase |
|-----------|-------|
| Skill activation (description matching) | 1 |
| Field extraction (date, time, travel, who) | 1 |
| Blocked time computation | 1 |
| Childcare implication surfacing | 1 |
| Confirm-before-save flow | 1 |
| Entry saved to correct day in week file | 1–2 |
| Next-week date routes to next Monday-dated source | 2A |
| Next-week query reads that same source | 2A |
| Log entry written | 2 |
| Schedule query ("what's on Thursday?") | 2 |
| Raw file format verification | 2, 5 |
| Conflict detection (childcare gap) | 3 |
| Entry removal | 4 |
| Clean state verification | 5 |

### Not covered by this test
- **Active-window rollover**: requires waiting for a new week or using the deterministic
  script test. Verify the old next file becomes current unchanged and only the newly
  exposed next file is created/populated.
- **Horizon management**: add an entry after next Sunday, verify it lands only in
  `horizon_family-schedule.md`, then advance the active window and verify it moves once
  into the next dated file.
- **Notifications**: verify the other parent receives a Telegram message when an entry
  affects them. Depends on TL being set up as a Hermes user.
- **First-time setup**: only happens once. If you need to re-test, delete the schedule
  directory on the Hermes volume and start fresh.
- **Recurring item population**: seed recurring items in `horizon_family-schedule.md`, delete the current
  week file, trigger rollover, verify recurring items appear in the new week.
