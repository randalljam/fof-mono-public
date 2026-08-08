file: apps/deutsch/deutsch-interject/openspec/changes/archive/2026-07-12-initial-build/tasks.md
title: Tasks — Initial Build Deutsch Interjector
last-updated: 2026-07-12_0610
ai: Codex GPT-5.5 via Claude Code (Fable 5, local)
session: Build content tools #3/#4/#5

# Tasks
- [x] Read use-cases.md §3, the shared dgraph services, worldview-mirror conventions, and existing tests.
- [x] Build `apps/deutsch/content-tools/` with `ctools.config`, `ctools.runs`, `ctools.server`, `run_tools.py`, landing page, and original sample transcript.
- [x] Build `apps/deutsch/deutsch-interject/` with CLI, config, engine, renderer, and hand-authored web UI.
- [x] Implement quote/paraphrase/voice fidelity modes with quote-mode verification and citation filtering.
- [x] Ensure no-position claims are never interjected and are listed in the sidecar.
- [x] Add README files for the shared harness and app with quickstart, layout, trade-offs, TODOs, rules, and tests.
- [x] Author the baseline OpenSpec config/spec and archive proposal/tasks.
- [x] Add pytest coverage for engine flow, quote verification, citation filtering, no-position handling, include-agreements, run storage, and the shared server.
