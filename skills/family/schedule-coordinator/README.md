file: skills/family/schedule-coordinator/README.md
title: Schedule coordinator — family schedule management via Telegram
source-github-url: original
source-guide-url: original
history:
  - 2026-07-29 · Randy · Codex [multi-day Horizon promotion repair](019fae24-bd13-7821-b421-9b22fb2ce461) — expand explicit date spans into daily weekly occurrences, preserve residual Horizon dates, and add a guarded legacy-range repair
  - 2026-07-29 · Randy · Codex [automatic family-schedule rollover](019fae24-bd13-7821-b421-9b22fb2ce461) — add a locked, retry-safe Pacific weekly transaction, guarded bootstrap, and Hermes runtime scheduler contract
  - 2026-07-29 · Randy · Codex [family-schedule Next Week](019fae81-a036-78b1-86b4-43decd6a9564) — make current and next Monday-dated files authoritative, add executable date routing, and align aliases, population, and dashboard sync
  - 2026-06-17 · TL · Claude Code [family-schedule-dashboard](https://claude.ai/code/session_01LAGLPtNUNDR2uta38M8K8C) — add notify_dashboard.py + step to live-refresh the lesson-logger dashboard Family Schedule tab after schedule edits
  - 2026-06-12 · Randy · Claude Code [schedule-coordinator](https://claude.ai/code/session_01FRAdJZvkLq89hmPU6D2z6x) — rename schedule files: YYYY-MM-DD_week_family-schedule.md (Monday date) and horizon_family-schedule.md
  - 2026-06-12 · Randy · Claude Code [schedule-coordinator](https://claude.ai/code/session_01FRAdJZvkLq89hmPU6D2z6x) — finalize procedure, add first-time setup, Hermes wrapper, drop planned scripts
  - 2026-06-08 · Randy · Claude Code [schedule-coordinator](https://claude.ai/code/session_01FRAdJZvkLq89hmPU6D2z6x) — initial skill procedure

**Coordinate family schedules between Randy and TL via Telegram.**

Turn natural-language voice or text messages into structured schedule entries, detect
conflicts (including travel time and childcare implications), and keep both parents
informed. Storage is plain markdown files on the agent's volume — no database, no backend.

The agent reads and edits authoritative schedule markdown files directly.
`schedule_files.py` is the canonical `family-schedule-routing-v1` storage/routing contract;
`weekly_rollover.py` is the canonical `family-schedule-weekly-rollover-v1` automatic
transaction; `rollover_week.py` preserves the legacy skeleton gate interface.


## When to use
When Randy or TL:
- Proposes a schedule item ("Kid1 has gymnastics Monday at 4, I'll take her")
- Asks about the schedule ("what's on tomorrow?", "are we free Saturday afternoon?")
- Needs to coordinate ("can you take the kids Thursday evening?")
- Mentions something coming up further out ("dentist appointment in two weeks")
- Asks to see or modify the horizon / future schedule


## Storage overview
Two kinds of markdown files, both on the agent's volume (not in the repo):

| File | What | Lifecycle |
|------|------|-----------|
| `schedule/YYYY-MM-DD_week_family-schedule.md` | One authoritative Monday–Sunday schedule + log | Durable; current and next week are ensured idempotently, and past files remain unchanged as history |
| `schedule/horizon_family-schedule.md` | Items after next Sunday + recurring defaults | Persistent; dated items move once into a weekly file when that week becomes the active next week |

`current-week.md` and `next-week.md` are never authoring sources. They are read-only aliases
served by Hermes or local dashboard caches derived from the authoritative dated files.

See `skills/family/schedule-coordinator/references/schedule-schema.md` for field
definitions, travel-time handling, storage routing, and the status lifecycle.

See `skills/family/schedule-coordinator/references/example-week.md` for a concrete
weekly file template.


## Gate check — run before every schedule interaction

Before processing any schedule request, ensure both active weekly sources exist:

```bash
python3 scripts/rollover_week.py "$SCHEDULE_DIR"
```

- The first line remains `exists:` or `created:` for the current week (legacy contract).
- `next-exists:` or `next-created:` reports the following Monday–Sunday file.
- `rollover_week.py` is idempotent and never overwrites a dated file. It creates skeletons
  only; it is not the automatic weekly transaction owner.
- The live Hermes gateway separately polls `weekly_rollover.py scheduled` every five
  minutes. That code—not the UTC cron expression—derives the Pacific boundary and catches
  up a missed Monday after a restart.
- If the automatic runner reports `bootstrap required`, do not improvise or create state.
  Follow the reviewed bootstrap procedure under "Automatic weekly rollover" below.


## First-time setup

If the schedule directory doesn't exist yet (very first use of the skill):

1. Run the gate check script — it creates the directory plus current- and next-week skeletons.
2. Create `horizon_family-schedule.md` with empty sections:
   ```markdown
   file: schedule/horizon_family-schedule.md

   ## Recurring
   (none yet)

   ## Upcoming
   (none yet)

   ## Notes
   ```
3. Ask the user about recurring weekly items to seed the Recurring section:
   > "I've set up the schedule. Do you have any recurring weekly items I should know about?
   > Things like kids' activities, regular commitments, weekly errands — with day, time,
   > location, and how far the drive is."
4. For each recurring item, capture as a proposal: day of week, time, location, travel
   time, and who usually goes. Do not write these defaults yet.
5. Present the proposed recurring defaults and their resulting population for both active
   weeks. Wait for explicit confirmation.
6. Only then write the approved defaults to `## Recurring`, populate both dated files,
   log the setup, notify the dashboard, and proceed with the original request.
7. Before enabling the runtime job, run the automatic-rollover bootstrap dry-run, review
   its inventory/diffs, take the required Hermes backup, and apply only the matching digest
   as described below.


## Flow — adding a schedule item

1. **Extract** from the user's message. Key fields (see schema reference for full list):
   - `date`, `time` (activity window), `title`, `who` (who's going)
   - `travel` — stated ("30 min drive") or known from recurring activities
   - `blocked_time` — compute from activity time + travel + any errands mentioned
   - `childcare` — who's covering kids while the other parent is out
   - `notes` — anything else mentioned

2. **Resolve the target from the concrete Pacific date.** Do not infer a filename or edit a
   dashboard alias. Run:
   ```bash
   python3 scripts/schedule_files.py route "$SCHEDULE_DIR" YYYY-MM-DD --write
   ```
   The canonical resolver returns exactly one authoritative target:
   - `current: ...YYYY-MM-DD_week_family-schedule.md` for this Monday–Sunday.
   - `next: ...YYYY-MM-DD_week_family-schedule.md` for the following Monday–Sunday.
   - `horizon: .../horizon_family-schedule.md` for a future date after next Sunday.
   It rejects a past write. If the user clearly intends a retroactive correction, explain
   that it changes history, obtain explicit confirmation, then rerun with `--allow-past`;
   the historical dated file must already exist and is never created by routing.

   A multi-day request is a set of daily occurrences, not one range-shaped weekly entry.
   Enumerate each intended date and route it independently. Write one ordinary entry under
   each current/next weekly day. If the same title, time, and metadata repeat over a
   contiguous inclusive span wholly in Horizon, store one canonical source bullet:
   ```markdown
   - 2026-08-03 through 2026-08-07 · **9:00a–12:00p** daily (Mon–Fri) · Kids soccer camp · pickup at noon
   ```
   The two ISO dates are authoritative. Do not put this range representation in a dated
   weekly file, and do not rely on prose alone to identify its dates.

3. **Check for conflicts** by reading the exact resolved dated week file and comparing blocked times:
   - **Time overlap**: same person has two entries with overlapping blocked times.
   - **Childcare gap**: both parents' blocked times overlap — no one home with kids.
     This is the highest-priority conflict.
   - **Tight transition**: one entry ends within 15 min of another starting (warn, not
     a hard conflict).
   - Flag conflicts to the user before saving — don't silently overwrite.
   - If the resolver returned Horizon, skip conflict checking (dates may be approximate;
     conflicts are caught when the item is pulled into a week during rollover).

4. **Confirm in plain English** before saving. State the extracted info including blocked
   time and childcare implications:
   > "Got it — **Monday 3:30p–5:30p**, Randy taking Kid1 to gymnastics (activity 4:00–5:00,
   > 30min drive each way). TL on childcare. Save it?"
   If the user corrects anything, update and re-confirm. **Never save without explicit yes.**
   If travel time is unknown for a new location, ask before confirming.

5. **Save** the entry by editing only the exact path returned by the resolver:
   - Find the correct day heading (e.g., `## Monday Jun 15`).
   - If the day shows `(nothing scheduled)`, replace that placeholder with the new entry.
   - If the day already has entries, insert the new one in chronological order by
     blocked-time start.
   - Use the entry format from the schema reference:
     ```
     - **{blocked_time}** {who} — {title} ({activity detail, travel note})
       {childcare note} · {location}
     ```
   - Append the raw user message to the `## Log` section at the bottom of the week file.

6. **Refresh the dashboard** (best-effort) so the live Family Schedule view updates.
   After writing any schedule file — add, modify, cancel, or rollover — run the dashboard
   notify script. It's a no-op when no dashboard is configured (e.g. local dev):
   ```bash
   python3 scripts/notify_dashboard.py
   ```
   See "Dashboard sync (live view)" below.

7. **Notify the other person** if the entry affects them (blocks their time, puts them on
   childcare, or changes a shared plan). Send a Telegram message summarizing what was added.
   If it doesn't affect the other person, skip notification.

8. **Log their response** too — whether they confirm, modify, or flag an issue, append it
   to the log.


## Flow — checking the schedule

1. Resolve each concrete date without `--write`:
   ```bash
   python3 scripts/schedule_files.py route "$SCHEDULE_DIR" YYYY-MM-DD
   ```
   Current and next dates resolve to their authoritative dated files; past dates resolve
   only when the historical file exists; dates after next Sunday resolve to Horizon.
2. For "today" / "tomorrow" / a specific day: report that day's entries with blocked times.
3. For "this week" or a range: summarize each day that has entries.
4. For "are we free [time]?": check both parents' blocked times and report availability.
5. "Next week" reads the next dated file, not Horizon. A broad "what's coming up?" reads
   next week first, then Horizon for dates after next Sunday.


## Flow — automatic weekly rollover
The durable dated-file model makes the transition itself simple: when Pacific Monday
begins, the file that was Next Week is immediately the current source by date. Nothing is
copied, renamed, or rebuilt. The transaction then prepares the newly exposed Next Week
(`boundary Monday + 7 days`) from exact-dated Horizon entries.

The live Hermes runtime job is a no-agent script job defined by
`agents/hermes/runtime_cron_jobs.json`. Its UTC scheduler expression is `*/5 * * * *`;
that expression is only a polling cadence. `weekly_rollover.py` converts each tick to
`America/Los_Angeles`, so Monday 00:00 is 08:00 UTC in PST and 07:00 UTC in PDT without
ever hardcoding either UTC hour. If the machine is down at midnight, the durable boundary
state causes the next tick to catch up each missed Monday in order.

### Automatic transaction
For each uncompleted Pacific Monday, the script:

1. Acquires `$SCHEDULE_DIR/.family-schedule-rollover.lock` with `fcntl`.
2. Reads exact-dated, top-level bullets under Horizon `## Upcoming`, including explicit
   inclusive `YYYY-MM-DD through YYYY-MM-DD` spans and indented continuation lines.
3. Intersects each source with the new Next Week's Monday–Sunday interval. A span becomes
   one ordinary entry on every intersecting date; explicit range/daily-weekday prose is
   removed from those copies while title, time, notes, and metadata remain.
4. Adds each occurrence under the matching day, replacing `(nothing scheduled)`. Range
   occurrences carry invisible SHA-256 source-plus-date markers, so retrying a partial
   transaction cannot duplicate any day.
5. Rewrites a partially consumed source to the unconsumed date span(s) in Horizon. Only
   target-week dates move; later (and any earlier) dates remain represented exactly once.
6. Atomically replaces the destination dated file first, then atomically rewrites Horizon,
   then atomically advances
   `.family-schedule-rollover-state.json`.

Destination-first ordering means a crash can temporarily leave a duplicate but cannot
lose the only copy. On retry, the source marker suppresses a second destination entry,
Horizon pruning completes, and state advances last. Later Horizon dates, `## Recurring`,
`## Notes`, headings, and unrelated formatting are preserved. Scheduled mode is
noninteractive; normal user-authored schedule writes still require confirmation.

Recurring defaults are not automatically interpreted or expanded by this deterministic
transaction. They remain in Horizon and use the existing confirmed agent population
workflow. Only concrete `YYYY-MM-DD` entries are eligible for the automatic move.

### One-time bootstrap — dry-run first
Scheduled mode refuses to mutate anything until a reviewed bootstrap initializes its
boundary state. The default command is a pure dry-run: it creates no skeleton, lock, state,
or directory.

```bash
python3 scripts/weekly_rollover.py bootstrap "$SCHEDULE_DIR"
```

It prints the target interval, every eligible source line (including soccer camp if its
exact date is in the current Next Week), unified destination/Horizon diffs, and a
`proposal-sha256`. Before applying on Hermes, take the uniquely identified Fly volume
snapshot required by `agents/hermes/RUNBOOK.md`; an S3 copy is optional after checking that
the current ISO-week key will not replace an existing backup.

Apply only the exact reviewed proposal:

```bash
python3 scripts/weekly_rollover.py bootstrap "$SCHEDULE_DIR" \
  --apply --proposal-sha256 <reviewed-sha256>
```

Apply re-reads both files while holding the lock and refuses if the digest changed. After
the destination-first transaction succeeds, it initializes state to the current Pacific
Monday. Never enable the runtime job before this bootstrap succeeds. Do not run bootstrap
again after state exists.

### Manual diagnostics
The same noninteractive scheduled path may be invoked manually; a normal no-op prints
nothing, completed work prints one audit line per boundary, and missing bootstrap or
invalid state exits nonzero:

```bash
python3 scripts/weekly_rollover.py scheduled "$SCHEDULE_DIR"
```

`rollover_week.py` remains available for manual/interactive skeleton creation. It does not
move Horizon entries and does not advance automatic rollover state.

### Guarded repair of a legacy weekly range
An older rollover could place one range-shaped entry under only its first weekly day.
Repair exactly one such entry by supplying the SHA-256 from its invisible
`family-schedule-source` marker and the Monday naming that dated weekly file. Dry-run is
the default and writes nothing:

```bash
python3 scripts/weekly_rollover.py repair-range "$SCHEDULE_DIR" 2026-08-03 \
  --source-sha256 <legacy-source-sha256>
```

Review the occurrence dates, unified diff, and `proposal-sha256`, take the required
recoverable schedule backup, then apply only that digest:

```bash
python3 scripts/weekly_rollover.py repair-range "$SCHEDULE_DIR" 2026-08-03 \
  --source-sha256 <legacy-source-sha256> \
  --apply --proposal-sha256 <reviewed-proposal-sha256>
```

The command holds the schedule lock, re-reads the file, refuses a changed proposal, and
atomically replaces only the named dated week. It never searches by event title and
recognizes an already completed source-plus-date marker set as an idempotent no-op. It
intentionally refuses a legacy range extending outside the selected week; reconcile such
ambiguous historical data from its backup instead of silently dropping an unseen
remainder.


## Flow — horizon management

- Items in `horizon_family-schedule.md` are strictly after next Sunday and are organized by rough timeframe under `## Upcoming`:
  - `### Next 2 weeks` — dates within 14 days of the Horizon start (the Monday after next week)
  - `### This month` — same calendar month, beyond the two-week Horizon window
  - `### Later` — next month and beyond (dates can be approximate: "July", "mid-August")
- When the user asks "what's coming up?", read `horizon_family-schedule.md` and summarize.
- At the Pacific weekly boundary, the automatic transaction moves matching exact dates
  into the new Next Week and removes them from Horizon with retry-safe destination-first
  ordering. Explicit ranges expand into one entry per intersecting day, and any
  unconsumed part remains as a Horizon range. Never author a duplicate in both sources.
- If an exact Horizon date is already within current or next week, stop and reconcile it
  into the dated source before any new write; do not silently preserve competing copies.
- The `## Recurring` section is never pulled or cleaned — it's read as defaults for
  populating new weeks.


## Travel time and blocked time

Travel time is critical for accurate conflict detection. Three ways it enters the system:

1. **Explicitly stated**: "It's about 30 minutes away" — extract and apply.
2. **Known from recurring activities**: if Kid1's gymnastics is always at the same place,
   the travel time is stored in the `## Recurring` section of `horizon_family-schedule.md`.
3. **Ask if missing**: for a new location with no stated travel time, ask: "How far is
   that? I want to capture when you'll actually be unavailable."

**Blocked time** = travel-to + activity + travel-from + any errands (e.g., "picks up dinner
on the way back"). Always confirm blocked time, not just activity time, in the confirmation
step. This is what gets checked for conflicts.


## Childcare implications

When one parent is out, the other is implicitly on childcare (unless a sitter or other
arrangement is mentioned). The agent should:
- Surface this in the confirmation: "TL on childcare 3:30–5:30"
- Check for conflicts: if both parents have overlapping blocked times, flag it immediately
- Not assume — if the user mentions a sitter or grandparent covering, note that instead
- For "Family" entries (everyone goes), no childcare line is needed


## Notes
- **Schema will evolve.** Extraction is prompt-driven, not rigid — the fields in the schema
  reference are guidelines. If the user mentions something new worth capturing, capture it.
- **Recurring items.** A `## Recurring` section in `horizon_family-schedule.md` holds
  weekly/regular activities with their defaults (location, travel time, usual parent).
  Their expansion remains a confirmed agent workflow; the deterministic scheduler moves
  exact-dated Upcoming entries only.
- **Cancellations.** Mark cancelled items with ~~strikethrough~~ and `(cancelled)` rather
  than deleting — keeps the history visible.
- **Modifications and cancellations.** Resolve the item's intended date through
  `schedule_files.py route` first, read/conflict-check/edit that returned source, and append
  the change to that source's log. Confirm before every write.
- **Timezone.** All times are Pacific (America/Los_Angeles). Use 12-hour format with
  `a`/`p` suffix (e.g., `3:30p`, `10:00a`) for readability.
- **The log is append-only.** Every interaction that modifies the schedule gets a log entry
  with the raw transcript. This is the audit trail.
- **Formatting: one blank line before `##` headings** in schedule files (week files and
  horizon_family-schedule.md). Deviates from the repo's two-blank-line convention — schedule files are
  compact with short day sections, so condensed spacing reads better.
- **New weeks don't depend on the previous week.** Population uses recurring items and
  matching Horizon items only. Previous week files stay as-is for history.
- **Agent edits markdown directly.** No save script needed — the agent reads, edits, and
  writes the resolved authoritative file after confirmation. Scripts create/resolve files;
  they do not bypass confirmation or write entries.
- **Legacy file names.** Early versions used `YYYY-Www.md` week files and `horizon.md`.
  If files with those names exist in the schedule directory, rename them to the current
  scheme (week files take the week's Monday date; `horizon.md` →
  `horizon_family-schedule.md`) and update their internal `file:` header lines —
  contents are unchanged.


## Dashboard sync (live view)

The schedule markdown can be viewed live in the lesson-logger dashboard (a Fly app) under
its **Family Schedule** tab. Hermes exposes current- and next-week read-only aliases derived
from the corresponding Monday-dated sources, plus Horizon. The dashboard caches all three
as `current-week.md`, `next-week.md`, and `horizon.md`. To make edits show up live, the
agent calls `scripts/notify_dashboard.py` after writing any schedule file — it POSTs to the
dashboard's sync endpoint, which re-pulls all three.

The script is **best-effort and self-disabling**: with no sync URL configured it prints a
note and exits 0, so it's safe to call everywhere (local dev, tests, any host without the
dashboard). Configuration (env vars, generic names preferred, lesson-logger names as
fallback so the existing Hermes secrets work unchanged):

| Variable | Fallback | Purpose |
|----------|----------|---------|
| `DASH_SYNC_URL` | `LESSON_DASH_SYNC_URL` | Dashboard `/internal/sync` URL (required to do anything) |
| `DASH_SYNC_USER` | `LESSON_DASH_SYNC_USER` | Basic Auth user (optional) |
| `DASH_SYNC_PASSWORD` | `LESSON_DASH_SYNC_PASSWORD` | Basic Auth password (optional) |
| `DASH_SYNC_TIMEOUT` | `LESSON_DASH_SYNC_TIMEOUT` | Request timeout, seconds (default 10) |

Dashboard side: `apps/education/lesson-logger/dashboard/` (`sync_schedule.py`, `/schedule`).


## Scripts

| File | Purpose |
|------|---------|
| `scripts/schedule_files.py` | Canonical `family-schedule-routing-v1` contract: ensure current+next skeletons and resolve an intended date to one authoritative source. Stdlib-only. |
| `scripts/rollover_week.py` | Backward-compatible gate check over the canonical helper. Ensures current and next skeletons idempotently. Stdlib-only. |
| `scripts/weekly_rollover.py` | Canonical `family-schedule-weekly-rollover-v1` transaction: Pacific boundary guard, locking, retry-safe exact-date/range promotion, residual Horizon splitting, durable state, digest-gated bootstrap, and marker-targeted legacy repair. Stdlib-only. |
| `scripts/notify_dashboard.py` | Best-effort POST to the dashboard sync endpoint after a schedule edit. No-op without a sync URL. Stdlib-only. |


## References
- `skills/family/schedule-coordinator/references/schedule-schema.md` — field definitions,
  status lifecycle, travel-time handling, storage layout
- `skills/family/schedule-coordinator/references/example-week.md` — concrete weekly file
  template with sample entries
- `skills/family/schedule-coordinator/references/example-horizon.md` — sample horizon file
  with recurring items, upcoming dates, and notes
- `skills/family/schedule-coordinator/references/example-rollover/` — before/after test set
  showing the active window advance (current Jun 8 + next Jun 15 → current Jun 15 + next
  Jun 22) with one-time Horizon pull-in


## Eval
Focused automated contract checks (from the repository root):
```bash
.venv/bin/python3 -m pytest tests/test_schedule_files.py tests/test_rollover_week.py tests/test_weekly_rollover.py tests/test_schedule_skill_contract.py agents/hermes/test_lesson_db_server.py tests/test_notify_dashboard.py -v --rootdir=tests
```

- `skills/family/schedule-coordinator/eval/manual-test-procedure.md` — step-by-step manual
  test via Telegram: add a test entry, verify, check conflict detection, remove, verify
  clean state. Run before merging or after any significant changes.
- `skills/family/schedule-coordinator/eval/pre-merge-test-workflow.md` — how to test this
  skill on Hermes from the feature branch before merging (uses the shared
  `skills/repo-ops/hermes-branch-testing` procedure for the branch switch)
- `skills/family/schedule-coordinator/eval/extraction-test-cases.md` — 13 hand-written
  transcript → ground-truth pairs covering extraction variety (travel, blocked time,
  conflicts, horizon, queries, cancellations, modifications, recurring, terse input)
