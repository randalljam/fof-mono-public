file: apps/deutsch/deutsch-graph/docs/deutsch-well-integration.md
title: Deutsch Well 2023 + terms integration — mapping, modifications, and rationale
last-updated: 2026-07-07_1100
ai: Claude Code (cloud)
session: `Create new app deutsch-graph`

How the 2023 Deutsch Well Obsidian vault (`data/deutsch/deutsch-well_2023/`, 28 categories / 127 claims / 1,812 excerpts) and the curated terms collection (`data/deutsch/terms/`, 250 files in 4 sub-sources) were integrated into graph v0.2, and exactly where the integration deviates from the original. Both folders were read from S3 (they are not yet in `manifests/deutsch.manifest.jsonl`; the build pins them as per-folder sha256 rollups flagged `unmanifested` until their manifest rows land).


## What the vault is, in graph terms
The vault's own Style Guide defines three levels; they map onto the graph one-to-one:

| Well level | Well form | Graph node | Count (v0.2) |
|---|---|---|---|
| L1 | top-level folder ("Problems") | `category` | 28 (+6 added, see M1) |
| L2 | subfolder whose *name is an assertion* ("are solvable, given the right knowledge…") | `claim` | 127 |
| L3 | excerpt file: `<source>.md : <verbatim quote>` | `excerpt` | 1,797 (15 image artifacts skipped) |

On terminology: these L1 nodes are what GraphRAG-style systems call "communities" and what you called first-tier topics/top-level nodes. The build keeps the vault's own word — **category** — and they now sit as the first-tier layer above the 353 fine-grained QRAG topics, connected by explicit `category_topic` bridge edges.

The categories ARE the seed of the worldview layer: "deep optimism" as 28+6 named ideas, each decomposed into claims, each claim backed by verbatim quotes. That is precisely the "cited position" structure the Worldview Mirror/Atlas need, one level below the future L5 axes.

## What was kept verbatim
- **All 28 category names**, unchanged, as `category` nodes (`origin: "deutsch-well-2023"`).
- **All 127 claim texts**, unchanged, as `claim` nodes (the folder name is the claim, exactly as authored).
- **All 1,812 excerpt files** were parsed; 1,797 became `excerpt` nodes with their verbatim text measured, previewed (240 chars), and pointed at (path), and their source attribution resolved. 100% of excerpts resolve to a source: 1,140 to a specific book chapter node, 657 to an interview work node.
- **Terms**: all four sources parsed; `Terms - BOI` (92), `Terms - FOR` (79), `Terms - BOIxyz` (63) merged into the `concept` layer; `Topics - Important` (16) definitions attached to their matching categories.

## Modifications (deviations from the original), with rationale

**M1 — Six categories added** (flagged `origin: "v0.2-addition"`, defined in `overlays/categories_extra.jsonl`, each with a written rationale; delete a line there and rebuild to reject one): *Quantum Physics and the Multiverse*, *Reality*, *Constructor Theory*, *Morality*, *Children and Education*, *Beauty and Aesthetics*. The 2023 vault predates the transcript corpus, and the corpus's heaviest themes have no home in it — physics (161 QA items) and multiverse (130) are the two biggest topics in the whole corpus yet the vault has no physics category at all. *Reality* was in your own `Topics - Important` list but not among the vault categories. The additions carry no claims/excerpts yet — claims for them are future curation (or LLM extraction + review, roadmap R3/R4).

**M2 — Categories bridge to topics instead of replacing them.** The vault's categories and QRAG's 353 `TOPICS:` labels are different granularities of the same thing. Rather than merging them (lossy) the build keeps both layers and connects them with 77 `category_topic` edges: automatic slug/plural matching plus the curated bridge in `overlays/category_topics.jsonl` (e.g. Human Mind ← mind, consciousness, psychology, free-will, fun; Explanatory Knowledge ← knowledge, epistemology, fallibilism, popper). This makes "everything under Problems" a two-hop query across the entire interview corpus — which the 2023 vault could never do.

**M3 — Excerpts store pointer + preview, not full text** (architecture D3). The original vault duplicates verbatim book/interview text as page content. Graph excerpt nodes keep a 240-char preview, the text length, and the file pointer; consumers needing full text read the vault file (or, later, the canonical corpus location it quotes).

**M4 — Source attributions resolved to canonical node ids.** Vault excerpts name their sources by 2023-era file names. 402 references used names the corpus has since renamed; date+title-token fuzzy matching resolved most, and the last 4 renamed/re-dated works (the two Closer to Truth episodes, Tyler Cowen, Sci-Fi London) are mapped in `overlays/aliases.jsonl` — the wiki-redirect mechanism doing exactly its job. Result: 1,797/1,797 excerpts resolved.

**M5 — Vault index pages and tags are not imported.** Category/claim index .md pages, `Associated Entries` lists, and `#L1/#L2/#L3` tags are *derived* structure (the vault's rendering of its own hierarchy). The graph re-derives them from the nodes; a future `export-obsidian` (roadmap R7) regenerates a publishable vault, so nothing is lost.

**M6 — 15 image-artifact excerpts skipped** (mathpix figure-reference debris from the 2023 PDF conversion, e.g. cropped-image URLs as "excerpt" text). Each skip is listed in the build diagnostics; they carry no prose content.

**M7 — Term dedup with book text as source of truth.** Where a term exists both in a chapter's `## TERMINOLOGY` section and in the terms folders, the chapter version wins (it carries the chapter link); term-folder entries fill the gaps (+47 concepts: 218 total, up from 171). Every concept records its provenance in a `source` field (`chapter-terminology`, `all-terms-file`, `terms-boi`, `terms-for`, `terms-boixyz`).

**M8 — One `Topics - Important` entry not imported: `Program.md`.** Its 15 siblings map by name to categories (Brain → Human Brain, Math → Mathematics, Knowledge → Explanatory Knowledge, …) and now serve as those categories' definitions. "Program" has no matching category and its subject is already covered by Computation's bridged `programs` topic; creating a top-level Program category would duplicate Computation. It is reported in the build diagnostics so the decision stays visible — say the word and it becomes a category (one line in `overlays/categories_extra.jsonl`).

## Where this leaves the layer model
- `category` (first tier, 34) → `claim` (127, Well-curated assertions) → `excerpt` (1,797 verbatim citations) is the **curated/top-down** half of the graph.
- `topic` (353) → `qa` (1,593 extraction items) is the **compiled/bottom-up** half.
- The two halves meet through `category_topic` edges and through excerpt source resolution (excerpt → same work/chapter nodes the QA items point into).
- Next obvious moves (roadmap): author claims for the 6 new categories; extend claims with QA-item citations (not just book/interview excerpts); grow L5 axes on top of categories.
