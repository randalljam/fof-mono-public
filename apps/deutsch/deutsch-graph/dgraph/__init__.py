"""deutsch-graph build library: parse the Deutsch corpus into a property graph.

Modules:
- ids: slugify and typed node-id construction
- parse_corpus: QA-block grammar (matches core/structured.py conventions, stdlib-only)
- parse_books: book chapters, BOI terms, chapter summaries
- parse_well: 2023 Deutsch Well vault (categories -> claims -> excerpts)
- parse_terms: curated terms collection (BOI/FOR/BOIxyz glossaries, important topics)
- inventory: manifest scan -> work identity across all pipeline folders
- build: orchestrates a full deterministic build
- validate: referential-integrity checks per docs/graph-spec.md
- query: load and traverse the built graph
- grounding: shared graph grounding packages and citation metadata
- llm_util: import-safe chat/JSON helpers for graph-conditioned LLM services
- claims: external-content turn parsing and claim segmentation
- divergence: route, ground, and judge external claims against the graph
- export_vis: vis-network JSON + standalone HTML viewer
- fetch: download required corpus inputs from S3 per the manifest
"""
GRAPH_BUILDER_VERSION = "0.2.0"
