file: apps/transcription/stellar-transcriber/docs/2026-07-06_milestone-4-alignment-first-plan.md
title: Stellar Transcriber — Milestone 4: alignment-first plan
last-updated: 2026-07-06_1750
ai: Claude Code (cloud)
session: `Stellar Transcriber — alignment review and rework`

Milestone 4 of the Stellar Transcriber project. Supersedes the M3B score interpretation: the M3B alignment and word-accuracy columns were computed with unit bugs (see "Why the M3B numbers were unreadable") and should not be used. Working branch: `stellar-transcriber-start`.


## Objective
Make segment alignment — correct speaker-segment boundaries vs the gold reference — measurably and reliably better than raw ASR output, before investing further in the other quality dimensions. Alignment is the dimension where raw diarized transcripts fail in characteristic ways: dialogue left in the previous speaker's segment and cut off from the start of its true segment, and speaker segments eliminated entirely.


## Why the M3B numbers were unreadable
Two unit bugs made the M3B subscores meaningless:

1. **Alignment subscore double-divided.** `evaluate_step_segments_align` stores `is_aligned == True` (and the other boolean metrics) as 0–1 fractions of eval segments, but `compute_subscore_alignment` treated them as raw counts and divided by `total_eval_segments` again. Reported "alignment" was therefore ≈ `aligned_fraction / segment_count × 100` — roughly 100× too small and inversely proportional to episode length. That is exactly why Reason Is Fun Ep5 showed 0.61–0.63 while the (shorter) Arjun Khemani episode "jumped" to 3.4–3.8: the jump measured episode segment count, not quality.
2. **Word-accuracy subscore never scaled.** `word_accuracy` is stored as a 0–1 fraction but was used as if 0–100, so it contributed ~0.3 instead of ~30 points to the composite. Overall ≈ 25–26 on every variant was just the speaker subscore (0.25 × ~100) plus noise.

Both are fixed (eval code version 0.3.0). Alignment is now scored from absolute segment-error counts (below), and historical metrics CSVs can be re-scored with `rescore_metrics_csv`.


## The alignment metric: absolute segment-error accounting
The reference has a discrete number of speaker segments; each eval transcript either represents a reference segment correctly or commits a categorizable error. Per eval/ref pair the eval now reports:

| Metric | Meaning |
|--------|---------|
| `total_ref_segments` | Discrete segment inventory of the gold reference |
| `seg_missing_count` | Reference segments eliminated entirely from the eval transcript |
| `seg_spurious_count` | Eval segments with no reference counterpart |
| `seg_boundary_error_count` | Aligned segments whose start or end words sit on the wrong side of a transition |
| `seg_error_count` | Total = missing + spurious + boundary |
| `seg_error_rate` | `seg_error_count / total_ref_segments` |

The alignment subscore is `100 × (1 − seg_error_rate)`, clamped to [0, 100].

**The headline numbers for any correction method** are the absolute error count before → after, the **percent error reduction** `(E_raw − E_draft) / E_raw × 100`, and the **residual error count** (segments remaining with errors). Word accuracy rides along as a content-damage guard: a correction method must not lower it versus its input.


## Method ladder (terminology)
Two raw diarized transcripts per episode: raw A `_nova2gen`, raw B `_dgwhspm`. Reference `_vrb` (or `_qafixed`). Rungs:

| Rung | Variant | Method |
|------|---------|--------|
| A0 | `raw_A`, `raw_B` | Baselines — establish `E_raw` per source |
| A1 | `_draftds` on each raw | Deterministic single-transcript repair (control arm) |
| A2 | `_draftls` on each raw | **Single-LLM repair — primary development target** |
| A3 | `_draftld` on raw A + raw B | Dual-LLM merge of the raws |
| A4 | `_draftld` on `draftls(A)` + `draftls(B)` | Dual-LLM merge of the single-repaired drafts (cascade) |

The stepwise development procedure:

1. **Develop A2 first.** Run the single-LLM repair on each raw independently and measure percent error reduction per raw. A single-transcript method must show solid, reproducible reduction before dual fusion adds value on top; it is also the cheaper and simpler failure surface to debug.
2. **Then run A3 and A4** and compare: does dual fusion of raws beat the better single-repaired raw? Does the cascade (A4) beat both? Each rung is judged on percent error reduction vs the best raw baseline, with word accuracy as the guard.
3. **Iterate prompts at the weakest rung** using the fixture harness (below), one prompt version per iteration (`denovo-v2`, `denovo-v3`, …), keeping the config-selected version stamped in draft metadata so runs are comparable.

Runner: `scripts/run_alignment_eval.py` (`--fixture` for the local harness; `--raw-a/--raw-b/--ref [--profile deutsch]` for real episodes). It prints and writes the full ladder table with error categories, reduction percentages, and the guard column.


## Fixture harness (ground-truth defect injection)
`scripts/make_alignment_fixture.py` injects a known defect set (boundary shifts in both directions, merges, spurious splits, wrong speaker) into a clean 30-segment reference, producing synthetic raw A and raw B with **exact expected error counts**. `tests/test_stellar_alignment_fixture.py` locks the metric to those counts (14 and 16 on the seeded raws, 0 on self-eval).

This gives a free, deterministic inner loop for metric validation and prompt iteration that does not depend on S3 corpus access, and it already exposed five real pipeline bugs (see results). Real-corpus runs remain the outer loop.


## Current fixture results (2026-07-06, gpt-5-mini, prompts denovo-v2)
| Variant | Errors | Missing | Spurious | Boundary | Reduction | Word acc |
|---------|--------|---------|----------|----------|-----------|----------|
| raw_A | 14 | 2 | 1 | 11 | — | 1.000 |
| raw_B | 16 | 2 | 2 | 12 | — | 1.000 |
| draftds_A | 8 | 2 | 0 | 6 | 42.9% | 1.000 |
| draftds_B | 14 | 3 | 1 | 10 | 12.5% | 1.000 |
| draftls_A | 4–6 | 2 | 0 | 2–4 | **57–71%** | 1.000 |
| draftls_B | 12–15 | 3 | 2–3 | 7–9 | 6–25% | 1.000 |
| draftld_raws | 10 | 3 | 1 | 6 | 28.6% | 1.000 |
| draftld_singles | 10 | 3 | 2 | 5 | 28.6% | 1.000 |

Ranges reflect LLM run-to-run variation (single fixture, n=3 runs). Standard tier (`gpt-5.4`) was not better than cheap on this fixture.

Pipeline defects found and fixed during these runs (each was invisible under the old scoring):

1. Draft outputs were written with policy normalization applied (lowercased, punctuation stripped) — destroyed drafts and starved the LLM of boundary signal.
2. LLM chunk calls echoed the read-only context segments back, duplicating dialogue at every chunk join (word accuracy 0.4 → caught by the guard).
3. The LLM silently merged segments; output timestamps are now validated (copied verbatim, 100% input coverage in single mode).
4. Deterministic same-speaker merge eliminated real reference segments; merges now require a mid-sentence continuation and run after boundary repair, and ellipsis endings count as intentional breaks.
5. Dual-merge duplicated content two ways: overlapping sub-island windows, and 0.75-similarity anchors that let disputed words live inside an anchor on one side and an island on the other (word accuracy 0.844 on every dual run). Anchors now require identical normalized dialogue.


## Real-corpus run (2026-07-06)
Done — five deutsch episodes, full ladder, results and findings in `references/alignment-results-real5.md`. Word-conservation validation was added to the single-LLM path after the first real runs showed word drift with no structural change. Cloud S3 access now works via the Cataclysm environment's `FOF_FILES_DATA_S3_*` scoped grant (`fetch_eval_pairs.py` prefers it automatically).

## Next steps (updated after the real-corpus run)
1. **Make the single-LLM pass earn its keep.** `draftls` ≈ `draftds` on real episodes — under the conservation and no-merge constraints, gpt-5-mini makes few moves. Iterate on the fixture + Arjun/RIF-Ep6 (episodes with real misplaced signal): per-transition repair calls (just the two segments around each suspect transition), chunk overlap so no transition lands on a chunk join, `denovo-v3` prompt variants.
2. **Conservation-checked merge/split repair.** Sagenhaft and Alex O'Connor's strict errors are dominated by missing/spurious blocks (merge/split-scale divergence) that boundary repair cannot touch. Allow the LLM to merge/split under the word-conservation invariant plus explicit segment-accounting validation, instead of forbidding merges outright.
3. **Redesign the dual merge before running it again.** Quarantined: on real ASR pairs word accuracy collapses (duplication) because identical-dialogue anchors are rare and positional island pairing drifts. Needs word-level A↔B alignment (e.g. anchor on matching word n-grams, not whole-segment equality) to pair content correctly.
4. **Wrong-speaker attribution** shows up in the speaker dimension, not alignment; leave until alignment is on track.
