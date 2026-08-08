file: skills/family/schedule-coordinator/references/example-horizon.md
title: Example horizon file — recurring items, upcoming dates, and notes
history:
  - 2026-07-29 · Randy · Codex [multi-day Horizon promotion repair](019fae24-bd13-7821-b421-9b22fb2ce461) — demonstrate the canonical inclusive date-span source form
  - 2026-07-29 · Randy · Codex [family-schedule Next Week](019fae81-a036-78b1-86b4-43decd6a9564) — keep Horizon strictly beyond the current and next dated weeks
  - 2026-06-08 · Randy · Claude Code [schedule-coordinator](https://claude.ai/code/session_01FRAdJZvkLq89hmPU6D2z6x) — initial example

**A sample `horizon_family-schedule.md` showing the structure and range of entries.**

The horizon file is persistent — it lives across weeks. In this example the active dated
files cover Jun 15–21 and Jun 22–28, so Horizon contains only dates from Jun 29 onward.
The agent moves items once into the next dated file as the active window advances. The
`## Recurring` section is never moved — it provides defaults for every new week.

---

```markdown
file: schedule/horizon_family-schedule.md

## Recurring
- **Kid1 gymnastics** · Mon 4:00p–5:00p · Sunnyvale Gymnastics · 30 min drive
  Usually: Randy takes, TL on childcare
- **Grocery run** · Sat morning · Costco · ~30 min drive · Randy
- **Family game night** · Fri 7:00p–8:30p · at home

## Upcoming

### Next 2 weeks
- 2026-06-30 (Tue) · Kid1 dentist · 10:00a · Dr. Smith, Main St · 15 min drive · Randy taking
- 2026-07-07 (Tue) · Summer camp starts (2 weeks) · Kid1 · Camp Redwood
- 2026-07-13 through 2026-07-17 · **9:00a–12:00p** daily (Mon–Fri) · Day camp · pickup at noon

### This month
(nothing else this month)

### Later
- 2026-07-20 (Mon) · Randy's parents visiting · through Jul 27
- 2026-08-15 · Back to school prep

## Notes
- Randy usually handles weekday afternoon activities
- TL's mom can babysit with 2 days notice (call her cell)
- Costco trip can flex to Sunday if Saturday is busy
- Dr. Smith's office: (408) 555-0123
```
