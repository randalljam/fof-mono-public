file: apps/math-quiz/learner_profiles/states/README.md
title: Learner Fluency-State Files — Specification
last-updated: 2026-06-14_1500

A **learner fluency-state file** is a standalone, app-aligned snapshot of what one learner currently knows — the per-fact *observed* fluency status (`green`/`yellow`/`red`/`gray`/`blue`/`nodata`), not the simulation's hidden skill level. It is shaped to match what the fluency tracker itself produces (`downloadFluencyData()` → `fluency_data_<date>.json`, `version: "2.0"`), so a file in this format could be loaded back into the app or handed to the adaptive selector as its session-to-session seed.

This is distinct from a **learner profile** (`learner_profiles/profile_*.md`): a profile describes a *simulated* learner (persona, latent skill, response model, learning model, schedule) used to *generate* behavior. A state file describes a *real-or-simulated* learner's *current observed state* at a point in time — exactly what a teacher reviews.


## Why a separate file
The app currently has **no persisted, reloadable learner state**: fluency is recomputed on every page load from imported session JSON (in-memory SQLite → `prepareFluencyDatasets`). This spec defines the missing artifact — a portable state snapshot — so state can be saved, reviewed, diffed over time, and used to prime the adaptive selector without re-importing every historical session.


## File format
A JSON object. Top-level fields:
- `version` — `"2.0"`, matching the app's `downloadFluencyData` export so the shapes interoperate.
- `schema` — `"math-quiz/fluency-state"`; disambiguates this state file from other v2.0 payloads.
- `user` — `{ "name": "<display name>" }`, matching the session-JSON user shape.
- `profile_id` — optional; the source profile slug when the state was generated from one.
- `source` — how the state was produced (e.g. `"baseline-snapshot"`, `"exported"`, `"hand-authored"`).
- `generated_at` — date/time the snapshot was made.
- `seed` — optional; the RNG seed when the state was generated deterministically.
- `thresholds` — the fluency thresholds in force when statuses were computed (`windowSize`, `minAccuracy`, `greenMs`, `redMs`, `retentionSessions`, `permanentSessions`).
- `addition`, `subtraction`, `multiplication` — one object per operation, keyed by canonical fact key, each value a **fact-state entry** (below). An operation not in the learner's scope is an empty object `{}`.

A **fact-state entry** mirrors the app's per-fact "combined" record:
- `key` — canonical fact key `op|min|max` (commutative `+`,`*`) or `-|num1|num2` with `num1 ≥ num2`.
- `operation`, `num1`, `num2` — the canonical fact.
- `status` — displayed status (after any manual override): `green`|`yellow`|`red`|`gray`|`blue`|`nodata`.
- `calculatedStatus` — status from the data alone, before overrides.
- `accuracy` — fraction correct over the considered window (`0`–`1`).
- `medianMs` — median correct-response time, or `null` when no correct attempts.
- `attemptCount` — total attempts recorded for the fact.
- `attemptsConsidered` — attempts inside the evaluation window (≤ `windowSize`).
- `correctCount` — correct attempts within the window.
- `statusHistory` — per-session status list (oldest→newest); drives the `blue`/permanent check.
- `isPermanent` — `true` once `green` for `permanentSessions` consecutive sessions.
- `needsRecheck` — `true` when the fact hasn't been practiced within `retentionSessions`.
- `manualOverride` — `true` when a human set `status` manually (with `overrideReason`/`overrideTimestamp`).

Every field is consistent with `math_fluency.js`: `status` is whatever `evaluateFluencyStatus()` returns for the entry's `accuracy`/`medianMs` under the file's `thresholds`.


## Example files (starting versions)
One baseline snapshot per profile — the learner's observed state at the moment they begin using the adaptive system, after a short diagnostic. Generated deterministically (seed `<profile_id>-baseline`) by sampling `windowSize` baseline attempts per in-scope fact from the profile's latent skill, then scoring them with the **real** `evaluateFluencyStatus()`:
- `addition-beginner_start.json` — addition only; mostly `gray`/`red`/`yellow` with a few `green` trivials (`+0`/`+1`). Subtraction/multiplication empty (out of scope).
- `mixed-with-holes_start.json` — `+`/`−`/`×`; mostly `green`, with the ×6–9 (and a few subtraction) facts surfacing as `gray`/`red` holes.
- `proficient-adult_start.json` — `+`/`−`/`×`; all `green` (fast and correct), no `blue` yet (permanence needs 5 consecutive green sessions).

No starting snapshot contains `blue`: permanence requires a multi-session history, which a baseline doesn't have.


## Regenerating
From `apps/math-quiz/`:
```
node simulation/generate_start_state.mjs
```
Writes the three `*_start.json` files here. Generation is deterministic, so re-running produces byte-identical files (`generated_at` is pinned, not wall-clock). The profile objects live in `simulation/profiles.mjs` (single source of truth, shared with the harness and tests).
