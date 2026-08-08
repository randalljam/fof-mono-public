file: apps/math-quiz/docs/2026-06-28_fluency-in-analysis-page.md
title: Fluency rating on the analysis page
last-updated: 2026-06-28_1430
ai: Cursor - Composer 2.5 Fast
session: Fluency in analysis page Q&A

How fluency ratings work on `math_analysis.html` when **Cell metric → Fluency rating** is selected. Fluency is **not stored** in the SQLite file; it is recomputed on every render from raw `ProblemAttempts`.


## Stored in SQLite?

**No.** The database holds only raw attempts — problem text, correctness, response time, flags, timestamps, and session metadata. There is no fluency table and no status columns.

Example: `math-flu_K1_2026-06-17.sqlite` has the usual tables (`Users`, `Sessions`, `ProblemAttempts`, etc.) and raw attempt rows, but nothing like `FluencySnapshots` or per-fact status fields.

Implementation references:
- Rubric: `fluency_core.js` → `evaluateFluencyStatus`
- Analysis wiring: `math_analysis.js` → `computeFluencyByCellKey`


## What goes into the fluency rating

### Step 1 — Which attempts are in scope?

Fluency is computed from **all attempts matching the current filters**, not from the sequence stepper window:

- Selected **user**
- **Session** filter (all sessions, last session, last N, or one specific session)
- **Operation** filter (+, −, ×, etc.)
- **Flag** filter
- **Category** checkboxes (Add 0, Doubles, etc.)
- **Number range** (0–9 grid bounds)

The **sequence stepper** (start/end slider) only limits what you see in **response time** mode. Fluency always uses the full filtered population (`seqState.population`), so narrowing the stepper does **not** change fluency ratings.


### Step 2 — Group by exact fact

Attempts are grouped by exact fact key: `num1|operation|num2` (e.g. `5|+|3`). Commutative pairs are **not** merged — `3+5` and `5+3` are separate cells.

Within each group, attempts are sorted by session `start_time` (oldest → newest).


### Step 3 — Rolling window: the n most recent attempts

From that sorted list, the rubric takes the **last n attempts** (`windowSize`, default 5, adjustable 1–6 on the analysis page). If a fact has fewer than n attempts total, it uses however many exist (e.g. 2 attempts → window of 2).


### Step 4 — Evaluate status from those attempts

| Parameter | Default | Adjustable on analysis page? |
|-----------|---------|------------------------------|
| **Window size** | 5 most recent attempts | **Yes** — "Rolling window" slider (1–6) |
| **Min accuracy** | 80% correct in the window | **Yes** — "Min accuracy (%)" number input |
| **Green threshold** (`greenMs`) | 2000 ms | **Yes** — "Fluency threshold" slider |
| **Red threshold** (`redMs`) | 4000 ms | **Yes** — "Red threshold" slider (independent of green) |

Algorithm:

1. **Accuracy** = correct attempts ÷ attempts in window (e.g. 4/5 = 80%)
2. If accuracy **< 80%** or **zero correct** → **gray** ("Missing" — doesn't know it yet)
3. Otherwise, take **response times of correct attempts only** (wrong answers count toward accuracy but are excluded from the speed calculation)
4. Compute the **median** of those correct response times
5. Compare median to thresholds:
   - median **< greenMs** → **green** (Fluent)
   - median **< redMs** → **yellow** (Almost Fluent)
   - median **≥ redMs** → **red** (Needs Practice)
6. No attempts for that fact in scope → **nodata** (empty/light gray cell)


## Why duplicate handling doesn't affect fluency (but response time does)

- **Response time mode** aggregates multiple attempts **per cell in the visible window** using duplicate handling (average, first, last, min, max).
- **Fluency mode** treats **each attempt as its own row** in the rolling window of 5. Duplicate handling is never applied to fluency.

Example: if `7+8` was attempted 3 times in the filtered data, all 3 count toward the "last 5" window individually. Response time mode might show their average; fluency mode evaluates speed from the median of the **correct** ones in that window.


## Blue ("Permanent") on the analysis page

The analysis page color scale includes blue, but `computeFluencyByCellKey` only calls `evaluateFluencyStatus` — it does **not** run the cross-session "permanent" upgrade.

**Blue** requires green status in **N consecutive sessions** (default 5), computed on the dedicated **Fluency Tracker** page (`math_fluency.html` via `prepareFluencyDatasets` + `checkPermanentStatus`). On `math_analysis.html` you'll typically see gray / red / yellow / green / nodata, not blue.


## Quick reference

| Question | Answer |
|----------|--------|
| Stored in SQLite? | **No** — only raw attempts |
| Which attempts? | All matching filters, grouped per fact, **5 most recent** per fact |
| Speed metric | **Median** of correct-attempt response times |
| Accuracy gate | **≥ 80%** correct in the window, or gray |
| Thresholds | Green, red, rolling window, and min accuracy are all adjustable on the page |
| Affected by duplicate handling? | **No** |
| Affected by sequence stepper? | **No** (only response-time view is) |

Hover a cell in fluency mode to see the breakdown: status label, median ms, accuracy %, and total attempt count for that fact in the current filter scope.
