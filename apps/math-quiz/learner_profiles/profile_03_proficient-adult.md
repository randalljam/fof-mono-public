file: apps/math-quiz/learner_profiles/profile_03_proficient-adult.md
title: Profile 03 — Proficient Adult (mastery demonstration)
last-updated: 2026-06-14_1150

A proficient adult who already knows single-digit +, −, × cold. **Demonstration** use case: prove mastery **quickly, in minutes**. This profile is the primary test of the two mastery determinations:
- **Predictive mastery (short)** — from a short sample (a few dozen problems, *not* the whole matrix), all answered fast and correct, the system infers mastery of the full set.
- **Thorough mastery (complete)** — every fact in the matrix attempted at least once and answered correctly within `mastery_ms`, certifying the full set.

The learner is **static** (no learning model — they don't improve, they already know it). The simulation should run two passes from the same profile: a short pass that must trip predictive mastery, and a complete pass that must trip thorough mastery. Because the selector prefers **hard facts** (operands 6–9) at `hard_weight` (3×), the short pass achieves near-complete coverage of the hard facts while only sampling the easy ones — which is precisely what predictive mastery is allowed to infer from.

```yaml
profile_id: proficient-adult
display_name: "Sam (proficient adult)"
persona:
  age: adult
  description: "Fluent in all single-digit +, -, x facts; here to demonstrate mastery fast."
purpose: [demonstration, assessment]
operations: ["+", "-", "*"]
number_range: [0, 9]
fact_matrix: single-digit

initial_state:
  default: fluent

response_model:
  fluent: { p_correct: 0.99, rt_ms: { dist: lognormal, median: 1100, sigma: 0.25 } }

learning_model:
  type: static

# Two runs from one profile exercise the two mastery thresholds.
runs:
  - name: predictive-short
    schedule: { sessions: 1, problems_per_session: 80 }   # well under full matrix (165 for 3 ops)
    mastery_target: predictive
  - name: thorough-complete
    schedule: { sessions: 1, problems_per_session: full-matrix }  # >= 1 of every fact in scope
    mastery_target: thorough

# Mastery determination parameters (see goal doc "Two mastery determinations").
mastery_params:
  predictive_min_coverage: 0.45         # overall fraction of matrix sampled (80/165 ≈ 0.485 with 80 probs)
  predictive_hard_min_coverage: 0.8     # hard fraction of sampled facts must be >= 0.8 (hard_weight=3 gives ~0.83)
  mastery_ms: 2000                      # per-fact time bar for thorough mastery (== greenMs)

final_state:
  expectation: "predictive-short trips predictive mastery in minutes (hard facts near-complete); thorough-complete certifies every fact"
  mastery_target: both
  tolerance: "predictive fires with overall coverage < 100% but hard coverage >= 0.9; thorough requires 100% coverage all within mastery_ms"
```
