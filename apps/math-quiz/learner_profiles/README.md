file: apps/math-quiz/learner_profiles/README.md
title: Learner Profiles — Simulation Input Schema
last-updated: 2026-06-14_1150

Structured, human-reviewable learner profiles that drive the adaptive-delivery simulation (see `apps/math-quiz/2026-06-14_adaptive-and-profiles-goal.md`). Each `profile_*.md` is **self-contained simulation input**: a prose description for humans plus a fenced `yaml` block the harness parses.

Profiles are drafts — refine field values during the goal run. The schema below is the contract between a profile and the simulation harness.


## Skill levels and how they map to the app
A simulated learner holds a per-fact **skill level**. Levels are the simulation's internal model; the app's fluency *statuses* (`green`/`yellow`/`red`/`gray`/`blue`) are the *output* computed from the emitted attempts.
- `unknown` — not learned; slow, error-prone, may answer "I don't know".
- `emerging` — knows it but counts/computes; usually correct, slow-ish.
- `fluent` — instant recall; fast and correct.

The `response_model` turns a skill level into `(is_correct, response_time_ms)` per attempt. RT distributions should straddle the app thresholds (`greenMs 2000`, `redMs 4000`) so that `fluent` → `green`, `emerging` → `yellow`, `unknown` → `red`/`gray` when imported and evaluated by the real fluency code.


## Schema (fenced `yaml` block in each profile)
```yaml
profile_id: addition-beginner          # stable id; matches the filename slug
display_name: "Mia (beginner, ~7)"
persona:
  age: 7
  description: "Learning single-digit addition; counts on fingers."
purpose: [practice]                     # practice | assessment | demonstration (one or more)
operations: ["+"]                       # canonical ops: + - * / ^
number_range: [0, 9]                    # operand range for the fact matrix
fact_matrix: single-digit               # the operand1 x operand2 grid within number_range

# Initial per-fact skill. `default` applies to all facts; `overrides` adjust subsets.
# Selectors are human-readable; the harness interprets them (e.g. operand ranges, doubles).
initial_state:
  default: unknown                      # unknown | emerging | fluent
  overrides:
    - facts: "num1 in 0..1"             # trivial +0 / +1 facts
      level: emerging
    - facts: "doubles up to 5+5"
      level: emerging

# Map skill level -> answering behavior. rt_ms median should straddle app thresholds.
response_model:
  unknown:  { p_correct: 0.55, rt_ms: { dist: lognormal, median: 6500, sigma: 0.5 }, may_idk: true }
  emerging: { p_correct: 0.85, rt_ms: { dist: lognormal, median: 3200, sigma: 0.4 } }
  fluent:   { p_correct: 0.98, rt_ms: { dist: lognormal, median: 1300, sigma: 0.3 } }

# How skill changes with exposure. Omit (or type: static) for a learner who doesn't change.
learning_model:
  type: exposure-based                  # exposure-based | static
  promote_after: 4                      # consecutive correct-and-fast attempts to advance a level
  regress_after: 2                      # consecutive misses to drop a level

# How many sessions and how big — drives practice (many small) vs assessment (few large).
schedule:
  sessions: 30
  problems_per_session: [5, 10]         # fixed int, or [min, max] range

# The test assertion target after the scheduled sessions are imported + evaluated.
final_state:
  expectation: "addition 0-9: >=70% green, no facts red"
  mastery_target: predictive            # predictive | thorough | none
  tolerance: "status counts within +/- 1 fact"
```


## Easy vs hard facts (global selector concept)
Independent of any single profile, the adaptive selector splits the fact matrix:
- **Easy:** both operands in `0–5`. **Hard:** either operand in `6–9` (`max(num1, num2) ≥ 6`).
The 6–9 combinations are the last facts learners master, so the selector serves hard facts `hard_weight` (3×) more often than easy facts in every priority tier, and predictive mastery requires near-complete hard coverage (`predictive_hard_min_coverage`). See the goal doc → "Easy vs hard facts" and "Decisions" for the canonical params (`hard_weight 3`, `predictive_min_coverage 0.5`, `predictive_hard_min_coverage 0.9`, `mastery_ms 2000`). These live with the engine/harness, not in profiles, but a profile's `final_state`/`mastery_params` may reference them.


## Files
- `profile_01_addition-beginner.md` — practice; longitudinal growth; `blue` upgrades.
- `profile_02_mixed-with-holes.md` — assessment + targeted practice; hole detection.
- `profile_03_proficient-adult.md` — demonstration; both mastery thresholds.
- `states/` — standalone **learner fluency-state files** (app-aligned observed-status snapshots) and their spec. A *profile* describes a simulated learner that *generates* behavior; a *state file* is the *observed* per-fact fluency at a point in time (what a teacher reviews). Each profile has a `*_start.json` baseline snapshot. See `states/README.md`.
