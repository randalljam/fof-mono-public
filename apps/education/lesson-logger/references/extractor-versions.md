file: apps/education/lesson-logger/references/extractor-versions.md
title: Lesson-logger extractor version history

Tracks the extraction pipeline version stamped into each saved lesson entry
(`extractorVersion` field). The version in `scripts/extract_lesson.py:EXTRACTOR_VERSION`
is the source of truth; this file is the human+machine readable changelog.

Bump the version when: the tool schema changes (fields added/removed/renamed), the system
prompt changes in a way that affects extraction behavior, or the default model changes.
Don't bump for eval-only or test-case changes.

Format: semver (`MAJOR.MINOR.PATCH`). MAJOR = breaking schema change (field removed or
type changed); MINOR = new field or behavioral change; PATCH = prompt tuning, model change,
bug fix. Start real versioning (1.1.0+) once production data is being generated.


## Versions

### 1.0.0
- **Date:** 2026-06-08
- **Model:** gpt-4.1-mini (default)
- **Extracted fields:** students, teachers, subject, curricula, duration, location, date, time, notes
- **Notes:** Initial versioned release. 9 extracted fields via OpenAI function calling with
  strict mode. All 13 eval cases pass (full pass) on gpt-4.1-mini.
