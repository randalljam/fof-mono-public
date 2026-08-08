file: apps/deutsch/content-redo/README.md
title: content-redo - divergence-aware optimistic rewrites of existing content
last-updated: 2026-07-12_0627
ai: Codex GPT-5.5 via Claude Code (Fable 5, local)
session: Build content tools #3/#4/#5

Use case #4 from `apps/deutsch/deutsch-graph/docs/use-cases.md`: take an existing piece, detect where its claims or framing diverge from David Deutsch's recorded positions, and produce a more optimistic improved version. The app shares the same front half as `deutsch-interject` (`parse_content` -> `segment_claims` -> `divergence.detect`) but uses a different back half: a grounded rewrite plan, constrained turn-level rewriting, marked additions, a per-change audit list, and a JSON sidecar that lets the UI render the original-vs-rewritten diff without recomputing anything.


## Quickstart
From the repo root with the venv active:
```
python apps/deutsch/content-redo/run_redo.py selftest
python apps/deutsch/content-tools/run_tools.py serve --port 8971
python apps/deutsch/content-redo/run_redo.py process apps/deutsch/content-tools/samples/sample-discussion.md --tone 3 --degree 2 --reading-level adult
```
The web UI is served through the shared harness at `http://127.0.0.1:8971/redo`.


## How a run works
1. `dgraph.claims.parse_content` turns pasted prose/transcript text into ordered turns.
2. `dgraph.claims.segment_claims` extracts atomic claims through an injectable LLM chat call.
3. `dgraph.divergence.detect` routes claims to graph grounding and judges each as `agree`, `diverge`, or `no-position`.
4. `dredo.engine.generate_plan` asks for one structured rewrite plan, then hard-filters it by remix degree, claim verdicts, and grounding citations.
5. `dredo.engine.apply_rewrites` rewrites only turns with `correct` or `reframe` changes, batches about five turns per call, keeps untouched turns byte-identical, retries once when a rewrite exceeds the +/-40% length guard, and records skipped notes when it keeps the original.
6. `dredo.render` writes the rewritten markdown, change-list markdown, and JSON sidecar with provenance, disclosure, claims, plan audit rows, per-turn diff data, applied changes, and skipped notes.


## Layout
```
run_redo.py             CLI: process / selftest / serve
dredo/
  config.py             paths, sys.path wiring, degree and reading-level defaults
  engine.py             parse -> segment -> divergence -> plan -> rewrite -> render
  render.py             rewritten markdown, change list, and JSON sidecar assembly
web/content-redo.html   hand-authored UI served by content-tools
openspec/               baseline app spec and archived initial build change
data/                   gitignored output and saved runs
```


## Knobs
- **tone** comes from `ctools.config.TONES`.
- **degree 1** keeps only `correct` changes: outright contradictions of Deutsch's recorded positions.
- **degree 2** keeps `correct` plus `reframe`: pessimistic, inductivist, or authority-based framings can be recast.
- **degree 3** keeps `correct`, `reframe`, and `add`: new knowledge-creation material can be inserted as clearly marked additions after a paragraph.
- **reading-level adult** preserves the source register.
- **reading-level young** aims at ages 10-13 with shorter sentences and inline definitions of hard terms.
- **reading-level child** aims at ages 6-9 with simple vocabulary, concrete examples, and two or three BOI concept terms drawn from the claim grounding.


## Copyright and Provenance Posture
This is a private-education remix tool, not a publishing pipeline. Every rewritten document includes the fixed disclosure that it is an AI transformation of the named source for private educational use, and every applied change is listed with graph-grounded citations. Publishing transformed versions of copyrighted articles, essays, or children's books is legally and ethically dicey; a publishing-safe excerpt mode is a TODO rather than a claim this prototype makes.


## Trade-offs / Alternatives
- **Turn-level rewrite**: pro: untouched paragraphs are copied byte-identically and the UI can show a clean diff. Con: global style smoothing is weaker than whole-document rewriting.
- **Whole-document rewrite**: pro: could produce smoother prose. Con: harder to prove what changed and easier to drift into propaganda-grade rewriting.
- **Plan then rewrite**: pro: degree gates and citation filters are enforceable before generation. Con: costs an extra LLM call and depends on plan quality.
- **Marked additions**: pro: full remix remains auditable because new material is visibly marked. Con: the rewritten document can read less like a seamless original.


## TODOs
- Children's-book picture-text mode that keeps page breaks and image prompts aligned.
- Publishing-safe excerpt mode that rewrites only small quoted spans and leaves the rest as commentary.
- Eval set with known corrections, reframes, no-position cases, and length-guard failures.
- Richer citation previews and claim clustering for long essays.


## Rules for agents
- Do not re-implement parsing, segmentation, routing, judging, grounding, or JSON extraction here; use `dgraph.claims`, `dgraph.divergence`, `dgraph.grounding`, and `dgraph.llm_util`.
- Keep imports safe without API keys; `core.llm` must only be reached through `dgraph.llm_util.chat`.
- Keep unchanged turns byte-identical in the diff and markdown.
- Do not correct `no-position` claims; they can be listed in the sidecar but not treated as Deutsch disagreements.
- `data/` is gitignored local output and run storage; do not commit it.


## Tests
```
.venv/bin/python3 -m pytest tests/test_content_redo.py tests/test_deutsch_interject.py tests/test_dgraph_services.py -q
```
The Content Redo tests stub every LLM call, use the committed Deutsch graph, and cover degree filtering, citation filtering, child reading-level prompts, length-guard retry/skip behavior, provenance, request handling, and sidecar diff completeness.
