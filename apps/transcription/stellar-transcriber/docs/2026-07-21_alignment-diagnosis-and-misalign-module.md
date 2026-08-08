file: apps/transcription/stellar-transcriber/docs/2026-07-21_alignment-diagnosis-and-misalign-module.md
title: Alignment diagnosis + misalignment-extraction module plan
last-updated: 2026-07-21_1827
ai: Claude Code (Fable 5, orchestrating Codex gpt-5.5)
session: `fable5-w-codex — stellar transcriber alignment`

Diagnosis of why deterministic alignment repair (`_draftds`) is not reaching high-90s strict scores, an assessment of the new strict metric, and the design for a new misalignment-extraction + LLM-classifier module that isolates the misaligned windows so we can develop de-novo repair prompts/code against them.


## 1. Is the new strict metric right?
Yes, with two caveats. Strict alignment is the correct progress needle for boundary repair:
```
seg_error_count_strict = missing + spurious + boundary_misplaced   # excludes ASR edge-word "boundary" noise
subscore_alignment_strict = 100 * (1 - strict / total_ref_segments)   # clamped 0..100
```
The essential move — separating **misplaced text** (a cut-move can fix it) from **ASR edge-word differences** (`head on` vs `headon`, which no re-segmentation fixes) — is exactly what a segmentation tool needs. `compute_subscore_alignment_loose` preserves the old metric; `compute_subscore_alignment_strict` is the new one; `compute_composite_scores` rolls up strict with a one-line revert. Implementation is sound.

- **Caveat A — the missing/spurious half of strict is fragile.** `is_boundary_misplaced` is well isolated (2-word phrase probe across the transition), but `seg_missing_count` / `seg_spurious_count` come from the 3-pass matcher. A single mis-anchored segment cascades into a *block* of false missing + false spurious (the real-five run saw up to 40 missing / 45 spurious on Sagenhaft and Alex O'Connor). So the strict *count* can overstate the number of independent defects. This is the core reason to look at misaligned **windows**, not raw counts.
- **Caveat B — `is_boundary_misplaced` is a 2-word probe** over 12-word tails/heads. It will miss subtle single-word bleeds and can occasionally false-positive on repeated phrases. Good primary needle; not a ground-truth oracle.


## 2. Why `_draftds` isn't hitting the 90s
The strict mean sits at ~73–78 because the residual is **two different problems**, and only one of them is what boundary repair targets. Per-episode strict (today's rerun, `_draftds`):

| Episode | nova2 strict | whisperM strict | Character |
|---------|-------------:|----------------:|-----------|
| Ep6 Feelings Ideas | 78.9 | 83.7 | near target |
| Ep5 Decision Making | 81.2 | 86.8 | near target |
| Arjun Khemani | 89.3 | 92.9 | at target |
| Sagenhaft | 71.7 | 64.6 | structural drag |
| Alex O'Connor | 63.3 | 62.1 | structural drag |

- **The good three (Arjun, Ep5, Ep6)** are already 79–93 strict — the deterministic path basically works there.
- **Sagenhaft and Alex** carry large **missing/spurious structural blocks**: the human reference segmented the conversation on a *different philosophy* than the raw diarizer (merge/split-scale divergence). Boundary repair cannot touch these, and merge/split is currently forbidden to both the deterministic and LLM paths (word-conservation guard). This matches `references/alignment-results-real5.md` finding #3.

So the ~20–35 strict-point gap on the worst episodes is **not** "the deterministic code is weak." It is a mix of: (a) a genuinely-repairable pile of boundary-misplaced / blip / cutoff cases, and (b) a structural pile that is partly real merge/split defects, partly **matcher cascade artifacts**, and partly **reference-vs-raw segmentation-style differences that are not defects at all**. Nobody has separated these three, which is why the "why" has been unclear.


## 3. Assessment of "dual LLM should get there easily"
Partly right. Isolating the misaligned subset and hitting it with a cheap LLM is the correct next step and *will* be fast (small subset, cheap model). But it will not "easily" reach high-90s until the structural blocks are resolved — and some of those are not fixable and not even real. The honest path to 90s is: **classify the misaligned windows first, quantify the repairable vs. structural vs. artifact mix, then repair the repairable ones.** Build the classifier to *tell us the mix*, not to assume the mix is all fixable.


## 4. What is being built
Two deliverables (implemented via Codex gpt-5.5, reviewed by the orchestrator):

### (A) `core/transcript_misalign.py` — misalignment extraction
Reuses `evaluate_step_segments_align`'s per-segment flags to isolate contiguous misaligned regions, using aligned segments as fixed anchors. Each **window** pairs the candidate (eval) section with the corresponding reference section and its flanking anchor context, plus an error signature and a deterministic `window_kind_hint` (`boundary_only` / `spurious_block` / `missing_block` / `mixed_structural`). Invariant: windows partition the strict errors — sum of per-window spurious/misplaced/missing equals the corpus metric counts. This is the data structure the user asked for: aligned segments as anchors, misaligned sections isolated and chunked small.

### (B) LLM classifier over the windows (gpt-5-mini)
Each window → a structured classification labeling *what is wrong*: taxonomy drawn from EA's vocabulary + structural categories (`boundary_bleed_start/end`, `blip_merge`, `cutoff_ellipsis`, `missing_turn`, `spurious_turn`, `split_needed`, `structural_divergence`, `matcher_artifact`, `asr_edge_word`), each with `repairable` (bool), `confidence`, `rationale`, `suggested_fix`. Output feeds de-novo repair prompt/code development. Uses the existing `openai_function_call_with_usage` + `parse_function_call_response` + `TokenUsageAccumulator` pattern (mirrors `llm_arbitrate_dual_chunk`).

### (C) Run/version + results ledger
Append-only log (JSONL source of truth + rendered markdown summary in `references/`) recording, per run: mode (`_draftds`/`_draftls`/`_draftld`), `DENOVO_PIPELINE_VERSION`, `EVAL_CODE_VERSION`, prompt/config ids, corpus/profile, per-episode strict/loose + missing/spurious/misplaced, classifier label distribution, and output paths. This is what lets us track Stellar Transcriber performance across versions.


## 5. First live-classifier results (raw ASR baseline, 2026-07-21) — corrects §2/§3
First live gpt-5-mini classification run over all 10 Deutsch pairs (raw `_nova2gen`/`_dgwhspm` vs `_vrb`), 129 misalignment windows, $0.27, logged to `references/stellar-run-log.jsonl`. This **partially reverses the structural-pessimism in §2/§3**: the residual is not mostly incompatible merge/split divergence.

Label distribution (129 windows): `missing_turn` 48, `spurious_turn` 43, `boundary_bleed_start/end` 29, `structural_divergence` **only 3**, `blip_merge` 2, `split_needed` 2, other/artifact/asr-edge 3. gpt-5-mini called 88% "repairable", but that figure is optimistic — see the missing-turn caveat below.

**The decisive finding — the two ASR arms fail in opposite, complementary ways:**
- `missing_turn`: whisper **32** vs nova2 **16** — Whisper Medium drops whole short turns.
- `spurious_turn`: nova2 **35** vs whisper **8** — Nova2 invents blip/short spurious splits.

This is the strongest empirical case yet **for the dual approach**: where one arm drops a turn, the other almost certainly has it; where one over-segments, the other is clean. Missing turns cannot be fixed by single-transcript segmentation (the words aren't in the candidate), so they are precisely what a dual merge — or audio re-transcription — is *for*. Spurious blips and boundary bleed are single-path-repairable and are exactly EA's denovo targets.

**Honest re-read of the mix (adjusting for classifier optimism on `missing_turn`):**
- ~**54%** genuinely single-transcript segmentation-repairable: `spurious_turn`/blip deletion (39) + `boundary_bleed` (27) + `split_needed`/`blip_merge` (4). The deterministic + single-LLM paths should close these.
- ~**37%** `missing_turn`: needs the **other ASR arm (dual)** or audio — not single-path repairable despite the classifier's label.
- ~**9%** genuinely stuck / structural / artifact (the 3 `structural_divergence` are multi-defect: collapsed turns + word-level ASR errors + duplication).

**Caveats.** (a) The classifier over-calls `missing_turn` as `repairable=True` (`insert_missing`) even when the words are absent from the single candidate — the prompt's "repairable" definition needs one tightening: a dropped turn is only single-path-repairable if its words exist in the candidate under a different segmentation. (b) It also usefully *overrode* the deterministic heuristic in at least one window (Arjun/nova2: `boundary_only` flag → correctly re-labeled a speaker-label mismatch, not a boundary defect), confirming the counts alone mislead. (c) This baseline is on **raw ASR**, not `_draftds` — re-running with `--candidate-folder` pointed at the denovo `_draftds` outputs will show what deterministic repair already closed and what remains; that is the natural next measurement.

**Implication for the 90s goal.** Reaching high-90s strict is plausible but requires two tracks, not one: (1) finish single-path repair of spurious/blip/bleed (deterministic + `_draftls`), and (2) revive the dual path specifically to recover `missing_turn` from the complementary arm. The ~9% structural residual is the realistic ceiling for automated repair without audio.


## 6. Follow-up runs (2026-07-21 evening) — draftds ceiling + dual opportunity

**`_draftds` ≈ raw on strict for the Deutsch five (current-mode measurement).** Re-scoring the deterministic `_draftds` output against `_vrb` gives strict/loose scores identical to the raw baseline on all 10 pairs. Two things confirmed this: (a) the pre-existing `data/deutsch/dev-eval/draftds_vs_raw_five_2026-07-21_161538/draftds/*` files are byte-identical to raw (a stale/empty generation); (b) a freshly generated `_draftds` (via `build_draft_transcript.py --method deterministic --profile deutsch`) changes only ~2 lines and does **not** move the strict metric (Ep6 nova2: 78.9 → 78.9, 35 strict errors either way). **Interpretation:** deterministic denovo has essentially exhausted its strict-alignment gains on this set — the residual is missing-turn + structural (per §5), not the boundary/blip patterns denovo targets. Consistent with real-five's "2–4% strict reduction" and EA's "decent on Deutsch." More denovo patterns will not move Deutsch strict; the leverage is dual + missing-turn recovery. (No ledger row was kept for this run since it duplicated the raw baseline.)

**Dual missing-turn recovery opportunity — the number that justifies reviving dual.** New `core/dual_missing_recovery.py` measures, for each arm's dropped reference turns, whether the *sibling* arm contains that content near the same timestamp (time-windowed Levenshtein + contiguous-word-run match; containment gated to ≥3-word turns so a common word buried in a long sibling segment is not a false recovery). Deutsch five, strict mode:

| Arm | Missing turns | Recoverable from sibling | Rate |
|-----|--------------:|-------------------------:|-----:|
| nova2gen | 44 | 31 | 70.5% |
| dgwhspm (whisper) | 88 | 70 | 79.5% |
| **overall** | **132** | **101** | **76.5%** |

**~3 of every 4 dropped turns are present in the other arm** — the upper bound on what a dual merge could recover without audio, and the strongest quantified case for reviving the dual path. Whisper (which drops the most turns) has ~80% of them recoverable from Nova2. Run via `scripts/run_dual_recovery.py`.

**Classifier prompt tightened (§5 caveat a).** `missing_turn` is now `repairable=false` when the words are absent from the single candidate (recovery needs dual/audio), `true` only when the words are present under a different segmentation. This corrects the earlier over-optimistic 88% repairable figure.

**What this means for the plan.** The three tracks are now quantified: (1) deterministic single-path is near its Deutsch ceiling — pursue it on harder EPC, not Deutsch; (2) dual is the lever for the ~37% missing-turn share, with a measured 76.5% recovery ceiling; (3) the ~9% structural residual is the realistic floor without audio. Next concrete step for dual: a conservation-guarded, missing-turn-targeted merge evaluated on the recovery metric above (a risky refactor of the quarantined `_draftld` path — worth a dedicated plan).


## 7. Segmentation of the work (first step of the pipeline)
This work makes **alignment/segmentation the measured first stage** of Stellar Transcriber, per the ROADMAP alignment-first emphasis. Word-error, proper-name, and speaker-ID fixes come after and must not regress the strict metric or word-conservation guard.
