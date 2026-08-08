file: apps/deutsch/deutsch-interject/openspec/changes/archive/2026-07-12-initial-build/proposal.md
title: Initial Build — Deutsch Interjector
last-updated: 2026-07-12_0610
ai: Codex GPT-5.5 via Claude Code (Fable 5, local)
session: Build content tools #3/#4/#5

# Initial Build — Deutsch Interjector


## Why
Use case #3 from `apps/deutsch/deutsch-graph/docs/use-cases.md` needs a defensible local prototype that can take external content, detect where it diverges from David Deutsch's recorded positions, and insert clearly labeled virtual Deutsch interjections with citations and no-position honesty.


## What Changes
- Create the shared `apps/deutsch/content-tools/` harness with tone settings, saved-run storage, sample content, a tool registry, a local FastAPI server, and a landing page.
- Create the `apps/deutsch/deutsch-interject/` app with CLI, engine package, renderer, hand-authored web UI, README, and OpenSpec baseline.
- Reuse `dgraph.claims`, `dgraph.divergence`, `dgraph.grounding`, and `dgraph.llm_util` for parsing, segmentation, routing, judging, grounding, and JSON parsing.
- Implement fidelity modes, with `quote` as the default and mandatory long-quote verification against claim grounding.
- Persist server runs to the app's gitignored `data/runs/` through the shared harness.


## Non-Goals
- No `content-redo` or `content-forge` product behavior yet; the harness only exposes registry slots for them.
- No deployment, accounts, or shared backend database.
- No changes to `dgraph` or `worldview-mirror` source.
- No claim that synthetic `voice` mode is endorsed by David Deutsch.
