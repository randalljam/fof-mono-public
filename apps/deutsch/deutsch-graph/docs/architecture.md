file: apps/deutsch/deutsch-graph/docs/architecture.md
title: Deutsch Graph — architecture decisions, alternatives, and tradeoffs
last-updated: 2026-07-07_1100
ai: Claude Code (cloud)
session: `Create new app deutsch-graph`

This doc records the architecture choices made for the Deutsch Graph v0.1 build, the alternatives considered, and the tradeoffs. Decisions are made (per Randy's instruction) but every one is reversible: the canonical data is plain text in git, so migrating to any alternative below is an export, not a rewrite.

Guiding constraints (from `AGENTS.md`, `PROFILE-randy.md`, and the corpus reality):
- Solo dev + assistant collaborators; everything must be runnable as documented commands, reviewable at the PR level, and maintainable by future AI agents.
- Bulk data lives in S3 keyed 1:1 with repo paths; the repo tracks manifests. `data/` dirs are gitignored at any depth; pre-commit blocks new files > 512 KB.
- The corpus is small by database standards (≈100 processed works, ≈3.5k QA items, ≈300 topics) but rich; full rebuilds are cheap (seconds). Design for legibility and revisability, not scale.


## D1. Canonical representation: compiled property graph as git-tracked JSONL

**Decision:** the graph is a set of newline-delimited JSON files (`graph/nodes/*.jsonl`, `graph/edges/*.jsonl`) committed to the repo, produced by a deterministic build from the corpus + curated overlay files. Property-graph model: typed nodes with attributes, typed directed edges with attributes.

Alternatives and tradeoffs:

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **A. JSONL flat files in git (chosen)** | Zero infra; diffable/reviewable in PRs (matches the repo's whole workflow); trivially consumed by Python, JS viewer, Lambdas; versioning = git; survives any tooling change | No query language; joins are hand-rolled; concurrent editing limited to git semantics | **Chosen for v0.x.** At 10³–10⁴ nodes, `dict` lookups beat any DB round-trip anyway |
| B. SQLite artifact | Real queries (SQL, FTS5 full-text, recursive CTEs for traversal); single file; Lambda-friendly (ship in layer); `apps/math-quiz` precedent (sql-wasm) | Binary blob in git = bad diffs (would need to be gitignored/S3'd or rebuilt in CI); schema migrations | **Adopt as a derived artifact** when a Lambda needs server-side queries — build it from the JSONL, never hand-edit it |
| C. Embedded graph DB (Kuzu, DuckDB+pgq) | Cypher-ish queries, fast traversal at scale | New dependency + query dialect for a graph that fits in RAM; weak agent/collaborator familiarity; binary artifacts | Revisit only if the graph grows ~100× (e.g. per-sentence claims across thousands of works) |
| D. Server graph DB (Neo4j, Neptune) | Full graph stack, visualization, concurrent writes | Standing infra + cost + ops for a solo nonprofit; overkill by orders of magnitude | No |
| E. Obsidian vault as canonical (md + wikilinks) | Human-browsable, the original Deutsch-well form; free UI | Links-in-prose are untyped and unvalidatable; merge conflicts; hard for programs to consume reliably; graph data trapped in a UI's conventions | **Export target, not canonical.** An `export-obsidian` command can regenerate a vault (Deutsch-well 2.0) from the graph at any time |
| F. RDF/OWL triple store | Standards, reasoners, SPARQL | Heavy ceremony; poor fit for narrative provenance; nobody on the team speaks it | No — but keep node/edge types documented so an RDF export is mechanical if ever needed |

## D2. Source of truth: sources compile to the graph; humans edit overlays, not outputs

**Decision:** the graph is a **build artifact**. Inputs are (a) the corpus files in `data/deutsch/` (via S3), (b) the committed manifest `manifests/deutsch.manifest.jsonl`, and (c) committed, hand-editable **overlay files** in `overlays/` (topic aliases/merges, node curation, future worldview axes). `build_graph.py build` is deterministic and idempotent; nothing under `graph/` is ever hand-edited.

- Alternative: hand-curate the graph directly (wiki-style). Pro: maximum editorial control. Con: the corpus keeps growing via the transcription pipeline, and hand-curation can't keep up; regeneration would clobber edits. The overlay pattern gets both: automation for the bulk, curation where humans add value, and every human decision survives rebuilds because it lives in an input file.

This mirrors the repo's existing Chalice rule ("never edit `chalicelib/`, edit `core/`") — same principle, same reviewability.

## D3. Text stays in the corpus; the graph stores pointers

**Decision:** graph nodes carry small text (questions, titles, definitions, summaries ≤ ~1 KB) but **never verbatim answer/transcript bodies**. Each QA node points to its source: repo-relative path (= S3 key), block index, timestamp seconds, YouTube URL. Consumers resolve pointers via local files or S3.

- Why: keeps the committed graph within git/pre-commit budgets; respects the "bulk data lives in S3" rule; avoids duplicating rights-sensitive verbatim content into a second location; and guarantees one source of truth for text (a transcript correction doesn't need a graph edit — the next rebuild picks it up).
- Alternative (embed all text): self-contained artifact, no S3 dependency for consumers — rejected because it doubles storage of a 962 MB corpus's most valuable slices and puts bulk text in git history forever.

## D4. Identity: stable slugs aligned with existing conventions

**Decision:** node IDs are typed, human-readable slugs derived from the corpus's own naming: `work:2018-12-08_joe-boswell-constructor-theory`, `qa:<work-slug>:012`, `topic:constructor-theory`, `concept:boi/explanation`, `chapter:boi/09`. QA nodes also record the **Pinecone vector ID base** (`{filename}_{block}` per `core/vectordb.py`) so graph nodes and QRAG vectors cross-reference exactly.

- Alternatives: UUIDs (opaque, merge-proof, but unreviewable diffs and no human meaning) or content hashes (stable only until any edit). Slugs can break on file renames — mitigated by the overlay alias table (wiki "redirect" pattern) and by the build reporting ID churn between builds.

## D5. Versioning: git + build manifest + review gates

**Decision:**
- Every build writes `graph/build-manifest.json`: builder version, input file list with sha256 (taken from `manifests/deutsch.manifest.jsonl` — the same hashes that govern S3 sync), node/edge counts by type, and diagnostics. The committed graph is therefore a **pinned, reproducible snapshot**: manifest hash ↔ graph state.
- Graph revisions ride ordinary git history on this branch/PRs; a graph release = a tagged commit (`deutsch-graph-v0.1`). `GRAPH.md` (generated) is the human-readable changelog surface — its stat tables make graph diffs legible in PR review.
- Review workflow (wiki best practice, adapted to git): corpus edits and overlay edits are the review surface (small text diffs); `graph/` regeneration is mechanical and reviewed via `GRAPH.md` count deltas + `build_graph.py validate` in the PR.

Alternatives: temporal/bitemporal edges (every assertion carries valid-time — powerful, heavy; revisit for the worldview layer where positions change over Deutsch's career — node `date` fields already give a lightweight version of this); event-sourced graph (append-only change log — the git log already is one at our scale).

## D6. Update model: full rebuild, additive pipeline

**Decision:** adding content follows the existing corpus pipeline (transcribe → `_vrb` → `_qafixed` → `_qa-multi` → S3 upload + manifest refresh), then `build_graph.py fetch && build_graph.py build`. Full rebuild each time — at ~500 files/17 MB it takes seconds, and eliminates the entire class of incremental-consistency bugs.

- Alternative (incremental updates): only worthwhile when rebuild cost hurts; it never will at this corpus's growth rate (a few works/month at most).

## D7. Consumption: static artifacts + Python query lib now; API later

**Decision (v0.x):** consumers read the JSONL directly or via `dgraph/query.py` (load, index, neighbors, top-starred-by-topic, subgraph select, stats). The committed vis-network viewer serves human exploration. No server.

Roadmap when apps need it: a read-only Lambda (`apps/deutsch/deutsch-graph/api/`) serving graph queries from a bundled SQLite artifact (D1-B), following the Chalice patterns in `apps/qrag/api/`; the Pinecone index stays the semantic-search entry point, with vector hits joined to graph nodes via the recorded vector IDs (this join IS the minimal "GraphRAG").

## D8. Relationship to GraphRAG frameworks (LightRAG, MS GraphRAG, etc.)

**Decision:** do not adopt a framework for the core graph. The corpus already has something those frameworks try to synthesize: human-reviewed QA extraction with topics, stars, and timestamps. Wrapping it in a framework's auto-extracted entity graph would *lower* provenance quality.

- Where frameworks earn a look (roadmap R4): auto-extraction of **claim/idea nodes** (L4→L5) and community-summary generation over topics. Evaluate LightRAG (Randy's noted interest, per PROFILE) on a 5-work slice and compare its entity/relation output against the curated topic layer before committing to anything.


## Best practices adopted from the graph-KB / wiki field

| Practice | Origin | How it lands here |
|---|---|---|
| Stable IDs + redirects/aliases | Wikipedia/Wikidata | Typed slugs + overlay alias table (D4) |
| Claims carry citations | Wikidata references | Every node/edge records `source` pointers; L5 positions require citation lists (use-cases §2) |
| Atomic notes, typed links | Zettelkasten/Obsidian | QA items are the atoms; edges are typed, not prose wikilinks |
| Separate ingest / curation / publish layers | Enterprise KG pipelines | corpus → overlays → build → exports (D2) |
| Community summaries over clusters | MS GraphRAG | Topic-level digest generation is roadmap R4, grounded in existing topic edges |
| Editorial review gates | Wiki governance | PR review on overlay/corpus diffs + validate gate (D5) |
| Progressive levels of digestion | (Randy's existing pipeline) | Formalized as layers L0–L5 in `graph-spec.md` |


## Roadmap (post-v0.1)
- **R1 — Deutsch-well 2023 import: DONE (v0.2).** The vault and the `terms/` collection are integrated as the category/claim/excerpt layers — see `deutsch-well-integration.md` for the mapping and modifications. Remaining follow-up: manifest rows for the two folders (they are pinned as unmanifested rollups until then).
- **R2 — Star/quality enrichment:** per-QA stars are sparse in `_qafixed`; extend top-stars matching, consider LLM-assisted star seeding with human review via overlays.
- **R3 — Worldview axes (L5):** author 8–15 axes, extract Deutsch's positions with citations from top-starred QA (LLM pass + review), publish as `overlays/worldview/`. Unblocks Worldview Mirror and Atlas.
- **R4 — Claim extraction + GraphRAG eval:** LightRAG/GraphRAG pilot on a 5-work slice; claim/idea nodes with cross-work "same-idea" edges (the real "graph of ideas").
- **R5 — Divergence detection service:** shared engine for Interjector/Redo (use-cases §3–4), built on Pinecone + graph join.
- **R6 — Serving API + SQLite artifact** when the first downstream app goes live.
- **R7 — Obsidian export** (`Deutsch-well 2.0`): regenerate a publishable vault from the graph.
