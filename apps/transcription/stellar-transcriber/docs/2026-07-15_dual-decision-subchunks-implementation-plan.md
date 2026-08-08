file: apps/transcription/stellar-transcriber/docs/2026-07-15_dual-decision-subchunks-implementation-plan.md
title: Dual decision-subchunk implementation plan
last-updated: 2026-07-15_2143
ai: Cursor - GPT-5.6 Sol
session: `Stellar Transcriber — localized dual source selection`

# Dual Decision-Subchunk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let dual v4 select the locally better source inside oversized structural-disagreement chunks without generating text or creating unsafe seams.

**Architecture:** Preserve existing top-level word-anchored chunks. Oversized `diff` chunks are subdivided only at relaxed internal anchors where both sources already start a segment. Each decision subchunk is reclassified and independently passed through or selected as A/B verbatim; chunks with no safe internal cut remain unchanged.

**Tech Stack:** Python, `difflib.SequenceMatcher`, structured OpenAI/Anthropic source selection, pytest.

---


## Files
- Modify `core/denovo.py`: build safe decision subchunks and use them in preview, extraction, cost estimation, and merge.
- Modify `apps/transcription/stellar-transcriber/config/denovo-pipeline.json`: add internal anchor and oversized-decision thresholds.
- Modify `apps/transcription/stellar-transcriber/scripts/explore_dual_prompts.py`: retain parent/subchunk IDs in evaluation output.
- Modify `tests/test_stellar_denovo.py`: add subdivision, coverage, mixed-selection, fallback, and no-op regressions.


## Task 1: Safe subdivision
- [x] Write a failing small-chunk no-op test.
- [x] Write a failing oversized-chunk test that expects relaxed dual-segment-start cuts.
- [x] Assert subchunks monotonically and exactly tile both parent source slices.
- [x] Implement subdivision using `build_dual_chunks` with internal minimum match 3 and edge 1.
- [x] Keep the parent unchanged when no safe dual-segment-start cut exists.


## Task 2: Local selection integration
- [x] Write a failing merge test where source A is selected for one subchunk and B for another.
- [x] Assert output equals the exact concatenation of selected source segment dictionaries.
- [x] Write a failing per-subchunk fallback test.
- [x] Wire flattened decision subchunks into `merge_dual_llm`.
- [x] Preserve base-B pass-through for match and wording subchunks.


## Task 3: Tooling consistency
- [x] Use decision subchunks in preview and cost estimation.
- [x] Emit parent chunk and decision-subchunk IDs from extraction.
- [x] Include IDs in prompt-exploration result rows.
- [x] Confirm no behavior change for non-diff and small diff chunks.


## Task 4: Verification
- [x] Run all `tests/test_stellar_denovo.py` tests.
- [x] Check lint diagnostics and `git diff --check`.
- [x] Rebuild the current EPC decision chunks without API calls.
- [x] Confirm former chunk 46 becomes three exact, monotonic decision units and isolates the Kristi/Chris/Jerry exchange.
- [x] Run a small chunk-level selector evaluation before any full transcript rerun.
