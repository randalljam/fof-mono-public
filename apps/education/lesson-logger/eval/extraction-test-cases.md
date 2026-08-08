file: apps/education/lesson-logger/eval/extraction-test-cases.md
title: Lesson-logger extraction test cases (transcript → ground truth)
history:
  - 2026-06-09 · Randy · Claude Code — teachers: "not specified" for ambiguous, "self" for independent, new case 16
  - 2026-06-09 · Randy · Claude Code — add time field to all cases, new cases 14–15 exercise time
  - 2026-06-08 · Randy · Claude Code — add teachers/curricula/location fields, new cases 11–13

**Lesson-logger extraction test cases**

Hand-written transcript → ground-truth pairs to exercise the LLM field extraction in the
`lesson-logger` skill. They span phrasing variety (spoken durations, subject synonyms,
custom subjects, default vs named students, multi-student, relative dates, terse input,
teachers, curricula, locations).

**How to read this:** each case has a `Transcript` (what TL might say/type) and an
`Expected` block. Conventions:
- `date`: `today` = the day the entry is logged; `yesterday` = day before. (Resolve relative
  to run date.)
- `students`: the canonical list; omitted-name cases expect `["Kid1"]` (the default).
- `teachers`: `["not specified"]` when the transcript doesn't mention a teacher; `["self"]` for
  explicit independence; named person(s) when stated.
- `curricula`: empty string `""` unless a book/curriculum/program is mentioned.
- `location`: empty string `""` unless a place is mentioned.
- `time`: empty string `""` unless a time of day is mentioned.
- `notes`: ground truth is the **gist**, not character-exact — an eval harness should assert
  `students` / `subject` / `duration` / `date` exactly and check `notes` for key content only.

---

### Case 1 — named, explicit duration + subject
**Transcript:** "Kid1 spent thirty minutes on math today, working on fractions. She finally got common denominators."
**Expected:**
```json
{"students": ["Kid1"], "teachers": ["not specified"], "subject": "Math", "curricula": "", "duration": 30, "location": "", "date": "today", "time": "", "notes": "fractions; got common denominators"}
```

### Case 2 — no name (defaults to Kid1), "half an hour", curricula mentioned
**Transcript:** "Did about half an hour of reading — two chapters of Charlotte's Web, read aloud."
**Expected:**
```json
{"students": ["Kid1"], "teachers": ["not specified"], "subject": "Reading", "curricula": "Charlotte's Web", "duration": 30, "location": "", "date": "today", "time": "", "notes": "two chapters, read aloud"}
```

### Case 3 — "an hour and a half", writing, no teacher mentioned
**Transcript:** "Kid1 worked on her handwriting for an hour and a half. Cursive lowercase, getting much neater."
**Expected:**
```json
{"students": ["Kid1"], "teachers": ["not specified"], "subject": "Writing", "curricula": "", "duration": 90, "location": "", "date": "today", "time": "", "notes": "cursive lowercase, neater"}
```

### Case 4 — custom subject (history), "forty-five minutes"
**Transcript:** "Forty-five minutes of history today — read about ancient Egypt and she drew a pyramid."
**Expected:**
```json
{"students": ["Kid1"], "teachers": ["not specified"], "subject": "History", "curricula": "", "duration": 45, "location": "", "date": "today", "time": "", "notes": "ancient Egypt; drew a pyramid"}
```

### Case 5 — multi-student (co-op), science, location, informal time
**Transcript:** "At co-op this morning Kid1 and her friend Mia did a 45 minute science experiment — baking-soda volcanoes."
**Expected:**
```json
{"students": ["Kid1", "Mia"], "teachers": ["not specified"], "subject": "Science", "curricula": "", "duration": 45, "location": "co-op", "date": "today", "time": "morning", "notes": "baking-soda volcano experiment"}
```

### Case 6 — relative date (yesterday), music, "twenty minutes"
**Transcript:** "Yesterday Kid1 practiced piano for twenty minutes."
**Expected:**
```json
{"students": ["Kid1"], "teachers": ["not specified"], "subject": "Music", "curricula": "", "duration": 20, "location": "", "date": "yesterday", "time": "", "notes": "piano practice"}
```

### Case 7 — long lesson (no cap), art, "two hours"
**Transcript:** "Kid1 was really into it and painted for two hours straight — watercolors of the backyard."
**Expected:**
```json
{"students": ["Kid1"], "teachers": ["not specified"], "subject": "Art", "curricula": "", "duration": 120, "location": "", "date": "today", "time": "", "notes": "watercolors of the backyard"}
```

### Case 8 — subject synonym + "a quarter of an hour", no name, informal time
**Transcript:** "Quick one this afternoon — a quarter of an hour on times tables."
**Expected:**
```json
{"students": ["Kid1"], "teachers": ["not specified"], "subject": "Math", "curricula": "", "duration": 15, "location": "", "date": "today", "time": "afternoon", "notes": "times tables"}
```

### Case 9 — writing, journal, "25 minutes"
**Transcript:** "Kid1 did 25 minutes of writing — a journal entry about our hike on Saturday."
**Expected:**
```json
{"students": ["Kid1"], "teachers": ["not specified"], "subject": "Writing", "curricula": "", "duration": 25, "location": "", "date": "today", "time": "", "notes": "journal entry about the hike"}
```

### Case 10 — terse, no name
**Transcript:** "40 min reading."
**Expected:**
```json
{"students": ["Kid1"], "teachers": ["not specified"], "subject": "Reading", "curricula": "", "duration": 40, "location": "", "date": "today", "time": "", "notes": ""}
```

### Case 11 — teacher named, curricula, location
**Transcript:** "TL taught Kid1 math for an hour at the kitchen table using Singapore Math 4A. They covered chapter 3 on fractions."
**Expected:**
```json
{"students": ["Kid1"], "teachers": ["TL"], "subject": "Math", "curricula": "Singapore Math 4A", "duration": 60, "location": "kitchen table", "date": "today", "time": "", "notes": "chapter 3 on fractions"}
```

### Case 12 — software curricula, self-directed (no teacher)
**Transcript:** "Kid1 spent 45 minutes on Khan Academy doing multiplication drills."
**Expected:**
```json
{"students": ["Kid1"], "teachers": ["self"], "subject": "Math", "curricula": "Khan Academy", "duration": 45, "location": "", "date": "today", "time": "", "notes": "multiplication drills"}
```

### Case 13 — multi-student, teacher, location, yesterday
**Transcript:** "Yesterday at the library, Mrs. Chen led Kid1 and Mia through a 30-minute science lesson on magnets."
**Expected:**
```json
{"students": ["Kid1", "Mia"], "teachers": ["Mrs. Chen"], "subject": "Science", "curricula": "", "duration": 30, "location": "library", "date": "yesterday", "time": "", "notes": "magnets"}
```

### Case 14 — explicit time of day, teacher, curricula
**Transcript:** "At 2:30 this afternoon TL read with Kid1 for an hour — they're on chapter 8 of Charlotte's Web."
**Expected:**
```json
{"students": ["Kid1"], "teachers": ["TL"], "subject": "Reading", "curricula": "Charlotte's Web", "duration": 60, "location": "", "date": "today", "time": "2:30 PM", "notes": "chapter 8"}
```

### Case 15 — morning time, no name, terse
**Transcript:** "This morning at 9 Kid1 did 20 minutes of math drills."
**Expected:**
```json
{"students": ["Kid1"], "teachers": ["not specified"], "subject": "Math", "curricula": "", "duration": 20, "location": "", "date": "today", "time": "9 AM", "notes": "math drills"}
```

### Case 16 — explicit self-directed, "on her own"
**Transcript:** "Kid1 read on her own for 40 minutes — finished the last two chapters of Charlotte's Web."
**Expected:**
```json
{"students": ["Kid1"], "teachers": ["self"], "subject": "Reading", "curricula": "Charlotte's Web", "duration": 40, "location": "", "date": "today", "time": "", "notes": "finished the last two chapters"}
```
