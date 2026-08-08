file: skills/family/schedule-coordinator/references/example-week.md
title: Example weekly schedule file — template and sample entries
history:
  - 2026-06-08 · Randy · Claude Code [schedule-coordinator](https://claude.ai/code/session_01FRAdJZvkLq89hmPU6D2z6x) — initial example

**A concrete example of what a weekly schedule file looks like.**

The agent uses this as a template when creating new week files. Entries below are
fictional but illustrate the range of real scenarios: travel time, childcare handoffs,
all-day items, proposed vs confirmed, cancellations, and the log section.

---

```markdown
file: schedule/2026-06-15_week_family-schedule.md
week: Mon 2026-06-15 — Sun 2026-06-21

## Monday Jun 15
- TL work-from-home day
- **3:30p–5:30p** Randy — Kid1 gymnastics (activity 4:00–5:00, 30min drive each way)
  TL on childcare · Sunnyvale Gymnastics

## Tuesday Jun 16
- **9:45a–11:00a** Randy — Kid1 dentist (appt 10:00–10:30, 15min drive each way)
  TL on childcare · Dr. Smith, Main St
- **6:00p–9:00p** TL — work dinner downtown *(proposed by TL)*
  Randy on childcare · picks up dinner on the way back so more like 9

## Wednesday Jun 17
(nothing scheduled)

## Thursday Jun 18
- **12:00p–1:00p** Randy + TL — lunch together
  Kid1 at school · downtown

## Friday Jun 19
- ~~**4:00p–6:00p** Randy — Kid1 swim lesson~~ *(cancelled — pool closed)*

## Saturday Jun 20
- **9:00a–10:30a** Randy — grocery run (Costco, ~30min away)
  TL on childcare
- **2:00p–4:00p** Family — park playdate with the Johnsons
  Sunnyvale Central Park · bring snacks

## Sunday Jun 21
(nothing scheduled)

## Log
- 2026-06-13 4:30p · Randy — "Kid1 has gymnastics again Monday, same time, I'll take her"
- 2026-06-13 4:31p · agent — Confirmed: Mon 3:30p–5:30p, Randy taking Kid1 to gymnastics (recurring). TL on childcare.
- 2026-06-13 6:00p · TL — "I have a work dinner Tuesday evening, probably 6 to 9, it's downtown"
- 2026-06-13 6:01p · agent — Proposed: Tue 6:00p–9:00p, TL work dinner downtown. Randy on childcare. Notified Randy.
- 2026-06-13 6:05p · Randy — "sounds good, I'll have the kids"
- 2026-06-13 6:05p · agent — Confirmed Tue work dinner. Randy on childcare.
- 2026-06-14 9:00a · Randy — "oh and Kid1's dentist is Tuesday at 10, it's at Dr. Smith on Main, about 15 min away"
- 2026-06-14 9:01a · agent — Confirmed: Tue 9:45a–11:00a, Randy taking Kid1 to dentist. TL on childcare. No conflicts with TL's evening dinner.
- 2026-06-14 10:00a · Randy — "let's do lunch Thursday, just us, noon downtown"
- 2026-06-14 10:00a · agent — Confirmed: Thu 12:00p–1:00p, Randy + TL lunch. Kid1 at school. Notified TL.
- 2026-06-14 10:02a · TL — "yes! sounds great"
- 2026-06-15 8:00a · Randy — "cancel Friday swim, pool is closed"
- 2026-06-15 8:00a · agent — Cancelled: Fri 4:00p–6:00p swim lesson (pool closed).
- 2026-06-17 7:30p · TL — "actually I'll probably pick up dinner on the way back Tuesday so more like 9 by the time I'm home"
- 2026-06-17 7:31p · agent — Updated Tue dinner: TL blocked until ~9:00p (picks up dinner on the way back). Randy on childcare until 9.
```
