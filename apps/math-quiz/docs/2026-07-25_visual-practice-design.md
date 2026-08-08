file: 2026-07-25_visual-practice-design.md
title: Visual Practice — strategy-supported retrieval sessions (ten-frames)
last-updated: 2026-07-26_1117
ai: Cursor - Grok 4.5
session: `dragon fluency sync visual practice`


## Why
Kid1 (Kid1) is in the zone between counting-based accuracy and instant recall: mostly correct on 0–10 addition, with a handful of sticky facts (she passed on 8+3 in Reflex). The education literature's consensus for that zone is not "flash the card until memorized" and not "drill faster": it is **strategy-supported, spaced retrieval practice** — teach an efficient structure for the fact (make-ten, doubles, count-on-from-larger), make the structure visible with a representation (ten-frames), fade the visual quickly, then strengthen access with retrieval attempts spaced behind known facts and across days. Key sources: IES practice guides (Fuchs 2021, Gersten 2009 — concrete→visual→abstract progression, small individualized sets, short timed activities only after understanding), Tournaki 2003 (strategy instruction beats pure drill, especially for strugglers), Schutte 2015 (distributed beats massed practice), Hopkins & de Villiers 2016 (ten-frame subitizing intervention improving retrieval). The physical model is the Math for Love "Addition by Heart" deck 2 (double ten-frames, one color per addend).

Design implications implemented here:
- The visual is a **rescue, not a permanent prompt**: equation first, quiet retrieval window, visual only on pass/wrong/hesitation, then hidden and immediately retrieved cold.
- **Trial roles matter**: a fast answer right after seeing the visual is weak evidence; a fast answer after fillers (or days) is strong. Every attempt records its role.
- **A pass is data**, distinct from a wrong answer.
- These supported sessions used to be treated as **assessment-contaminated** and excluded from fluency; as of 2026-07-26 they **count toward fluency** everywhere (analysis, anchor, feast, quick-practice, dragon) so progress stays synchronized. Flagged lightbulb-help attempts outside Visual practice still drop via `excludeFlagged`.
- No visible countdown during instruction; response times are recorded silently.


## What it is
A third session kind on the anchor page, alongside assess and targeted practice: **Visual practice** (kid label: "Targeted ten frames"). 1–5 target facts worked serially with a secure-fact filler pool, driven by a DOM-free engine.

Per-target state machine (engine/visual_practice.mjs):
1. **Cold probe** — equation only. Fast+correct → the target needs only one **delayed confirmation** (after fillers) to clear. Slow-correct, wrong, or Pass → teach.
2. **Teach** — the visual replaces the problem/answer area: two stacked ten-frames (one per addend, big numeral under each, `+` between the rows) in constant high-contrast colors (cyan `#00acc1` / goldenrod `#daa520`, one per addend so doubles still read as two groups). After ~2 s the make-ten result appears below a divider (frame filled to 10 + remainder, `= sum`) — no captions, no tap-through; the parent narrates. One "Got it" button closes it.
3. **Spaced retrieval only** — after a teach the same fact is **not** re-asked immediately (the answer was just shown, so that datum would be invalid); fillers come first and the target returns later as a `delayed-retrieval`, alternating orientation. A target **clears** after `retrievalsToClear` cumulative fast-correct equation-only answers (successes cumulative, never lost — same philosophy as targeted rings). A failed retrieval re-opens the teach. (The `immediate-retrieval` role remains in the schema for early sessions but is no longer emitted.)
4. Session ends **immediately when the last target clears** (a trailing "end on a known fact" filler was tried and removed 2026-07-25 — in live use it read as the session refusing to stop). The final clear plays a **distinct completion animation** (`completionImage`, falling back to `pipa_no_wand_clap_jump_fixed.webp`) vs the per-target reward. Quit & save stores a partial session. Practice-bar note: the visual-mode `fastMs` defaults to 3000 (not the 2000 assessment bar) — two-digit iPad answers at ~2.5 s are real retrievals, and 2000 made correct answers earn no clearing credit (observed in Kid1's first live session: 51 problems for 3 targets).

During target trials a persistent **💡 lightbulb** button is available (never on fillers, no timer). Tapping it records a **pass** attempt and opens the teach — one control covering both "I don't know" and "show me". Wrong answers go straight to the teach (immediate explanatory help) instead of the plain correction panel.

Between-session spacing (later that day / next day / +3 days) stays a human-schedule concern for now: the parent reruns the mode; the recorded roles + dates make retention analyzable later.

**Generalized (2026-07-26):** The same ten-frame teach visual is now available on every teachable addition problem across assess, problem-list, quick-quiz, fluency-feast, targeted, and visual-practice flows. Trigger rules live only in `engine/teach_policy.mjs`; outside Visual practice, a learner-initiated lightbulb is recorded as a flagged `lightbulb` pass so fluency feeds ignore it while preserving review history. Dedicated Visual practice keeps its session engine behavior and role recording.


## Data model
- `Sessions.session_type` TEXT column (best-effort ALTER migration in `createTables`, same pattern as `flags_json`). Values written going forward: `assess`, `problem-list`, `targeted-practice`, `visual-practice`; legacy rows stay NULL. `importSessionData` populates it from `settings.session_type` (new explicit field), falling back to the preset (`anchor-targeted` → `targeted-practice`, etc.).
- New tables (mirroring the TargetedPractice trio, created in `createTables`):
  - `VisualPracticeSessions` — one row per visual session: outcome, complete, target/cleared counts, config params (fast_ms, retrievals_to_clear, hesitation_ms, filler gap), targets/cleared/metadata JSON.
  - `VisualPracticeTargets` — one row per target per session: order, key, cold-probe result, teach count, retrieval successes, cleared flag.
  - `VisualPracticeAttemptRoles` — one row per attempt: `trial_role` (`cold-probe` | `immediate-retrieval` | `delayed-retrieval` | `filler`), `target_key`, `visual_shown` (0/1), `passed` (0/1).
- `VisualPracticeConfig` (per-user setup, `tools/visual_store.py`, mirroring `TargetedConfig`): targets_json, filler_json, fast_ms, retrievals_to_clear, hesitation_ms.
- Session JSON: `settings.session_type`, `settings.preset = 'anchor-visual'`, `settings.note = 'mode:visual-practice;outcome:…'`, `settings.visual_practice_metadata`, and per-problem `visual_practice` sub-object (role, target key, visual_shown, passed).

### Fluency inclusion
Attempts from `session_type = 'visual-practice'` sessions count wherever fluency is computed or practice sets are generated: `anchor.js anchorAttemptsForFluency` (end-of-quiz %, feast, list generator), `math_fluency.js` datasets, `math_analysis.js` fluency classification, `tools/quick_practice_store.py`, and the dragon game. `sessionTypeExclusionSql` is a no-op kept for call-site compatibility. (Analysis-page session-type filter remains a follow-up.)


## UI
- Setup card: new problem source **Visual practice** (`__visual__`) with its own config box — up to 5 target fields (default 3 for a session, per the literature), secure-fact filler editor, fast-ms / retrievals-to-clear params, all auto-saved to `/api/visual-config` (debounced, same as targeted). (`hesitation_ms` remains in the store for compat but is unused — the lightbulb is always available.)
- Kid modal: **Targeted ten frames** button — one tap runs the saved config (falls back to per-learner code defaults). Kid1 defaults: targets `8+3, 4+9, 6+8` (the research-recommended starter set: the passed fact + a variable make-ten fact + a hardest-six fact), filler = her secure facts.
- Quiz card: rings graphic reused to show retrieval successes toward clearing; teach panel renders the ten-frame SVG with tap-through captions and a final "Hide it — your turn" button; Pass button during target trials.
- Summary: per-target line — cold-probe result, teaches used, retrieval successes; save path identical to targeted (per-user store + per-run .sqlite + dev-server filing + visualConfig persistence).


## Follow-ups (not in v1)
- Fact-family visual mapping (doubles arrays, near-doubles ±1, compensation for 9+) — v1 uses ten-frames for all addition facts, larger addend first.
- Cross-day scheduling/state per fact (learning states: unassessed → supported → emerging → fluent → maintenance) driven from the recorded trial roles.
- Analysis-page session-type filter and a retention view (cold-probe history per target across days).
- Latency normalization (retrieval-to-first-keypress vs entry time; learner-relative thresholds).
