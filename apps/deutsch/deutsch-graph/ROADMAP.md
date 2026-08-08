file: apps/deutsch/deutsch-graph/ROADMAP.md
title: Deutsch Graph — roadmap and vision

## Vision
Deutsch Graph is intended to become the shared, reviewable knowledge substrate for David Deutsch-related tools: a graph of primary-source works, Q&A extractions, topics, book concepts, first-tier categories, cited claims, and eventually worldview positions. It should preserve provenance back to transcripts, books, vault excerpts, and timestamped media while remaining easy for a solo developer and AI agents to rebuild, inspect, diff, and extend.

The long-term direction is not only a corpus index. The graph should support downstream apps such as Worldview Mirror, Worldview Atlas, Deutsch Interjector, Content Redo, and Content Forge by making Deutsch's ideas addressable, ranked, cited, and traversable.

## Now / Next / Later
- **Now** — Stabilize the S1-dev graph baseline on this branch: v0.2 JSONL graph artifacts, Deutsch Well category/claim/excerpt integration, category-topic bridges, viewer data shards, and the Explore/Research static viewer.
- **Now** — Preserve generated-output discipline: change `dgraph/` and `overlays/`, rebuild `graph/` and `web/graphdata/`, and use `GRAPH.md`, `build-manifest.json`, validation, and tests as the review surface.
- **Now** — Bootstrap OpenSpec as a single living `app` capability plus this roadmap companion so future work starts from an explicit current-behavior contract.
- **Next** — Add manifest rows for `data/deutsch/deutsch-well_2023/` and `data/deutsch/terms/` so the build no longer treats those folders as unmanifested S3 rollups.
- **Next** — Improve quality ranking: extend top-stars matching, fill sparse per-QA star data, and consider LLM-assisted star seeding with human review through overlays.
- **Next** — Build the L5 worldview layer: author roughly 8-15 axes, extract Deutsch positions with citations from top-starred QA and book material, and review them into overlay files for Mirror and Atlas.
- **Next** — Pilot claim/idea extraction and GraphRAG evaluation on a small slice before adding cross-work same-idea edges or community summaries.
- **Next** — Author claims and excerpt support for the six v0.2 added categories: Quantum Physics and the Multiverse, Reality, Constructor Theory, Morality, Children and Education, and Beauty and Aesthetics.
- **Later** — Add a read-only serving API and derived SQLite artifact when the first downstream app needs server-side graph queries.
- **Done 2026-07-12** — Shared divergence detection engine (`dgraph/divergence.py`, with `claims.py` segmentation and `grounding.py` packages): external claim -> routed grounding -> agree/diverge/no-position with citations. Consumed by deutsch-interject and content-redo; Worldview Mirror still uses its implicit reply-prompt version.
- **Later** — Export a publishable Obsidian-style Deutsch-well 2.0 vault from the graph.
- **Later** — Add delivery adapters for clips, TTS, and generated content packages once the citation and profile layers are solid.

## Idea inbox
- 2026-07-10 — Derive YouTube clip end times from neighboring transcript segments so timestamp links can become real clip ranges.
- 2026-07-10 — Make every generated essay, lesson, rewrite, or website emit a citations sidecar listing the graph nodes that grounded each section.
- 2026-07-10 — Design user-owned, visible worldview profiles as human-readable markdown or JSON that users can inspect, edit, delete, and compare against other profiles.
- 2026-07-10 — Explore a confidentiality ladder for Worldview Mirror: client-side encryption with user-held keys, no-retention inference calls, and possibly local profile inference.
- 2026-07-10 — Define knobs shared by downstream apps: tone, quote fidelity, degree of remixing, reading level, and profile/worldview lens.
- 2026-07-10 — Create a hand-labeled divergence eval set from two or three public transcripts before trusting automated interjections or rewrites.
- 2026-07-10 — Keep "virtual Deutsch" outputs clearly labeled as synthetic, with quote mode tied to real citations and timestamps.
- 2026-07-10 — Consider a lightweight local viewer or review UI for overlay edits so curation decisions are easy to inspect before rebuilds.
