file: apps/math-quiz/learner_profiles/profile_02_mixed-with-holes.md
title: Profile 02 — Mixed Operations with Holes (~9yo)
last-updated: 2026-06-14_1123

A ~9-year-old who knows **most** single-digit addition, subtraction, and multiplication but has specific **holes** — classically the upper multiplication facts (×6–×9) and a few subtraction facts. **Assessment + targeted practice** use case: a moderate number of medium sessions. This profile exercises the adaptive selector's core value: detecting holes from response data and preferentially targeting weak facts while not wasting time on already-fluent ones.

Expected arc: an initial session surfaces the holes (slow/incorrect on ×6–×9) → the selector concentrates presentations on those facts (repair/consolidate tiers) while sampling fluent facts sparingly → holes close to `green` by the final session; already-fluent facts stay `green`/`blue`.

```yaml
profile_id: mixed-with-holes
display_name: "Noah (mixed, ~9)"
persona:
  age: 9
  description: "Solid on most +, -, x facts; specific holes in upper multiplication and some subtraction."
purpose: [assessment, practice]
operations: ["+", "-", "*"]
number_range: [0, 9]
fact_matrix: single-digit

initial_state:
  default: fluent
  overrides:
    - facts: "operation == '*' and (num1 in 6..9 or num2 in 6..9)"   # upper times tables
      level: unknown
    - facts: "operation == '*' and (num1 == 7 or num2 == 7)"         # 7s especially weak
      level: unknown
    - facts: "operation == '-' and num1 in 8..9 and num2 in 4..7"    # a few subtraction holes
      level: emerging

response_model:
  unknown:  { p_correct: 0.50, rt_ms: { dist: lognormal, median: 5500, sigma: 0.5 }, may_idk: true }
  emerging: { p_correct: 0.85, rt_ms: { dist: lognormal, median: 3000, sigma: 0.4 } }
  fluent:   { p_correct: 0.98, rt_ms: { dist: lognormal, median: 1200, sigma: 0.3 } }

learning_model:
  type: exposure-based
  promote_after: 4
  regress_after: 2
  max_new_facts_per_session: 20   # covers all 165 facts within first ~9 sessions

schedule:
  sessions: 30
  problems_per_session: [25, 35]

final_state:
  expectation: "the multiplication holes close to green; previously-fluent facts remain green/blue"
  mastery_target: thorough           # targeted multiplication facts certified
  tolerance: ">=90% of the seeded holes are green by the final session"
  # Behavioral assertion (not just end state): the selector must over-present holes.
  selector_assertion: "seeded-hole facts receive >= 3x the presentations of fluent facts across the run"
```
