file: apps/math-quiz/docs/2026-06-24_targeted-practice-sqlite-schema-proposal.md
title: Targeted Practice SQLite Schema Proposal
last-updated: 2026-06-24_0605
ai: Cursor - GPT-5.5
session:


## Goal
Targeted practice should be analyzable from SQLite without relying on transient session JSON. The database needs to store:
- the per-learner setup config that prefills the anchor page;
- the exact target/filler state for each saved targeted session;
- the final state at exit, whether the session ended because all targets graduated or because Quit & save stored a partial run;
- enough per-attempt role data to distinguish target attempts from filler attempts.


## Current gap
`TargetedConfig` already stores the latest per-learner setup (`targets_json`, `filler_json`, `graduation_streak`, `fast_ms`, `percent_target`). During a targeted run, `anchor.js` also writes `settings.targeted_practice_metadata` into session JSON.
The SQLite importer (`importSessionData`) historically dropped the settings object, so saved `.sqlite` files only retained generic `Sessions`, `ProblemAttempts`, and `ModeEvents`. That means old targeted sessions can be identified, but their targets and final graduation state must be inferred from the latest `TargetedConfig` plus the observed attempts.


## Proposed schema
Keep existing generic tables unchanged and add three targeted-specific tables:
- `TargetedPracticeSessions` — one row per targeted session. Stores `outcome` (`targeted-complete`, `targeted-partial`, etc.), `complete`, `completion_reason`, target counts, current target at exit, config params, target/graduated JSON, full metadata JSON, and `inferred` / `inference_notes`.
- `TargetedPracticeTargets` — one row per target per session. Stores target order, canonical key, display text, operands/operator, graduated flag, fast-correct count, attempt count, required fast-correct count, final ring/streak count, and `inferred`.
- `TargetedPracticeAttemptRoles` — one row per problem attempt in a targeted session. Stores attempt order, problem id/text/key, `role` (`target` or `filler`), exact `target_key` when applicable, `current_target_key`, target order, fast-correct flag, and `inferred`.

`TargetedConfig` remains the latest editable setup config. The new tables are immutable session history.


## Capture behavior
Future anchor targeted sessions should persist exactly:
- `anchor.js` attaches `targeted_practice` metadata to each problem row before it is saved: role, target key, current target key, target order, and fast-correct flag.
- `targetedRun.metadata()` captures final session state: all targets, active/current target at exit, graduated targets, per-target attempts/fast-correct/final streak, config params, and completion reason.
- `importSessionData()` writes that metadata into the new SQLite tables during both per-run file creation and append into the cumulative per-user file.


## Historical backfill policy
For Kid1's existing real targeted session (`2026-06-23_134134-942d7a2c809c28`, 106 problems), exact per-session metadata was not retained. Backfill it once with `inferred=1`:
- recover the target list from the **observed serial pattern**, not from `TargetedConfig`: the config row was edited down to `6+3, 6+8, 4+9` at `21:45` — hours *after* the `13:41` run — so it is not a reliable record of that session's targets. The actual run drilled **five** targets in order (`6+3, 6+8, 4+9, 3+7, 3+4`): facts absent from the filler list that recur in tight clusters are targets; the next one starts when the prior reaches its fast-correct count;
- take config params (graduate-after 4; fast-ms 2000; percent-target 30) from the nearest `TargetedConfig`;
- infer target vs filler attempts by canonical target keys, including both orientations;
- infer per-target fast-correct counts from correct target attempts under the fast-ms threshold;
- infer `complete=1` / `completion_reason=all-graduated` only if every target reaches the required fast-correct count; otherwise mark partial and record the still-active target.

Caveat: the session predates the cumulative-rings change, so reconstructing graduation with current rules is approximate (e.g. a target may show more fast-correct than the threshold because the live run kept presenting it). This keeps historical analysis working while preserving that the reconstructed data is not exact runtime capture — every backfilled row carries `inferred=1`.
