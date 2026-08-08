file: apps/transcription/stellar-transcriber/docs/2026-07-16_review-ledger-implementation-plan.md
title: Transcript review ledger implementation plan
last-updated: 2026-07-16_1803
ai: Cursor - GPT-5.6 Sol
session: `Stellar Transcriber — bulk review ledger`

# Transcript Review Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn alignment differences into reusable single and dual review case lists so manual diff review can be done in bulk and checked for regressions.

**Architecture:** A small `core/review_ledger.py` module reuses transcript parsing, alignment tags, and dual decision chunks. A CLI writes machine-readable JSON plus an easy-to-scan Markdown report. Stable case IDs preserve manual status, corrected category, and notes across regeneration.

**Tech Stack:** Python standard library, existing `core.transcript_eval`, existing `core.denovo`, pytest.

---


## Task 1: Single `_draftds` ledger
- [x] Write failing fixture tests for raw/draft/reference cases.
- [x] Align raw and draft independently against the reference.
- [x] Emit remaining, fixed, made-worse, missing, spurious, boundary, and speaker cases.
- [x] Assign stable case and region IDs.
- [x] Add conservative category suggestions.


## Task 2: Dual ledger
- [x] Write failing tests for exact A/B source-choice detection.
- [x] Build the same decision chunks used by dual processing.
- [x] Record source A, source B, selected dual text, reference text, and selected source.
- [x] Mark unresolved output that is not an exact A/B source choice.


## Task 3: Output and review preservation
- [x] Write JSON and Markdown renderers.
- [x] Preserve `review_status`, `review_category`, and `review_notes` by stable case ID.
- [x] Add Markdown category counts and case sections.
- [x] Add `build_review_ledger.py` with `single` and `dual` subcommands.


## Task 4: Validation
- [x] Run fixture and review-ledger tests.
- [x] Run all Stellar denovo tests.
- [x] Generate March EPC single and dual sample ledgers.
- [x] Check category counts against alignment metrics and inspect sample cases manually.
