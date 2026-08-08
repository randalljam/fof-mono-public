file: skills/family/schedule-coordinator/references/schedule-schema.md
title: Schedule entry schema — fields, status lifecycle, storage layout
history:
  - 2026-07-29 · Randy · Codex [multi-day Horizon promotion repair](019fae24-bd13-7821-b421-9b22fb2ce461) — define canonical date spans, daily materialization, residual splitting, and source-plus-date retry markers
  - 2026-07-29 · Randy · Codex [automatic family-schedule rollover](019fae24-bd13-7821-b421-9b22fb2ce461) — define deterministic Horizon promotion, retry markers, and durable Pacific boundary state
  - 2026-07-29 · Randy · Codex [family-schedule Next Week](019fae81-a036-78b1-86b4-43decd6a9564) — define current/next dated authority, Horizon boundary, and safe historical routing
  - 2026-06-08 · Randy · Claude Code [schedule-coordinator](https://claude.ai/code/session_01FRAdJZvkLq89hmPU6D2z6x) — initial schema

**Field definitions and storage conventions for the schedule-coordinator skill.**

Extraction is prompt-driven — these fields are guidelines, not a rigid schema. The agent
extracts what's available from natural language and renders it in a consistent markdown
format. Fields will evolve as the family's needs become clearer.


## Entry fields

### Core (extract when present)

| Field | Format | Notes |
|-------|--------|-------|
| `date` | `YYYY-MM-DD` | Required. Defaults to today (Pacific) if not stated. |
| `time` | `H:MMa`–`H:MMp` | The activity itself. 12-hour with `a`/`p`. End time optional if open-ended. |
| `blocked_time` | `H:MMa`–`H:MMp` | When the person is actually unavailable. = travel-to + activity + travel-from + errands. This is what gets conflict-checked. |
| `title` | free text | Short description of the activity. |
| `who` | name(s) | Who's going / directly involved. Usually: Randy, TL, Kid1, or combinations. |
| `childcare` | name(s) | Who's on childcare duty as a result. Often implicit (the other parent). |
| `location` | free text | Optional. Where the activity is. |
| `travel` | minutes or description | One-way travel time. "30 min", "across town", etc. Used to compute blocked_time. |
| `notes` | free text | Anything else: errands on the way back, special instructions, context. |

### Status

| Field | Values | Notes |
|-------|--------|-------|
| `status` | `proposed` · `confirmed` · `cancelled` | Set on creation; updated on response. |
| `proposed_by` | name | Who originally proposed the item. |

Status is rendered inline in the entry (see example-week reference). Confirmed items
don't need a status marker — absence of a marker means confirmed. Only `proposed` and
`cancelled` are shown explicitly.


## Status lifecycle
```
proposed  ──→  confirmed     (other person agrees or proposer confirms solo)
proposed  ──→  cancelled     (withdrawn or declined)
confirmed ──→  cancelled     (plans change)
```

Cancelled items stay in the file with ~~strikethrough~~ and `(cancelled)` — keeps the
history. Don't delete entries.


## Blocked time computation

The key insight: **conflict detection uses blocked time, not activity time.** Blocked time
is when a person is truly unavailable.

```
blocked_start = activity_start − travel_time_to
blocked_end   = activity_end + travel_time_from + errand_time
```

Examples:
- Gymnastics 4:00–5:00, 30 min drive each way → blocked 3:30–5:30
- Gymnastics 4:00–5:00, 30 min drive, picks up dinner → blocked 3:30–6:00
- Dentist at 10:00 (no end time stated, 15 min away) → blocked 9:45–?? (ask or estimate)

When travel time isn't stated for a new location, ask. For recurring activities, use the
stored default from the `## Recurring` section in `horizon_family-schedule.md`.


## Conflict types

| Conflict | What it means | Agent action |
|----------|--------------|--------------|
| **Time overlap** | Same person has two overlapping blocked times | Flag both entries, ask which to keep/move |
| **Childcare gap** | Both parents' blocked times overlap, no one home with kids | Flag immediately — this is the highest-priority conflict |
| **Tight transition** | One entry ends within 15 min of the next starting | Warn (not a hard conflict, but worth noting) |


## Storage layout

All files live in a `schedule/` directory on the agent's volume (e.g.,
`$HERMES_HOME/schedule/` or `$HERMES_SCHEDULE_DIR`).

```
schedule/
  horizon_family-schedule.md           # items after next Sunday + recurring defaults
  2026-06-08_week_family-schedule.md   # historical week of Jun 8–14
  2026-06-15_week_family-schedule.md   # authoritative current week
  2026-06-22_week_family-schedule.md   # authoritative next week
  ...
```

Only these paths are authoring sources. `current-week.md` and `next-week.md` are read-only
Hermes route aliases or dashboard caches and must never be edited as schedule data.

### Date routing (`family-schedule-routing-v1`)
Resolve the intended Pacific date through
`skills/family/schedule-coordinator/scripts/schedule_files.py`:

| Intended date | Authoritative target | Creation rule |
|---------------|----------------------|---------------|
| Current Monday–Sunday | Current Monday-dated weekly file | Gate ensures it idempotently |
| Following Monday–Sunday | Next Monday-dated weekly file | Gate ensures it idempotently |
| After next Sunday | `horizon_family-schedule.md` | Store once under `## Upcoming`; do not create an arbitrary future week |
| Before current Monday | Existing historical Monday-dated file | Read-only by default; a write requires explicit retroactive confirmation and `--allow-past`; routing never creates history |

Any write whose intended date is before today's Pacific date is rejected by default,
including an earlier day in the current week. After explicit retroactive confirmation,
`--allow-past` routes an earlier current-week day to the existing current dated file or an
older date to its already-existing historical file.

When the active window advances, the dated file that was "next" naturally becomes
"current"; it is not copied, renamed, or promoted. The gate creates only the newly exposed
next Monday file. At each Pacific Monday 00:00 boundary, the automatic
`family-schedule-weekly-rollover-v1` transaction moves exact-dated top-level bullets from
Horizon `## Upcoming` into that newly exposed Next Week and removes those same source
blocks. A canonical inclusive span has a leading
`YYYY-MM-DD through YYYY-MM-DD` date expression. The mover expands its target-week
intersection into one ordinary entry per date, strips only redundant range/daily-weekday
prose from those copies, and preserves title, time, notes, and other metadata. Any
unconsumed earlier or later portion is rewritten as a residual Horizon span. It writes
the destination first, Horizon second, and durable boundary state last; invisible
source-SHA-plus-occurrence-date markers make range retries idempotent. `## Recurring`
remains a confirmed agent-expansion workflow rather than part of the deterministic mover.

### Weekly file (`YYYY-MM-DD_week_family-schedule.md`)
One file per week (Monday–Sunday), named by the week's Monday date. Structure:
- Header with week date range
- One `##` section per day (Monday–Sunday)
- Entries as structured bullets under each day
- `## Log` section at the bottom (append-only transcript)

See `skills/family/schedule-coordinator/references/example-week.md` for the full template.

### Horizon file (`horizon_family-schedule.md`)
Persistent file for recurring defaults and dated items after next Sunday. Structure:

```markdown
## Recurring
Weekly/regular activities with defaults. These get auto-populated into new week files.

- **Kid1 gymnastics** · Tue 4:00p–5:00p · Sunnyvale Gymnastics · 30 min drive
  Usually: Randy takes, TL on childcare
- **Grocery run** · Sat morning · Randy

## Upcoming
Items with known dates, not yet in a week file. Organized by timeframe relative to the
Horizon start (the Monday after the authoritative next week):

### Next 2 weeks
Dates within 14 days of the Horizon start (the Monday after next week).
- 2026-08-17 · Kid1 dentist · 10:00a · Dr. Smith · Randy taking
- 2026-08-24 through 2026-08-28 · **9:00a–12:00p** daily (Mon–Fri) · Day camp · pickup at noon

### This month
Same calendar month, beyond 2 weeks out.
- 2026-08-30 · TL work dinner · evening · downtown

### Later
Next month and beyond. Dates can be approximate ("July", "mid-August").
- September · Summer camp registration deadline
- 2026-09-15 · Back to school

## Notes
General scheduling notes, preferences, standing arrangements.
- Randy usually handles weekday afternoon activities
- TL's mom can babysit with 2 days notice
```

An explicit multi-day source is allowed only when the same occurrence body applies to
every day in one contiguous inclusive span. Use full ISO dates on both ends and the word
`through`; weekday prose is descriptive only. Agents must materialize any dates routed
to a current or next dated week as separate daily entries immediately. They must never
write the range representation into a dated weekly file.


## Rendering an entry in the weekly file

Entries are structured bullets. The format is flexible but should be consistent within a
file. Standard shape:

```markdown
- **3:30p–5:30p** Randy — Kid1 gymnastics (activity 4:00–5:00, 30min drive each way)
  TL on childcare · Sunnyvale Gymnastics
```

Decomposed:
```
- **{blocked_time}** {who} — {title} ({activity detail, travel note})
  {childcare note} · {location}
  {notes if any}
```

For proposed items, prefix with `[proposed]`:
```markdown
- **3:30p–5:30p** Randy — Kid1 gymnastics *(proposed by Randy)*
```

For cancelled items, use strikethrough:
```markdown
- ~~**3:30p–5:30p** Randy — Kid1 gymnastics~~ *(cancelled)*
```

All-day or untimed items go at the top of the day section without bold time:
```markdown
- TL work-from-home day
- Randy off
```


## Log entry format

Each log entry in the `## Log` section records the raw interaction:

```markdown
- 2026-06-08 10:15a · Randy — "Kid1 has gymnastics Monday at 4, I'll take her, it's about half an hour away"
- 2026-06-08 10:16a · agent — Confirmed: Mon 3:30p–5:30p, Randy taking Kid1 to gymnastics, TL on childcare
- 2026-06-08 10:20a · TL — "sounds good"
```

Format: `- {date} {time} · {person or agent} — {raw message or action summary}`

The log is append-only. Every message that adds, modifies, or discusses the schedule gets
an entry. Agent actions (confirmations, notifications) are also logged.
