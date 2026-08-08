file: skills/education/lesson-logger/README.md
title: Lesson logger — agent skill procedure

**Log a homeschool lesson from natural-language voice or text input.**

Agent procedure for the lesson-logger app. The app code (extraction, save, DB, eval) lives
at `apps/education/lesson-logger/`; this skill defines how an agent orchestrates it.


## When to use
When a user describes a lesson (who, subject, how long, notes) or asks to log/record one.


## Flow
1. **Extract** from the user's message. The extracted fields are (see
   `apps/education/lesson-logger/references/lesson-schema.md` for full rules):
   - `students` — list of kids. Defaults to **Kid1** when none named.
   - `teachers` — named teacher(s), `"self"` for independent learning, or `"not specified"`.
     The save pipeline defaults `"not specified"` to the message sender.
   - `subject` — one of **Math, Reading, Writing, Art, Science, Music**, or a custom subject.
   - `curricula` — book, curriculum, or software program if mentioned.
   - `duration` — minutes as integer. Normalize spoken forms.
   - `location` — where the lesson happened, if mentioned.
   - `date` — defaults to today; `"yesterday"` for yesterday.
   - `time` — time of day if mentioned; empty if not.
   - `notes` — the descriptive detail, lightly cleaned.

2. **Confirm in plain English** before saving — always state the student(s) and teacher so
   wrong defaults are caught:
   > "Got it — **Kid1** with **TL**, **30 min of Math** today, notes: *"fractions, did
   > well"*. Save it?"
   If the user corrects a field, update and re-confirm. **Never save without an explicit yes.**

3. **Save** only after confirmation:
   ```bash
   python3 apps/education/lesson-logger/log_lesson.py \
     --transcript "$TRANSCRIPT" --sender "$SENDER_NAME"
   ```
   Or for manual JSON input:
   ```bash
   printf '%s' "$LESSON_JSON" > /tmp/lesson.json
   python3 apps/education/lesson-logger/scripts/save_lesson.py --in /tmp/lesson.json
   ```
   Report the saved file path back to the user (and any `warning:` lines).


## Notes
- The save pipeline validates and fills `id` / `createdAt` / `extractorVersion` / defaults —
  don't hand-write those.
- If extraction is ambiguous (missing subject or duration), ask one short clarifying question
  rather than guessing.
- Records are JSON session files + SQLite DB rows on the agent's storage volume, not in the repo.
