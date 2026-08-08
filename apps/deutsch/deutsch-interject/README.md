file: apps/deutsch/deutsch-interject/README.md
title: deutsch-interject — insert grounded virtual Deutsch turns into external content
last-updated: 2026-07-12_0610
ai: Codex GPT-5.5 via Claude Code (Fable 5, local)
session: Build content tools #3/#4/#5

Use case #3 from `apps/deutsch/deutsch-graph/docs/use-cases.md`: take an external transcript or article, find claims that diverge from David Deutsch's recorded positions in the Deutsch graph, and insert clearly labeled `David Deutsch (virtual)` turns after the relevant source turns. The default `quote` fidelity mode is deliberately conservative: interjections should use framing plus verbatim quoted source spans with node-id citations, and quote verification drops or regenerates fabricated quotes.


## Quickstart
From the repo root with the venv active:
```
python apps/deutsch/deutsch-interject/run_interject.py selftest
python apps/deutsch/content-tools/run_tools.py serve --port 8971
python apps/deutsch/deutsch-interject/run_interject.py process apps/deutsch/content-tools/samples/sample-discussion.md --tone 3 --fidelity quote
```
The web UI is served through the shared harness at `http://127.0.0.1:8971/interject`.


## How a run works
1. `dgraph.claims.parse_content` turns transcript/prose into ordered source turns.
2. `dgraph.claims.segment_claims` extracts atomic third-person claims through an injectable LLM chat call.
3. `dgraph.divergence.detect` routes claims to graph topics/concepts, grounds them, and judges each as `agree`, `diverge`, or `no-position`.
4. `dinterject.engine.generate_interjections` selects `diverge` claims, plus `agree` claims when requested, and generates batched interjections of about six claims per call.
5. Quote mode verifies every double-quoted span of eight or more words against that claim's grounding text. Bad quotes are regenerated once or dropped with a sidecar note.
6. `dinterject.render` inserts virtual turns after the original turns, writes a synthetic-content disclosure, and returns a JSON sidecar with claims, verdicts, citations, skipped/no-position rows, knobs, and provenance.


## Layout
```
run_interject.py           CLI: process / selftest / serve
dinterject/
  config.py                paths, sys.path wiring, fidelity defaults
  engine.py                parse -> segment -> divergence -> interjections -> render
  render.py                annotated markdown and JSON sidecar assembly
web/deutsch-interject.html hand-authored UI served by content-tools
openspec/                 baseline app spec and archived initial build change
data/                     gitignored output and saved runs
```


## Ethics and Provenance Posture
Every output labels the inserted voice as `David Deutsch (virtual)` and includes the fixed disclosure: the virtual turns are AI-generated, not spoken or endorsed by David Deutsch; quotes are verbatim-cited where marked. The tool never interjects on `no-position` claims; those are listed explicitly in the sidecar as cases where the routed grounding does not establish a recorded Deutsch position.


## Fidelity Modes
- **quote**: defensible default. Use framing plus verbatim quotes from provided Deutsch graph grounding, each cited by node id. Mandatory quote verification runs before output.
- **paraphrase**: lightly paraphrase the provided sources while keeping citations.
- **voice**: more customized virtual-Deutsch prose, still grounded in provided sources and cited. This mode is less defensible for public use because the voice is synthetic.


## Trade-offs / Alternatives
- **Interjection instead of rewrite**: pro: preserves the source document and makes additions auditable. Con: less fluent than a full remix; use case #4 will own rewriting.
- **Graph-grounded divergence service instead of generic prompting**: pro: honest `agree/diverge/no-position` structure with citations. Con: quality depends on routing and graph coverage.
- **Quote mode default**: pro: strongest provenance and easiest review. Con: more terse and sometimes drops generated text when corpus grounding is sparse.
- **Markdown plus JSON sidecar**: pro: human-readable output and machine-readable audit trail. Con: no rich editor or diff workflow yet.


## TODOs
- Add a small eval set with hand-marked divergences on two or three external transcripts.
- Improve quote-mode fallbacks when the fetched corpus is unavailable and QA grounding only has questions/labels.
- Add optional `_vrb`-style export if downstream transcript tooling needs that grammar exactly.
- Add richer citation previews in the UI for concepts and book excerpts.


## Rules for agents
- Do not re-implement parsing, segmentation, routing, judging, or grounding here; use `dgraph.claims`, `dgraph.divergence`, `dgraph.grounding`, and `dgraph.llm_util`.
- Keep `core.llm` lazy through `dgraph.llm_util`; imports must work without API keys.
- Keep quote verification mandatory in `quote` mode.
- Do not interject on `no-position` claims.
- `data/` is gitignored local output and run storage; do not commit it.


## Tests
```
.venv/bin/python3 -m pytest tests/test_deutsch_interject.py tests/test_dgraph_services.py tests/test_worldview_mirror.py -q
```
The interject tests stub every LLM call, use the committed Deutsch graph, and cover the engine, quote verification, run storage, and shared server.
