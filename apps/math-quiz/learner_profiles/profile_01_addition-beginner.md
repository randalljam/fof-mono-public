file: apps/math-quiz/learner_profiles/profile_01_addition-beginner.md
title: Profile 01 — Addition Beginner (~7yo)
last-updated: 2026-06-14_1123

A ~7-year-old just starting single-digit addition. **Practice** use case: many short sessions over time. They count on fingers for most facts, reliably know the trivial ones (`+0`, `+1`) and small doubles, and gradually build fluency. This profile exercises gradual introduction of new facts, within- and across-session adaptation, longitudinal growth, retention, and the `green → blue` permanent upgrade (requires fluency across `permanentSessions` = 5 consecutive sessions).

Expected arc: starts mostly `nodata`/slow → adaptive selector introduces facts a few at a time, repairs weak ones with spaced re-presentation → ends mostly `green`, with the earliest-learned facts reaching `blue`.

```yaml
profile_id: addition-beginner
display_name: "Mia (beginner, ~7)"
persona:
  age: 7
  description: "Learning single-digit addition; counts on fingers for most facts."
purpose: [practice]
operations: ["+"]
number_range: [0, 9]
fact_matrix: single-digit

initial_state:
  default: unknown
  overrides:
    - facts: "num1 in 0..1"            # +0 and +1 facts
      level: fluent
    - facts: "num2 in 0..1"
      level: fluent
    - facts: "doubles up to 5+5"       # 2+2, 3+3, 4+4, 5+5
      level: emerging
    - facts: "sum <= 6"                # small sums easier early
      level: emerging

response_model:
  unknown:  { p_correct: 0.55, rt_ms: { dist: lognormal, median: 6500, sigma: 0.5 }, may_idk: true }
  emerging: { p_correct: 0.85, rt_ms: { dist: lognormal, median: 3200, sigma: 0.4 } }
  fluent:   { p_correct: 0.98, rt_ms: { dist: lognormal, median: 1300, sigma: 0.3 } }

learning_model:
  type: exposure-based
  promote_after: 4
  regress_after: 2
  # New facts introduced gradually so the beginner isn't flooded.
  max_new_facts_per_session: 3

schedule:
  sessions: 50
  problems_per_session: [8, 15]

final_state:
  expectation: "addition 0-9: >=70% green; earliest facts reach blue; no facts red"
  mastery_target: predictive
  tolerance: ">=70% green (count within +/- 2 facts); at least 3 facts blue"
```
