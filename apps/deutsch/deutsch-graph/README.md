file: apps/deutsch/deutsch-graph/README.md
title: deutsch-graph — graph knowledge base of David Deutsch's ideas and content
last-updated: 2026-07-07_1215
ai: Claude Code (cloud)
session: `Create new app deutsch-graph`

A graph-based knowledge base over David Deutsch's primary-source content: interviews, talks, books (The Beginning of Infinity, The Fabric of Reality), essays, and 41 Taking Children Seriously posts — layered under the first-tier categories, claims, and cited excerpts of the 2023 Deutsch Well vault (integrated in v0.2; see `docs/deutsch-well-integration.md`). Built deterministically from the `data/deutsch/` corpus (S3-backed) plus committed curation overlays; the compiled graph is committed under `graph/` and is the substrate for the downstream apps described in `docs/use-cases.md` (Worldview Mirror, Worldview Atlas, Deutsch Interjector, Content Redo, Content Forge). Successor to the 2023 "Deutsch well" Obsidian graph.

Docs:
- `docs/use-cases.md` — Randy's five downstream-app notes, summarized + analyzed with build paths
- `docs/architecture.md` — architecture decisions, alternatives, tradeoffs, roadmap
- `docs/graph-spec.md` — normative data spec: layers L0–L5, node/edge types, IDs, validation
- `docs/deutsch-well-integration.md` — how the 2023 Deutsch Well vault + terms collection map into the graph, and every modification made
- `docs/initial-prompt.md` — original voice-dictated brief


## Quickstart
From the repo root, with the project venv active (`source .venv/bin/activate`; needs `boto3` for fetch only):
```
python apps/deutsch/deutsch-graph/build_graph.py fetch       # download corpus inputs from S3 (~500 files, 16 MB)
python apps/deutsch/deutsch-graph/build_graph.py build       # deterministic build -> graph/ (+ auto-validate)
python apps/deutsch/deutsch-graph/build_graph.py stats       # node/edge counts
python apps/deutsch/deutsch-graph/build_graph.py topic "AGI" # best QA items for a topic
python apps/deutsch/deutsch-graph/build_graph.py export-vis  # regenerate graph/exports/graph_vis.json + web viewer
```
`fetch` uses the scoped `FOF_FILES_DATA_S3_*` credentials when set (cloud sessions), else the default AWS chain. It only downloads; it never writes to S3. Manifested folders come from `manifests/deutsch.manifest.jsonl`; `deutsch-well_2023/` and `terms/` are fetched by direct S3 listing until their manifest rows land.

Viewer: open `web/deutsch-graph-viewer.html` in a browser (works from a local checkout via file:// — data loads from `web/graphdata/` script shards, no server needed). Two modes:
- **Explore** (default) — starts from the 34 first-tier categories only; double-click drills down (category → claims → excerpts; topic → works → Q&A), capped to stay readable; the right panel shows curated content with ▶ YouTube links at the exact timestamp.
- **Research** — every layer with toggles (incl. Q&A items, concepts, chapters), node ids, file paths, open-file links, uncapped expansion, topic/edge-weight filters, isolate.
Shared: split view (graph left, content panel right), search, expand/collapse, show-in-graph, back history, physics toggle.


## Layout
```
build_graph.py      CLI (fetch / build / validate / stats / export-vis / topic)
dgraph/             build library (parsers, inventory, build, validate, query, export)
overlays/           committed curation inputs (topic merges, aliases, category bridge/additions)
graph/              committed build output — never hand-edit (see docs/graph-spec.md)
web/deutsch-graph-viewer.html   interactive viewer — hand-authored SOURCE, edit freely
web/graphdata/      generated data shards for the viewer — never hand-edit
docs/               specs and analysis
data/               (gitignored) bulk/derived outputs, if any
```

## Rules for agents
- `graph/` and `web/graphdata/` are generated: change `dgraph/` or `overlays/`, then rebuild — never hand-edit outputs. `web/deutsch-graph-viewer.html` is the opposite: hand-authored viewer source (edit it directly; `export-vis` only refreshes the data shards).
- The QA-block grammar in `dgraph/parse_corpus.py` deliberately mirrors `core/structured.py` (kept stdlib-only because `core.structured` imports GUI deps unavailable headless). If the corpus grammar changes in core, update both.
- QA node ids and `vector_id_base` line up with QRAG's Pinecone vector ids (`core/vectordb.py`); don't change id construction without reading `docs/graph-spec.md` §ID rules.
- Corpus files come from S3 via `fetch`; do not commit anything under `data/`.

## Tests
```
.venv/bin/python3 -m pytest tests/test_deutsch_graph.py -q
```
Self-contained (inline fixtures; no S3 or corpus files needed).
