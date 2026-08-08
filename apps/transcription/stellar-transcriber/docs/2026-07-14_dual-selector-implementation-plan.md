file: apps/transcription/stellar-transcriber/docs/2026-07-14_dual-selector-implementation-plan.md
title: Dual LLM verbatim selector implementation plan
last-updated: 2026-07-14_2004
ai: Cursor - GPT-5.6 Sol
session: `Stellar Transcriber — dual selector safety`

# Dual LLM Verbatim Selector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent dual LLM arbitration from copyediting or inventing speaker splits by limiting each disputed chunk decision to choosing source A or source B unchanged.

**Architecture:** Word-anchored chunking remains unchanged. For each structural `diff` chunk, the LLM returns only a validated side choice (`a` or `b`); `core/denovo.py` copies that side's original segment dictionaries verbatim. Match and wording chunks continue to pass through from configured base side B.

Human-reviewed transcripts are evaluation-only: they score completed outputs and are never passed to the production dual merge or its LLM. Existing short-interjection splits in A or B remain eligible for contextual selection; the selector may not invent one where neither input has it.

**Tech Stack:** Python, OpenAI/Anthropic structured function calls, pytest.

---


## Files
- Modify `core/llm.py`: add the selector-only prompt, function-call schema, and side-selection helper.
- Modify `core/denovo.py`: resolve the new prompt version and copy the selected source chunk unchanged.
- Modify `apps/transcription/stellar-transcriber/config/denovo-pipeline.json`: activate the new prompt behavior as `denovo-v4`.
- Modify `apps/transcription/stellar-transcriber/scripts/explore_dual_prompts.py`: score the selected source side rather than model-generated transcript text.
- Modify `tests/test_stellar_denovo.py`: cover exact preservation, no invented boundaries, fallback, and prompt constraints.


## Task 1: Define selector-only behavior with failing tests
- [x] Add a test where the mocked LLM selects B and assert the helper returns `"b"`.
- [x] Add a test where the mocked response contains generated transcript segments instead of a valid side and assert selection fails.
- [x] Add a test proving an existing short-interjection split remains eligible for contextual A/B selection.
- [x] Add a merge test that asserts the selected source chunk is copied exactly.
- [x] Run the focused tests and confirm they fail because selector-only behavior does not exist.


## Task 2: Implement the selector-only prompt and code path
- [x] Add `PROMPT_DENOVO_DUAL_V4`, explicitly stating that the model chooses an existing segmentation and never returns transcript text.
- [x] Add a strict function schema whose only output is `{"selected_version": "a" | "b"}`.
- [x] Implement `llm_select_dual_chunk_side` with bounded retries, usage tracking, and `None` on invalid output.
- [x] Update prompt resolution for `denovo-v4`.
- [x] Update `merge_dual_llm` to call the selector and deep-copy the selected chunk; use configured base side on failure.
- [x] Run focused tests and confirm they pass.


## Task 3: Keep chunk exploration compatible
- [x] Update `explore_dual_prompts.py` to call the selector helper.
- [x] Score the chosen A/B chunk against the projected reference.
- [x] Record the selected side and mark invalid decisions as base-side fallbacks.
- [x] Run a five-chunk PV/EPC selector check against the projected reference.


## Task 4: Verify
- [x] Run `.venv/bin/python3 -m pytest tests/test_stellar_denovo.py`.
- [x] Confirm existing word-anchored chunk tests remain green.
- [x] Check lint diagnostics for edited files.
- [x] Do not run another 25–35 minute full episode until chunk-level prompt results are reviewed.
