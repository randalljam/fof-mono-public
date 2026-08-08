# Deutsch Graph Specification

## Purpose
Deutsch Graph is a deterministic graph knowledge base over David Deutsch's primary-source corpus, including interviews, talks, books, essays, Taking Children Seriously posts, and the imported 2023 Deutsch Well vault. The app compiles S3-backed corpus inputs and committed curation overlays into reviewable JSONL graph artifacts, exposes a small Python CLI/query layer, and provides a static browser viewer for exploring categories, claims, excerpts, topics, works, Q&A items, chapters, and concepts.

This single `app` capability is the S1-dev baseline for the whole application. Split it into narrower capabilities later only when distinct behavior areas need independent change control.
## Workflows
### Workflow: Refresh the Graph Snapshot
Fetch corpus inputs -> build the deterministic graph -> validate graph integrity -> review generated graph summary and manifest.
Exercises requirements: Corpus Input Fetching, Work Inventory and Identity, QA Extraction and Topic Curation, Book, Chapter, and Concept Layer, Deutsch Well Category Layer, Category Topic Bridging, Deterministic Graph Build Outputs, Graph Validation, Generated Output Boundaries

### Workflow: Inspect the Graph From the CLI
Run stats or topic commands -> load the committed graph -> inspect counts, top QA items, source work ids, and timestamp links.
Exercises requirements: Query Library and Stats, Topic CLI Inspection

### Workflow: Publish Viewer Data Locally
Run export-vis -> regenerate script-loadable viewer shards -> open the hand-authored viewer directly from the checkout.
Exercises requirements: Viewer Data Export, Static Graph Viewer, Generated Output Boundaries

### Workflow: Explore the Deutsch Well Layer
Open the viewer in Explore mode -> expand first-tier categories -> drill into claims and supporting excerpts -> follow sources and bridged topics.
Exercises requirements: Static Graph Viewer, Deutsch Well Category Layer, Category Topic Bridging, Book, Chapter, and Concept Layer

### Workflow: Research a Topic Across the Corpus
Switch to Research mode -> search or filter topics -> inspect works and Q&A items -> follow YouTube timestamps or file links for source context.
Exercises requirements: Static Graph Viewer, Query Library and Stats, QA Extraction and Topic Curation, Work Inventory and Identity
## Requirements
### Requirement: Corpus Input Fetching
The system SHALL provide a fetch command that downloads the corpus inputs needed for a full graph build without uploading to or deleting from S3.

#### Scenario: Fetch uses the manifest and required prefixes
- **WHEN** `python apps/deutsch/deutsch-graph/build_graph.py fetch` is run from the repo root
- **THEN** the system reads `manifests/deutsch.manifest.jsonl`, selects the required `data/deutsch/` prefixes and root files, and downloads missing or size-mismatched files.

#### Scenario: Fetch includes temporary unmanifested folders
- **WHEN** the fetch command enumerates S3 inputs
- **THEN** the system also lists `data/deutsch/deutsch-well_2023/` and `data/deutsch/terms/` directly from S3 until those folders have manifest rows.

#### Scenario: Fetch leaves existing matching files alone
- **WHEN** a required local file already exists with the expected size
- **THEN** the system skips downloading that file.

### Requirement: Work Inventory and Identity
The system SHALL group corpus files into stable typed work records using manifest paths, known filename suffixes, and deterministic work ids.

#### Scenario: Processed files define a work
- **WHEN** manifest rows contain processed interview, talk, transcript, or top-stars files for the same base name
- **THEN** the system groups them into one work node with typed formats and a `work:<slug>` id.

#### Scenario: Archive and scratch folders are ignored
- **WHEN** manifest rows are under excluded folders such as `fx_archive/`, `f9_prev*`, `dd_test_files/`, or `dev-*` scratch folders
- **THEN** the system excludes those files from work inventory.

#### Scenario: Raw files fuzzy-join existing works
- **WHEN** a raw or pipeline-stage file has the same date and sufficiently overlapping title tokens as an already processed work
- **THEN** the system attaches that raw file format to the existing work instead of creating a duplicate work.

### Requirement: QA Extraction and Topic Curation
The system SHALL parse QA corpus files into QA nodes with questions, timestamps, topics, stars, source pointers, and QRAG-compatible vector id metadata.

#### Scenario: QAFixed block is parsed
- **WHEN** a fetched `_qafixed.md` file has a `### qa` section with `QUESTION`, `TIMESTAMP`, `ANSWER`, `TOPICS`, and `STARS` fields
- **THEN** the system creates zero-based QA nodes with timestamp seconds, YouTube timestamp URLs, topic ids, star values, answer pointers, answer character counts, and stable `qa:<work-slug>:<NNN>` ids.

#### Scenario: QA multi adds alternate questions and vector ids
- **WHEN** a matching `_qa-multi.md` block has numbered questions at the same timestamp
- **THEN** the system records alternate questions and a `vector_id_base` value that matches the QRAG Pinecone vector id base convention.

#### Scenario: Topic overlays are applied
- **WHEN** a QA block lists topic labels that appear in `overlays/topics_merge.jsonl`
- **THEN** the system resolves those labels to the configured canonical topic before creating topic nodes and work-topic edges.

### Requirement: Book, Chapter, and Concept Layer
The system SHALL add book, chapter, and concept nodes for The Beginning of Infinity, The Fabric of Reality, and the fetched terms collection.

#### Scenario: Book chapters are available
- **WHEN** chapter files exist under the configured book chapter folders
- **THEN** the system creates chapter nodes with book links, chapter numbers, titles, source paths, and first-paragraph summaries when present.

#### Scenario: Chapter terminology is available
- **WHEN** a chapter file contains a `## TERMINOLOGY` section
- **THEN** the system creates concept nodes linked to that chapter and book.

#### Scenario: Term folder fills concept gaps
- **WHEN** a term exists in the terms collection and no chapter terminology concept already claimed the same book-term id
- **THEN** the system creates a concept node from the term file and records the term source.

### Requirement: Deutsch Well Category Layer
The system SHALL import the 2023 Deutsch Well vault and terms-derived category definitions into category, claim, excerpt, and category-topic graph layers.

#### Scenario: Vault hierarchy is parsed
- **WHEN** the Deutsch Well vault is available under `data/deutsch/deutsch-well_2023/`
- **THEN** the system maps top-level folders to category nodes, claim folders to claim nodes, and excerpt files to excerpt nodes.

#### Scenario: Image artifacts are skipped
- **WHEN** a vault excerpt file is detected as mathpix or image-reference debris
- **THEN** the system omits that excerpt and records a build diagnostic.

#### Scenario: Source references are resolved
- **WHEN** an excerpt has a book chapter or renamed work source reference
- **THEN** the system resolves it to canonical chapter or work node ids using direct matching, overlay aliases, or date-and-title fuzzy matching.

### Requirement: Category Topic Bridging
The system SHALL connect first-tier categories to fine-grained corpus topics through deterministic and curated bridge edges.

#### Scenario: Category label matches a topic
- **WHEN** a category label or singular/plural variant matches an existing topic slug
- **THEN** the system creates a `category_topic` edge from the category to that topic.

#### Scenario: Overlay bridge lists extra topics
- **WHEN** `overlays/category_topics.jsonl` lists topic slugs for a category
- **THEN** the system adds bridge edges for the resolved topic ids and reports unresolved slugs as diagnostics.

#### Scenario: Extra categories are configured
- **WHEN** `overlays/categories_extra.jsonl` defines additional first-tier categories
- **THEN** the system creates those category nodes with `origin: "v0.2-addition"` and any configured definitions or topic bridges.

### Requirement: Deterministic Graph Build Outputs
The system SHALL build the graph deterministically into committed JSONL artifacts, a build manifest, and a generated human summary.

#### Scenario: Build writes graph files
- **WHEN** `python apps/deutsch/deutsch-graph/build_graph.py build` is run
- **THEN** the system writes sorted node JSONL files, sorted edge JSONL files, `graph/build-manifest.json`, and `graph/GRAPH.md`.

#### Scenario: Build manifest pins inputs
- **WHEN** graph outputs are written
- **THEN** the system records the builder version, node and edge counts, diagnostics, manifest-pinned input hashes, and rollups for unmanifested input folders.

#### Scenario: Build validates before success
- **WHEN** the build command finishes writing graph artifacts
- **THEN** the system validates the graph and exits with failure if validation errors are present.

### Requirement: Graph Validation
The system SHALL validate the committed graph for referential integrity, uniqueness, source pointers, and count consistency.

#### Scenario: Valid graph is checked
- **WHEN** `python apps/deutsch/deutsch-graph/build_graph.py validate` is run against the committed graph
- **THEN** the system prints `valid` and exits successfully when no validation errors are found.

#### Scenario: Edge endpoint is missing
- **WHEN** an edge references a missing source or destination node
- **THEN** the validator reports an unresolved endpoint error.

#### Scenario: Manifest counts disagree
- **WHEN** `graph/build-manifest.json` counts do not match the loaded graph data
- **THEN** the validator reports a manifest count mismatch.

### Requirement: Query Library and Stats
The system SHALL load the built graph and provide in-memory traversal, topic, question-search, and stats helpers.

#### Scenario: Graph is loaded
- **WHEN** `dgraph.query.load_graph()` reads a graph directory
- **THEN** the system returns nodes by id, ids grouped by node type, stored edges, and derived edges for QA, claim, excerpt, source, chapter, and concept relationships.

#### Scenario: Topic QA is requested
- **WHEN** `dgraph.query.top_qa_for_topic()` is called for a topic id
- **THEN** the system returns matching QA nodes ordered with top-starred items first, then by star count, then by answer length.

#### Scenario: Stats command is run
- **WHEN** `python apps/deutsch/deutsch-graph/build_graph.py stats` is run
- **THEN** the system prints node and edge counts grouped by type.

### Requirement: Topic CLI Inspection
The system SHALL provide a CLI command for inspecting the best QA items for a topic label.

#### Scenario: Known topic is requested
- **WHEN** `python apps/deutsch/deutsch-graph/build_graph.py topic "<label>"` is run for a known topic label
- **THEN** the system prints top QA items for the topic, including the work id, question, and timestamped YouTube URL when available.

#### Scenario: Unknown topic is requested
- **WHEN** the topic command is run for a label that does not resolve to a topic node
- **THEN** the system prints `unknown topic:` with the computed topic id and exits with failure.

### Requirement: Viewer Data Export
The system SHALL export graph data for browser consumption without requiring a local web server.

#### Scenario: Export-vis is run
- **WHEN** `python apps/deutsch/deutsch-graph/build_graph.py export-vis` is run
- **THEN** the system writes `graph/exports/graph_vis.json` and script-loadable JavaScript shards under `web/graphdata/`.

#### Scenario: Existing viewer shards are regenerated
- **WHEN** viewer data is exported
- **THEN** the system removes stale `.js` files in `web/graphdata/` before writing the new shard list and shard files.

#### Scenario: Shards are sized for repo limits
- **WHEN** viewer data sections are chunked into shard files
- **THEN** each shard is written below the configured shard budget used to stay under the repo pre-commit file-size limit.

### Requirement: Static Graph Viewer
The system SHALL provide a hand-authored static HTML viewer that loads generated script shards and supports graph exploration from `file://`.

#### Scenario: Viewer loads data shards
- **WHEN** `web/deutsch-graph-viewer.html` is opened in a browser from a local checkout
- **THEN** the viewer loads `web/graphdata/index.js` and each listed shard with script tags before booting the graph UI.

#### Scenario: Explore mode is active
- **WHEN** the viewer starts in Explore mode
- **THEN** it shows the first-tier categories, lets users click for details, double-click to expand or collapse children, and follow category, claim, excerpt, topic, work, and QA navigation in the right panel.

#### Scenario: Research mode is selected
- **WHEN** a user selects Research mode
- **THEN** the viewer enables all graph layers, id and file-path details, layer toggles, topic and edge-weight filters, and uncapped or expanded research-oriented traversal controls.

### Requirement: Generated Output Boundaries
The system SHALL preserve the distinction between generated graph/viewer data and hand-authored source files.

#### Scenario: Graph data needs to change
- **WHEN** an agent or developer needs to change generated files under `graph/`
- **THEN** they change `dgraph/` or `overlays/` inputs and rerun the build instead of hand-editing graph outputs.

#### Scenario: Viewer data needs to change
- **WHEN** a developer needs to refresh data consumed by the viewer
- **THEN** they rerun `export-vis` to regenerate `web/graphdata/` rather than hand-editing shard files.

#### Scenario: Viewer source needs to change
- **WHEN** the static viewer UI or behavior needs to change
- **THEN** the hand-authored `web/deutsch-graph-viewer.html` source is edited directly and `export-vis` does not regenerate or overwrite it.
