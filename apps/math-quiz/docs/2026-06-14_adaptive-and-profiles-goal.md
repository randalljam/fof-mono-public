file: apps/math-quiz/2026-06-14_adaptive-and-profiles-goal.md
title: Math Quiz — Adaptive Delivery & Learner Profiles Goal
last-updated: 2026-06-14_1300
ai: Claude Code (cloud) — Opus
session: `math quiz goal`

Tracking doc and **executable specification** for making the math quiz adaptive, proven by simulated learner profiles. This file is self-contained: the `/goal` run reads it and achieves the **Objective** below. Detailed design follows; the three profile drafts in `apps/math-quiz/learner_profiles/` are the structured simulation inputs.


## Objective — read this file and achieve it (success criteria)
Build an adaptive problem-delivery engine for the math quiz and prove it with a deterministic simulation over three learner profiles. **Encode every criterion below as an automated test**, so success reduces to the test suite passing. The run is complete when **all** of SC1–SC8 hold:

- **SC1 — Adaptive selector.** A DOM-free, shared, seeded engine picks the next problem from the current per-fact fluency state, biasing by (a) priority tier — `repair` > `consolidate` > `introduce` > `confirm` — and (b) **hard facts over easy facts** by the configured `hard_weight` (see "Easy vs hard facts"). Unit-tested.
- **SC2 — Simulation harness.** For each profile, a simulated learner answers selector-chosen problems and the harness emits canonical session JSON that is imported via the **real** `importSessionData()` and evaluated by the **real** fluency code (`evaluateFluencyStatus`, `checkPermanentStatus`). Fully deterministic via a seed derived from `profile_id` (+ run name).
- **SC3 — Per-profile end state.** Each profile's resulting fluency state matches its declared `final_state` within tolerance: beginner ends mostly `green` with ≥ 3 `blue`; mixed-with-holes has its seeded holes detected and closed to `green`; adult per SC4/SC5.
- **SC4 — Predictive mastery (fast/short).** The adult `predictive-short` run trips predictive mastery from a *partial* sample: overall coverage ≥ `predictive_min_coverage` (0.5) **and** hard-fact coverage ≥ `predictive_hard_min_coverage` (0.9), with all sampled facts `green` and accuracy ≥ `minAccuracy` (0.8). I.e. the hard facts are near-completely covered even though the full matrix is not.
- **SC5 — Thorough mastery (complete).** The adult `thorough-complete` run certifies mastery: every in-scope fact attempted ≥ 1 time, correct, each within `mastery_ms` (2000).
- **SC6 — Hard preference works.** A test proves the selector preferentially serves hard facts: for a uniformly-fluent learner, hard facts receive ≥ `hard_weight`× the presentations of easy facts, and hard-fact coverage in the predictive sample exceeds easy-fact coverage.
- **SC7 — Hole targeting works.** A test proves the mixed-with-holes profile's seeded-hole facts receive ≥ 3× the presentations of fluent facts across its run.
- **SC8 — All tests green.** `cd apps/math-quiz/tests && npm run test:all` exits 0, with the new tests above plus all pre-existing tests passing.

**Constraints:** do not weaken these criteria, the profile `final_state` targets, or existing tests to pass. Keep selector logic DOM-free and testable. Build the selector as a shared engine exercised by the simulation only this round; live-UI integration is a follow-up (Decision 9). **Bound: stop after 25 turns.**


## Decisions (locked 2026-06-14)
All recommendations accepted; plus the easy/hard requirement added this round.
1. **Operation scope:** `+`, `−`, `×` only. (`/`, `^` deferred.)
2. **Fact matrix:** operands `0–9`, ordered (`3+4` ≠ `4+3`). Addition & multiplication = full 100 cells; subtraction restricted to `num1 ≥ num2` (non-negative → 55 facts).
3. **`predictive_min_coverage`:** `0.5` overall (tunable param).
4. **`mastery_ms`:** `2000` (== `greenMs`).
5. **`max_new_facts_per_session` (beginner):** `3` (per-profile field).
6. **`final_state` assertions:** aggregate thresholds with small count tolerance, not exact per-fact match.
7. **Determinism:** seeded RNG from `profile_id` (+ run name). Required.
8. **Simulation runtime:** `apps/math-quiz/simulation/` (Node), reusing `tests/load_app.mjs` to call real browser functions in a vm. Session JSON in-memory for tests; optional `--dump` to gitignored `math-quiz_data/` for review.
9. **Integration:** shared DOM-free selector engine this round (in `math_utils.js` or a new shared module); live quiz UI wiring is a follow-up.
10. **Goal turn cap:** `25`.
11. **Easy/hard facts (new):** a fact is **hard** iff `max(num1, num2) ≥ 6`, else **easy**. The selector gives hard facts `hard_weight = 3`× the selection weight of easy facts across all tiers. Predictive mastery additionally requires `predictive_hard_min_coverage = 0.9`. All these are tunable params.


## Vision and use cases
The app already records per-attempt response time and correctness and computes per-fact fluency. The goal is to **use that signal to choose the next problem** — within a session and across sessions — and keep an always-reviewable fluency state. Two first-class use cases:
1. **Practice** — many short sessions over time; the engine grows fluency, introducing new facts and revisiting weak ones (spaced practice).
2. **Assessment / demonstration** — a proficient learner demonstrates mastery **quickly, in minutes**, without grinding every problem.

The hard/easy preference matters for both: the 6–9 combinations are the last facts learners master, so they deserve disproportionate coverage — especially in the fast predictive path, where easy facts can be inferred but hard facts should be nearly all confirmed.


## Easy vs hard facts
- **Easy:** both operands in `0–5`. **Hard:** either operand in `6–9` (`max(num1, num2) ≥ 6`).
- The selector applies `hard_weight` (3×) to hard facts in every priority tier, so a learner answering a mix is preferentially served the harder ones.
- **Coverage consequence:** for a fixed sample size, hard facts reach near-complete coverage well before easy ones — which is exactly what predictive mastery needs (SC4).


## Grounding in the existing app
Reuse what's already in the code — do not invent a parallel model.
- **Fluency statuses** (`math_fluency.js` → `evaluateFluencyStatus`): `nodata`, `gray` (accuracy < `minAccuracy`), `red` (median ≥ `redMs`), `yellow` (`greenMs` ≤ median < `redMs`), `green` (median < `greenMs`), `blue` (permanent — `green` for `permanentSessions` consecutive sessions via `checkPermanentStatus`).
- **Default thresholds** (`defaultFluencyThresholds`): `windowSize 5`, `minAccuracy 0.8`, `greenMs 2000`, `redMs 4000`, `retentionSessions 3`, `permanentSessions 5`. Use these unless a profile overrides them.
- **Canonical fact form:** `problem_text` like `5 + 3`, `5 * 3` (see `AGENTS.md`); fact key = `(operation, num1, num2)`, order significant.
- **Session artifact** consumed by `importSessionData()`: `{ user, session: { id, start_time, end_time, settings: { num_problems, number_range, numbers_include, numbers_exclude, num_numbers, operations }, summary: { total_problems, correct_answers, average_response_time_ms }, problems: [ { id, problem_text, correct_answer, user_answer_string, user_answer, is_correct, response_time_ms, flags } ] } }`. Emitting real session JSON exercises the real import + fluency code, not a mock.


## Adaptive algorithm (design)
The selector maintains a live per-fact estimate (seeded from prior sessions' fluency state) and picks the next problem to maximize learning-or-confirmation value.

Priority tiers (highest first), within the profile's in-scope operations and number range:
1. **Repair** — facts currently `red`/`gray` or just missed/slow this session (re-present with spacing, not immediately).
2. **Consolidate** — `yellow` facts near the fluency boundary.
3. **Introduce** — `nodata` facts, gradually (cap via `max_new_facts_per_session`).
4. **Confirm/maintain** — `green`/`blue` facts sampled sparingly to detect regression.

Within each tier, candidate weight is multiplied by `hard_weight` for hard facts. Net behavior: weakest-and-hardest first, with easy/fluent facts touched least.
- **Within-session:** after each answer, update the running estimate; correct-and-fast deprioritizes, wrong-or-slow re-queues with spacing.
- **Session-to-session:** at session start, load prior fluency state/history and seed the tiers.
- **Optional pretest:** a short adaptive pretest brackets the competence boundary to set initial priorities for an unknown-state learner.


## Two mastery determinations (outputs)
Computed from the imported sessions so they appear in the reviewable fluency state.
- **Predictive mastery (fast/short)** — infer mastery of a set without testing every cell. Fires when overall sampled coverage ≥ `predictive_min_coverage` (0.5) **and** hard-fact coverage ≥ `predictive_hard_min_coverage` (0.9), **all** sampled facts `green`, accuracy ≥ `minAccuracy`. The "demonstrate in minutes" path.
- **Thorough mastery (complete/certified)** — every fact in the matrix attempted ≥ 1 time, correct, each within `mastery_ms` (2000). The certified path.


## Simulation harness (design)
Location `apps/math-quiz/simulation/` (Node), reusing `tests/load_app.mjs` to call the **real** browser functions in a vm (the unit-test technique). New tests live in `tests/`.

Flow per profile:
1. Load the profile (`learner_profiles/*.md` → its `yaml` block).
2. Instantiate a **simulated learner** = a response model: given a fact and the learner's current per-fact skill level, produce `(is_correct, response_time_ms)` from that level's accuracy + RT distribution, using the profile's seed.
3. For each scheduled session, run the **adaptive selector** to choose problems, feed the learner, emit canonical session JSON.
4. For practice profiles, apply the **learning model** so skill improves across exposures toward `final_state`.
5. Import sessions via real `importSessionData()`; run the real fluency tracker.
6. **Assert** the resulting fluency state matches `final_state` (within tolerance) and the mastery determinations fire as expected.


## Profiles (summary)
Full drafts in `apps/math-quiz/learner_profiles/` (one self-contained markdown each; schema in that folder's `README.md`).
1. **`profile_01_addition-beginner`** — ~7yo, **practice**, ~30 short sessions (5–10). Mostly `nodata`/slow → mostly `green` with `blue` upgrades. Exercises gradual introduction, longitudinal growth, retention.
2. **`profile_02_mixed-with-holes`** — ~9yo, **assessment + targeted practice**, ~12 medium sessions (15–25). Holes in ×6–×9 (hard facts). Exercises hole detection + adaptive targeting; holes close.
3. **`profile_03_proficient-adult`** — proficient adult, **demonstration**, 1 intensive session (40 → full matrix). Exercises both mastery thresholds and hard-preferential sampling: predictive mastery in minutes (hard near-complete), thorough mastery when complete.


## How to run (goal command)
The `/goal` command references this file; the run reads it and works to the Objective. Switch the model to **Sonnet** (`/model`) before firing. The exact command is provided in the chat handoff; it bounds the run at 25 turns and anchors completion on `npm run test:all` exiting 0 with the new tests encoding SC1–SC8.


## Status / progress
- [x] Goal + executable spec documented; decisions locked; profiles drafted and approved.
- [x] Adaptive selector (DOM-free, seeded, tiered, hard-weighted) — SC1. (`simulation/adaptive_selector.mjs`)
- [x] Simulation harness + simulated-learner response model — SC2. (`simulation/simulation.mjs`)
- [x] Per-profile end-state assertions — SC3. (beginner ≥70% green, ≥3 blue, 0 red; holes ≥90% closed)
- [x] Predictive + thorough mastery determinations — SC4, SC5.
- [x] Hard-preference + hole-targeting tests — SC6, SC7.
- [x] `npm run test:all` green — SC8. (63 unit + 17 E2E = 80 tests, all passing)
- [ ] (Follow-up) integrate selector into the live quiz UI.
