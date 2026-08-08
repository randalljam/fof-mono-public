file: skills/family/schedule-coordinator/eval/extraction-test-cases.md
title: Schedule-coordinator extraction test cases (transcript → ground truth)
history:
  - 2026-07-29 · Randy · Codex [family-schedule Next Week](019fae81-a036-78b1-86b4-43decd6a9564) — add explicit next-week dated-source routing and move Horizon coverage beyond the active two-week window
  - 2026-06-12 · Randy · Claude Code [schedule-coordinator](https://claude.ai/code/session_01FRAdJZvkLq89hmPU6D2z6x) — initial test cases

**Schedule-coordinator extraction test cases.**

Thirteen hand-written transcript → ground-truth pairs to exercise the LLM field extraction in the
`schedule-coordinator` skill. They cover phrasing variety (explicit/implicit travel,
blocked time computation, childcare, recurring items, horizon items, schedule queries,
modifications, and cancellations).

**How to read this:** each case has a `Transcript` (what Randy or TL might say/type
via voice or text in Telegram) and an `Expected` block.

Conventions:
- `date`: relative to the day the message is sent (today, tomorrow, Thursday, etc.)
- `blocked_time`: the full unavailable window (travel + activity + errands)
- `childcare`: who's on kid duty — omitted for "Family" entries
- Fields marked `ask` mean the agent should ask the user for that info before saving
- An eval harness should assert `date`, `time`, `who`, `blocked_time`, and `childcare`
  exactly; check `title` and `notes` for key content only.

---

### Case 1 — explicit travel, simple entry
**Transcript:** "Kid1 has gymnastics Monday at 4, I'll take her, it's about 30 minutes away."
**Expected:**
```json
{"date": "Monday", "time": "4:00p–5:00p", "blocked_time": "3:30p–5:30p", "title": "Kid1 gymnastics", "who": "Randy", "travel": "30 min", "childcare": "TL", "location": "ask"}
```
**Notes:** Duration of gymnastics defaults to 1 hour (common for kids' activities). Agent should confirm. Travel is explicitly stated.

### Case 2 — no travel time stated (agent should ask)
**Transcript:** "I have a dentist appointment Wednesday at 10."
**Expected:**
```json
{"date": "Wednesday", "time": "10:00a", "blocked_time": "ask", "title": "dentist appointment", "who": "Randy", "travel": "ask", "childcare": "TL"}
```
**Notes:** Travel unknown → agent must ask before computing blocked time. Duration also unknown (dentist could be 30 min or 90 min) — agent should ask or estimate and confirm.

### Case 3 — travel with errands, extended blocked time
**Transcript:** "TL's taking the kids to swim lessons Saturday at 10, it's about 20 minutes, and she'll probably pick up groceries on the way back so figure she'll be gone till noon."
**Expected:**
```json
{"date": "Saturday", "time": "10:00a–11:00a", "blocked_time": "9:40a–12:00p", "title": "swim lessons", "who": "TL + kids", "travel": "20 min", "notes": "picks up groceries on the way back", "childcare": "n/a (kids are with TL)"}
```
**Notes:** Kids go with TL, so no childcare gap. Blocked time extends past activity end due to errands. The "noon" end time comes from the user's estimate.

### Case 4 — both parents out (childcare conflict)
**Transcript:** "I have a meeting downtown Thursday from 2 to 4, about 25 minutes away."
**Context:** TL already has an entry Thursday 3:00p–5:00p.
**Expected:**
```json
{"date": "Thursday", "time": "2:00p–4:00p", "blocked_time": "1:35p–4:25p", "title": "meeting downtown", "who": "Randy", "travel": "25 min", "conflict": "CHILDCARE GAP — overlaps with TL's 3:00p–5:00p entry. Both parents out ~3:00p–4:25p."}
```
**Notes:** Agent should flag the overlap and not save until the user resolves it.

### Case 5 — next-week dated source
**Reference date:** Wednesday 2026-07-29 Pacific (current week starts Jul 27; next week starts Aug 3).
**Transcript:** "Next Wednesday at 10 we're taking Kid1 to the science museum."
**Expected:**
```json
{"target": "2026-08-03_week_family-schedule.md", "date": "2026-08-05", "time": "10:00a", "title": "science museum", "who": "Family", "travel": "ask"}
```
**Notes:** Must resolve to the durable next Monday-dated file, conflict-check that file, confirm, save under Wednesday, and append its log. It must not go to Horizon or a `next-week.md` cache.

### Case 6 — horizon item (after next Sunday)
**Reference date:** Wednesday 2026-07-29 Pacific.
**Transcript:** "Randy's parents are coming to visit the week of August 17th."
**Expected:**
```json
{"target": "horizon_family-schedule.md", "section": "Next 2 weeks", "date": "2026-08-17", "title": "Randy's parents visiting", "notes": "week of Aug 17", "who": "family"}
```
**Notes:** No specific time and outside current/next week, so it goes to Horizon once. No weekly conflict check is needed until population moves it into a dated file.

### Case 7 — schedule query (today)
**Transcript:** "What's on today?"
**Expected behavior:** Agent reads today's section from the current week file and reports all entries with blocked times. If nothing scheduled, says so.

### Case 8 — availability check
**Transcript:** "Are we free Saturday afternoon?"
**Expected behavior:** Agent reads Saturday's entries from the week file, checks both parents' blocked times during "afternoon" (roughly 12p–5p), and reports whether both are available. If one parent has something, reports who's free and who isn't.

### Case 9 — cancellation
**Transcript:** "Cancel the swim lesson on Friday."
**Expected behavior:** Agent finds the swim lesson entry under Friday, marks it with ~~strikethrough~~ and `(cancelled)`, appends to the log. Does NOT delete the entry.

### Case 10 — modification
**Transcript:** "Actually the dentist moved to 11 instead of 10."
**Expected behavior:** Agent finds the dentist entry, updates the time from 10:00a to 11:00a, recomputes blocked time, updates the entry in place, appends the change to the log.

### Case 11 — recurring activity (known travel)
**Transcript:** "Gymnastics again Monday, same as usual."
**Context:** `horizon_family-schedule.md` has recurring entry: `**Kid1 gymnastics** · Mon 4:00p–5:00p · Sunnyvale Gymnastics · 30 min drive / Usually: Randy takes, TL on childcare`
**Expected:**
```json
{"date": "Monday", "time": "4:00p–5:00p", "blocked_time": "3:30p–5:30p", "title": "Kid1 gymnastics", "who": "Randy", "travel": "30 min (from recurring)", "childcare": "TL", "location": "Sunnyvale Gymnastics"}
```
**Notes:** Agent matches against recurring items and uses stored defaults. Should still confirm but can pre-fill all fields.

### Case 12 — terse voice memo
**Transcript:** "TL work dinner Thursday evening."
**Expected:**
```json
{"date": "Thursday", "time": "evening (ask for specifics)", "title": "work dinner", "who": "TL", "childcare": "Randy", "travel": "ask", "location": "ask"}
```
**Notes:** "Evening" is vague — agent should ask for approximate times before saving. Travel and location unknown.

### Case 13 — "we" / family entry
**Transcript:** "We're going to the park Sunday around 2, should be a couple hours."
**Expected:**
```json
{"date": "Sunday", "time": "2:00p–4:00p", "blocked_time": "2:00p–4:00p", "title": "park", "who": "Family", "travel": "ask (or minimal)", "notes": "couple hours"}
```
**Notes:** "We" = family entry. No childcare line needed. Travel may be minimal (local park) — agent can ask or assume short if not stated.
