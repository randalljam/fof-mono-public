file: apps/deutsch/deutsch-graph/docs/graph-spec.md
title: Deutsch Graph — data specification (layers, nodes, edges, IDs, layout)
last-updated: 2026-07-07_1215
ai: Claude Code (cloud)
session: `Create new app deutsch-graph`

Normative spec for the graph data under `apps/deutsch/deutsch-graph/graph/`. The builder (`dgraph/`) implements this; `build_graph.py validate` enforces it.


## Layers of digestion (L0–L5)
The graph formalizes the corpus's existing processing ladder. Every node records which layer it belongs to via its type; works record how far up the ladder they've been processed (`formats`).

| Layer | Content | Where it lives today |
|---|---|---|
| **L0 raw** | Audio/video, YouTube captions, raw ASR JSON | `f9_raw/` (`_yt`, `_dgwhspm`, `_nova2gen`), `deutsch-audio` bucket |
| **L1 verbatim** | Reviewed verbatim transcripts with speakers + timestamps | `_vrb.md` files |
| **L2 extraction** | QA items: question(s), verbatim answer, timestamp | `_qafixed.md`, `_qa-multi.md` |
| **L3 curation** | Topics per QA, star ratings, top-stars selections | `TOPICS:`/`STARS:` fields, `dd_top-stars_*/`, topics matrix |
| **L4 synthesis** | Chapter summaries, term definitions, large-context digests | `books/BOI - all summaries.md`, `BOI - all terms.md`, `deutsch_large_context_v1.md` |
| **L4 curated (Well)** | First-tier categories, claims, cited excerpts | `deutsch-well_2023/` vault, `terms/` (integrated v0.2 — see `deutsch-well-integration.md`) |
| **L5 worldview** | Worldview axes, cited positions, profiles | not built (roadmap R3) |

## Node types

All nodes share: `id`, `type`, `label`. JSONL, one object per line, sorted by `id` (deterministic diffs).

### `work` — a primary-source content item (`nodes/sources.jsonl`)
| Field | Notes |
|---|---|
| `id` | `work:<slug>` (see IDs below) |
| `kind` | `interview` \| `talk` \| `documentary` \| `book` \| `essay` \| `tcs_post` \| `paper` \| `about` |
| `title` | Human title (from filename base, minus date prefix) |
| `date` | `YYYY-MM-DD` when known (filename prefix), else `null` |
| `by_deutsch` | `false` for `about` works (writing about him), else `true` |
| `base_name` | Exact corpus filename base (joins all suffix variants) |
| `formats` | Map suffix → repo path for every corpus file of this work (`qafixed`, `qa-multi`, `vrb`, `read-qafixed`, `qa-topstars`, `yt`, …) |
| `link_youtube` | From `## metadata` when present |
| `link` | Article/publication URL when present (essays) |
| `layer_max` | Highest layer this work reaches (0–4) |
| `qa_count`, `starred_count` | Filled when L2/L3 present |
| `collection` | Source grouping, e.g. `f8_done`, `talks`, `tcs`, `books`, `essays`, `about` |

### `qa` — one QA extraction block (`nodes/qa/<work-slug>.jsonl`)
| Field | Notes |
|---|---|
| `id` | `qa:<work-slug>:<NNN>` (NNN = zero-padded block ordinal in `_qafixed.md`) |
| `work` | Parent `work:` id |
| `question` | Primary question text (first/only QUESTION) |
| `questions_alt` | Additional numbered questions from `_qa-multi.md` (empty if none) |
| `timestamp_sec` | Integer seconds (from `TIMESTAMP` link `&t=` param), else `null` |
| `youtube_ts_url` | Full timestamped URL, else `null` |
| `topics` | List of `topic:` ids (post-alias-resolution) |
| `stars` | Integer from `STARS:` (0 when blank) |
| `starred` | `true` if this block appears in the work's `_qa-topstars.md` selection |
| `answer_pointer` | `{path, block}` — repo path of `_qafixed.md` + block ordinal; the answer text itself is NOT stored (architecture D3) |
| `answer_chars` | Length of answer text (cheap size signal) |
| `vector_id_base` | `{filename_no_ext}_{block}` with spaces→`_` — matches `core/vectordb.py` Pinecone IDs (`_qN` appended per question there) |

### `topic` — curated topic label (`nodes/topics.jsonl`)
`id` (`topic:<slug>`), `label` (canonical form as written in TOPICS fields), `aliases` (labels merged into this topic via overlay), `qa_count`, `work_count`.

### `concept` — defined term (`nodes/concepts.jsonl`)
`id` (`concept:<book>/<slug>`), `label`, `definition` (short text, stored — L4), `source_work` (`work:boi` etc.), `source_path`, `chapter` (chapter id when defined in a chapter's `## TERMINOLOGY` section, else `null`).

### `chapter` — book chapter (`nodes/chapters.jsonl`)
`id` (`chapter:<book>/<NN>`), `book` (`work:` id), `number`, `title`, `path`, `summary` (first paragraph of the chapter file's `## SUMMARY` section, else `null`).

### `category` — first-tier concept from the Deutsch Well (`nodes/categories.jsonl`)
`id` (`category:<slug>`), `label` (vault folder name verbatim), `definition` (from `terms/Topics - Important` when name-mapped, or the overlay for additions), `origin` (`deutsch-well-2023` \| `v0.2-addition`), `source_path` (vault folder, `null` for additions), `claim_count`, `excerpt_count`, `topics` (bridged `topic:` ids).

### `claim` — assertion about a category (`nodes/claims.jsonl`)
`id` (`claim:<cat-slug>/<NN>`), `text` (vault claim-folder name verbatim), `category`, `excerpt_count`, `path`.

### `excerpt` — verbatim source citation backing a claim (`nodes/excerpts/<cat-slug>.jsonl`)
`id` (`excerpt:<cat-slug>/<claim NN>/<NNN>`), `claim`, `category`, `text_preview` (240 chars), `text_chars`, `source_ref` (raw attribution from the vault file), `source_work` (resolved `work:` id), `source_chapter` (resolved `chapter:` id when the source is a book chapter), `path` (vault file — full text lives there, per D3).

### Future node types (reserved)
`axis` / `position` / `profile` (worldview L5, R3), `person` (interviewers/co-hosts), `external_work` (things Deutsch responds to).

## Edge types

All edges share: `src`, `dst`, `type`. Stored edges are only those that are **not** derivable from node fields:

| File | Type | Meaning | Attributes |
|---|---|---|---|
| `edges/work_topic.jsonl` | `work_topic` | Work discusses topic | `weight` = # QA blocks in that work tagged with the topic |
| `edges/chapter_of.jsonl` | `chapter_of` | Chapter belongs to book | — |
| `edges/concept_of.jsonl` | `concept_of` | Term defined in book | — |
| `edges/category_topic.jsonl` | `category_topic` | First-tier category bridges to fine-grained topic | — |

Derivable (materialized by `dgraph/query.py` at load time, never stored): `qa → work`, `qa → topic`, `claim → category` (`claim_of`), `excerpt → claim` (`excerpt_of`), `excerpt → work/chapter` (`excerpt_source`, `excerpt_source_chapter`), topic–topic co-occurrence (computed, used by exports).

## ID rules
- Slugify: lowercase; spaces and `_`/`—`/`–` → `-`; strip everything except `[a-z0-9-]`; collapse repeats. The date prefix is kept in work slugs: `work:2018-12-08_joe-boswell-constructor-theory` (underscore after date per repo naming convention).
- IDs are permanent. Corpus renames are handled by the overlay alias table (`overlays/aliases.jsonl`, entries `{"type": "work"|"topic", "from": <old label/base>, "to": <canonical id>}`); the build applies aliases before ID assignment and reports unresolved drift.
- Topic IDs come from the label as written in `TOPICS:` fields after alias resolution; case-insensitive dedup keeps the most frequent surface form as `label`.

## Committed layout
```
graph/
  GRAPH.md               generated summary: counts, top topics, coverage tables
  build-manifest.json    builder version, input files + sha256, counts, diagnostics
  nodes/
    sources.jsonl        all works
    topics.jsonl
    concepts.jsonl
    chapters.jsonl
    categories.jsonl
    claims.jsonl
    qa/<work-slug>.jsonl one file per work with L2 data (diff-friendly, each ≪ 512 KB)
    excerpts/<cat-slug>.jsonl one file per category with Well L3 citations
  edges/
    work_topic.jsonl
    chapter_of.jsonl
    concept_of.jsonl
    category_topic.jsonl
  exports/
    graph_vis.json       vis-network payload (works+topics aggregate view)
web/graphdata/           generated viewer data shards (script-loadable, each < 512 KB)
overlays/                hand-curated build inputs (committed, reviewable)
  aliases.jsonl          work renames (wiki-redirect pattern; used by excerpt source resolution)
  topics_merge.jsonl     topic consolidations (seeded from log_2024-09-17 review decisions)
  category_topics.jsonl  curated category -> topic bridge (extends automatic slug matching)
  categories_extra.jsonl categories added beyond the 28 Deutsch Well originals (with rationale)
```
Bulk/derived outputs that exceed git budgets (full-text exports, obsidian vault, SQLite artifact) go under `apps/deutsch/deutsch-graph/data/` — gitignored by the root `data/` rule, S3-manifested later if worth keeping.

## Provenance and reproducibility
- `build-manifest.json` pins every input by repo path + sha256 (sourced from `manifests/deutsch.manifest.jsonl`); files without a manifest row yet (`deutsch-well_2023/`, `terms/`) are hashed directly and rolled up per top-level folder as `{dir, file_count, sha256_rollup, unmanifested: true}`.
- The build is deterministic: same inputs + same builder version ⇒ byte-identical output (stable sort orders everywhere, no timestamps inside node/edge files).
- Excluded from ingestion: `fx_archive/`, `f9_prev*`, `dd_top-stars_new copy/`, `dd_test_files/`, `dev-eval/`, `dev-multi-q/`, `f9_process/`, `f7_no-link-copy/` (archives/dupes/derived copies/eval scratch). `f9_raw/` and `f2/f4/f5/f6` stage folders contribute *inventory only* (works at L0/L1 with status, no QA parsing).

## Validation rules (enforced by `build_graph.py validate`)
1. Every edge endpoint resolves to an existing node id.
2. Every `qa.work` and `qa.topics[]` entry resolves; every `answer_pointer.path` exists in the manifest (or local disk).
3. ID uniqueness across all node files.
4. `work.formats` paths are unique across works (no file claimed twice).
5. Chapter summary alignment: summaries attach only if paragraph count == chapter count for the book.
6. Counts in `GRAPH.md` / `build-manifest.json` match the data files.
