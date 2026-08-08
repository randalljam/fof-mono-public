file: apps/deutsch/content-redo/openspec/changes/archive/2026-07-12-initial-build/tasks.md
title: Tasks - Initial Build Content Redo
last-updated: 2026-07-12_0627
ai: Codex GPT-5.5 via Claude Code (Fable 5, local)
session: Build content tools #3/#4/#5

# Tasks
- [x] Read use-cases.md §4, the shared dgraph services, the content-tools harness, deutsch-interject conventions, and existing tests.
- [x] Build `apps/deutsch/content-redo/` with CLI, config, engine, renderer, and hand-authored web UI.
- [x] Implement degree-gated plan filtering, citation filtering, no-position honesty, and marked additions.
- [x] Implement constrained batched rewrites, unchanged-turn passthrough, one retry for length-guard failures, and skipped notes.
- [x] Add README and OpenSpec files with provenance, copyright posture, trade-offs, TODOs, rules, and tests.
- [x] Add pytest coverage for engine flow, degree filtering, additions, unchanged text, length guard, child reading prompts, provenance, request handling, and sidecar completeness.
