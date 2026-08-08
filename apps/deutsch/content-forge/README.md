file: apps/deutsch/content-forge/README.md
title: content-forge — create graph-conditioned Deutsch-inspired content
last-updated: 2026-07-12_0625
ai: Codex GPT-5.5 via Claude Code (Fable 5, local)
session: Build content tools #3/#4/#5

Use case #5 from `apps/deutsch/deutsch-graph/docs/use-cases.md`: create new text content from a description, such as "make a lesson about optimism for high-school students", grounded in a selected deutsch-graph subgraph rather than the model's memory. v1 supports text formats only: essay, lesson, and dialogue. Audio, video, and interactive exports are placeholders.


## Quickstart
From the repo root with the venv active:
```
python apps/deutsch/content-forge/run_forge.py selftest
python apps/deutsch/content-tools/run_tools.py serve --port 8971
python apps/deutsch/content-forge/run_forge.py create "Make a short lesson about optimism and problem-solving for a thoughtful high-school student." --format lesson --length short --tone 3
```
The web UI is served through the shared harness at `http://127.0.0.1:8971/forge`.


## How a run works
1. `dforge.engine.route_description` passes the description through `dgraph.divergence.route_claims` as one claim-like item.
2. If the shared router returns fewer than four topics, Content Forge makes one wider routing call for up to eight topics, two categories, and three concept needles using exact catalog labels.
3. `dgraph.grounding.build_grounding` assembles the curated context package: top QA items, category claims/excerpts, and concept definitions.
4. One generation call receives the format template, length target, tone instruction, and SOURCE blocks. The prompt requires `##` section headings, inline graph node citations, and explicit gap statements when the selected sources do not cover part of the requested description.
5. Length is enforced softly. If the first draft is more than 1.6x the target, the engine retries once with a stronger length instruction and keeps the result with a sidecar note.
6. `dforge.engine.build_sidecar` post-processes citations without an LLM: it splits by `##` sections, validates citation ids against the graph citation index, strips unknown ids, resolves valid citations, flags ungrounded sections, and records retrieved-but-uncited context nodes.
7. `dforge.render` returns the final markdown document, a human-readable citations sidecar, and a JSON sidecar.


## Layout
```
run_forge.py             CLI: create / selftest / serve
dforge/
  config.py              paths, sys.path wiring, format/length defaults
  engine.py              route -> ground -> generate -> validate citations -> sidecar
  render.py              document markdown and citations-sidecar markdown
web/content-forge.html   hand-authored UI served by content-tools
openspec/                baseline app spec and archived initial build change
data/                    gitignored output and saved runs
```


## Provenance Posture
Every output includes a provenance header with the original description, tool, format, length, tone, model, and generated timestamp, plus this disclosure: `AI-GENERATED: This piece was generated from cited deutsch-graph sources; it was not written or endorsed by David Deutsch.` Dialogue format uses fictional named speakers and must not label a speaker as Deutsch.


## Trade-offs / Alternatives
- **Single-call generation instead of outline-then-write**: pro: lower latency, easier prompt audit, and one context package to inspect. Con: weaker global planning for long pieces; an outline pass could improve structure and citation distribution later.
- **Shared `route_claims` wrapper instead of a dedicated router**: pro: reuses catalog-label discipline and keeps routing behavior aligned with the divergence service. Con: the shared router caps topics at three, so forge needs one local widening call.
- **Graph citation-index validation instead of context-only validation**: pro: strips hallucinated ids while allowing any committed graph node id to resolve cleanly. Con: a model could cite a valid node that was not in the retrieved package; future evaluation should flag outside-package cites separately.
- **Markdown plus sidecars instead of a rich document model**: pro: easy to diff, save, review, and render in the local harness. Con: no editor workflow, no citation-aware export, and no curriculum package format yet.


## TODOs
- Add TTS output through `apps/voice/` after the text/citation loop is reliable.
- Add interactive-website export with embedded graph excerpts and citation previews.
- Add video generation only after scripted text plus cited source clips are trustworthy.
- Support multi-piece curricula with shared routing, prerequisite ordering, and per-piece sidecars.
- Build an eval rubric for section grounding, citation density, honest gaps, and outside-package citation drift.


## Rules for agents
- Do not re-implement graph loading, grounding, citation indexing, or the shared tone knob; use `dgraph.grounding`, `dgraph.divergence`, `dgraph.llm_util`, and `ctools.config`.
- Keep `core.llm` lazy through `dgraph.llm_util`; imports must work without API keys.
- Keep citation-sidecar construction pure post-processing. Do not use a second LLM to repair or explain citations.
- `data/` is gitignored local output and run storage; do not commit it.


## Tests
```
.venv/bin/python3 -m pytest tests/test_content_forge.py tests/test_dgraph_services.py -q
```
The forge tests stub every LLM call, use the committed Deutsch graph, and cover routing fallback, generation prompts, citation stripping, per-section grounding flags, length retry, provenance, `run_from_request`, and coverage stats.
