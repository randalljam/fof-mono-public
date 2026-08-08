file: skills/family/schedule-coordinator/references/example-rollover/after/2026-06-22_week_family-schedule.md
title: Rollover test — after state — week of Jun 22–28 (new next week)
history:
  - 2026-07-29 · Randy · Codex [automatic family-schedule rollover](019fae24-bd13-7821-b421-9b22fb2ce461) — distinguish deterministic Horizon moves from separately confirmed recurring expansion
  - 2026-07-29 · Randy · Codex [family-schedule Next Week](019fae81-a036-78b1-86b4-43decd6a9564) — add newly exposed next-week after state

**Set 2 (after the active window advances to Jun 15).** The gate created only the newly
exposed next week, Jun 22–28. The Jun 23 science museum trip and Jun 28 party-planning
item moved automatically from Horizon into this dated source. The recurring items shown
were expanded through the separate confirmed agent workflow; the deterministic scheduler
does not interpret recurring defaults.

---

```markdown
file: schedule/2026-06-22_week_family-schedule.md
week: Mon 2026-06-22 — Sun 2026-06-28

## Monday Jun 22
- **3:30p–5:30p** Randy — Kid1 gymnastics (activity 4:00–5:00, 30min drive each way)
  TL on childcare · Sunnyvale Gymnastics

## Tuesday Jun 23
- **9:15a–1:15p** TL + Kid1 — science museum field trip (museum 10:00a–12:30p, 45min drive each way)
  Bay Area Discovery Museum · pack lunch

## Wednesday Jun 24
(nothing scheduled)

## Thursday Jun 25
(nothing scheduled)

## Friday Jun 26
- **7:00p–8:30p** Family — game night at home

## Saturday Jun 27
- **9:00a–10:30a** Randy — grocery run (Costco, ~30min drive)
  TL on childcare

## Sunday Jun 28
- Kid1's birthday party planning · afternoon · at home · Family

## Log
- 2026-06-15 · system — Weekly boundary prepared Next Week; moved Jun 23 science museum plus Jun 28 party planning from Horizon.
- 2026-06-15 7:15a · agent — User confirmed the recurring Jun 22–28 population. Added gymnastics, game night, and grocery run.
```
