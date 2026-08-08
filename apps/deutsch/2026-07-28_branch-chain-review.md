file: apps/deutsch/2026-07-28_branch-chain-review.md
title: Deutsch application branch-chain review and future testing handoff
last-updated: 2026-07-28_1349
ai: Codex GPT-5
session: Review and cascade Deutsch content-tools, worldview-mirror, and deutsch-graph branches

**Deutsch application branch-chain review and future testing handoff**

## Executive decision

This branch chain is suitable to merge as a documented prototype baseline. The graph can be rebuilt from the locally fetched production corpus, the committed graph validates, all 91 Deutsch tests pass without network access, every applicable CLI self-test passes, and all reviewed web surfaces boot successfully.

This is not a claim that the applications are production-ready. No live OpenAI generation was performed, generated prose quality has not been human-evaluated, the local-file apps are not designed for concurrent or hosted use, and the Worldview Mirror confidentiality ladder remains explicitly unfinished. Those gaps are listed below so future testing can proceed incrementally.

The review intentionally took a light approach: definite correctness and provenance failures were fixed; larger security, evaluation, storage, and architecture improvements were documented rather than folded into this cleanup.

## Scope and boundaries

The reviewed product areas are:

1. `deutsch-graph`, including graph construction, validation, query/grounding services, generated artifacts, and the interactive viewer.
2. `worldview-mirror`, including the Worldview Atlas taxonomy.
3. `deutsch-interject`.
4. `content-redo`.
5. `content-forge`.

`content-tools` is the shared harness for the final three products.

The branch-chain diff is concentrated under `apps/deutsch/` plus six Deutsch test modules and one `.gitignore` correction. There is no current branch diff under `core/`, `apps/qrag/`, or `web-shared/`. The applications do depend on two external contracts:

- LLM calls reach `core/llm.py` lazily through the shared Deutsch adapters.
- Deutsch graph QA identifiers and `vector_id_base` values are designed to remain compatible with QRAG/Pinecone identifiers.

Neither contract was changed in this review. QRAG behavior was not modified or represented as tested.

No S3 writes, manifest rebuilds, or manifest refreshes were performed. The existing local S3-backed corpus was read for one production graph rebuild. User-owned `.vscode` changes and the unrelated untracked application directories were left untouched.

## Changes made during this review

Everything in this section was changed by the 2026-07-28 Codex review. Features described later as “existing behavior” predate the review.

| Area | Change | Why it was changed | Resulting behavior |
|---|---|---|---|
| Shared harness and all content apps | Added explicit `.gitignore` exceptions and restored five non-secret `config.py` modules for `content-tools`, Interject, Redo, Forge, and Worldview Mirror. | The repository-wide `**/config.py` rule had silently excluded source configuration that the code and documentation required. A fresh checkout failed during test collection. | Fresh checkouts contain the path wiring, registries, knobs, and defaults required to import and run all five modules. No secrets are stored in these files. |
| Shared graph services | Claim segmentation now keeps an LLM-produced source quote only when its whitespace-normalized text occurs verbatim in the referenced source turn. | The prompt asked for verbatim provenance, but malformed or fabricated quotes were previously trusted. | Empty, fabricated, missing-turn, and otherwise invalid claim rows are dropped before downstream divergence or rewriting. |
| Shared graph services | `agree` and `diverge` judgments now require both non-empty Deutsch position text and at least one citation from that claim's allowed grounding. | A model could previously assert a Deutsch position without evidence and downstream tools could act on it. | Unsupported judgments are conservatively downgraded to `no-position`, with empty position/citations, zero confidence, and an explanatory note. |
| Deutsch Interject | Generated interjections with no allowed grounding citation are dropped. | Filtering an invented citation could leave apparently grounded virtual speech with an empty citation list. | Every kept interjection has at least one citation from its claim's grounding, including the existing claim-citation fallback. |
| Content Redo | Marked remix degree 2 as selected in the HTML. | The runtime, CLI, documentation, and config defaulted to degree 2, but the browser silently selected the first option, degree 1. | CLI and browser now start with the same “2 Reframe” default. A regression test ties the HTML selection to the runtime constant. |
| Worldview Mirror | Added API validation for tone, lens, belief text, axis position, and observation confidence. | Manual profile APIs accepted positions outside `-2..+2`, confidence outside `0..1`, non-finite numbers, and invalid thread controls; malformed values could also become server errors. | Invalid editable state is rejected with HTTP 400 before it is persisted or passed to the engine. |
| Deutsch Graph builder | Stopped attempting to UTF-8 decode binary paper files. | The production manifest includes `data/deutsch/papers/Deutsch.law.without.law.pdf`; the builder inventoried the PDF correctly but tried to decode it before checking the extension, so a real rebuild crashed. | Binary papers are inventoried as paper work nodes without being parsed as Markdown. A binary-PDF regression test covers the production failure mode. |
| Generated graph | Rebuilt graph outputs after the builder fix. | The source corpus contained three spelling corrections that were not reflected in the committed generated QA files. | “BS Carter” became “Brandon Carter” in one alternate question, and two “K2 Nordau” occurrences became “Max Nordau.” No node IDs, counts, edges, or viewer shards changed. |
| Documentation | Replaced completed Content Tools TODOs and added this review handoff. | The shared README still said Redo and Forge needed to be created, and there was no single record distinguishing review-pass changes from the earlier implementation. | The future work list and review record now match the code being merged. |

The corresponding implementation commit subjects are:

- `fix(content-tools): track non-secret runtime configs`
- `fix(deutsch-graph): enforce grounded claim judgments`
- `fix(deutsch-interject): reject uncited output`
- `fix(content-redo): align web and runtime defaults`
- `fix(worldview-mirror): validate editable state`
- `fix(deutsch-graph): rebuild with binary paper inputs`

## Existing behavior reviewed by area

### Deutsch Graph

The branch already contained:

- deterministic inventory and parsing for interview/talk QA, books and terminology, essays/TCS material, the Deutsch Well category/claim/excerpt vault, and committed curation overlays;
- stable work, topic, QA, concept, chapter, category, claim, and excerpt IDs;
- referential-integrity validation, queries, grounding packages, and viewer export;
- the shared content parser, claim segmenter, divergence router/judge, and LLM JSON adapter;
- a committed graph and a hand-authored two-mode vis-network viewer.

Reviewed surfaces included `dgraph/`, overlays, graph build output, viewer data export, the viewer, graph docs/specs, and the graph/service tests.

The production rebuild contains:

| Kind | Count |
|---|---:|
| Work/source nodes | 171 |
| Topics | 353 |
| Concepts | 218 |
| Chapters | 32 |
| Categories | 34 |
| Claims | 127 |
| QA nodes | 1,593 |
| Excerpts | 1,797 |
| Work-topic edges | 2,368 |
| Chapter-of edges | 32 |
| Concept-of edges | 218 |
| Category-topic edges | 77 |

The builder reports known data diagnostics rather than failing:

- one duplicate `QUESTION` field in block 14 of the 2023-10-15 “Deutsch Files 2” QA file, where the last field wins;
- one `Topics - Important/Program.md` entry with no category mapping;
- known Mathpix/image-artifact excerpts skipped from several Deutsch Well claims.

Those diagnostics existed in the source corpus and were not silently “fixed” in this code review.

Recommended next tests:

1. Hand-check the top results for a small golden set of topics and concepts, including optimism, AGI, antisemitism, epistemology, and education.
2. Add hand-labeled routing and divergence evaluation cases; current tests prove filtering and orchestration, not semantic quality.
3. Decide whether every build diagnostic is an accepted corpus quirk or a data-cleanup task.
4. Add safe URL-scheme handling and `rel="noopener noreferrer"` to generated/viewer external links before hosting with less-trusted corpus inputs.
5. Consider atomic output replacement so a failed production build cannot leave a partially rewritten graph directory.

### Worldview Mirror and Worldview Atlas

The branch already contained:

- a 14-axis taxonomy and nine seed worldview profiles;
- graph-evidence validation for the Deep Optimism profile;
- a two-call chat engine that extracts beliefs, grounds a response, and mirrors user-vs-lens positions;
- visible local JSON/Markdown profiles, direct axis overrides, local conversation threads, deletion controls, and profile comparison;
- localhost token auth, CLI/self-test commands, and a chat/Profile/Atlas UI.

Reviewed surfaces included taxonomy validation, routing/extraction clamps, prompt assembly, citation resolution, profile aggregation/persistence, thread lifecycle, API behavior, and the UI.

The review did not change the documented v1 security posture. Local files are unencrypted, message text is sent to the selected LLM provider, there are no accounts, and “provably secure” storage/inference is not implemented.

Recommended next tests:

1. Run a real multi-turn conversation with each tone extreme and at least three lenses; inspect the source citations and every automatically recorded belief.
2. Add a confirm/edit step before extracted beliefs enter the persistent profile.
3. Test corrupt/partial local JSON files and introduce atomic writes plus recovery behavior before relying on the profile as durable user data.
4. Replace deprecated FastAPI startup events with lifespan handlers when the shared dependency set is next upgraded.
5. Add URL-scheme allowlisting for citation and Atlas links.
6. Localize and periodically review crisis-resource guidance before use outside the current US-oriented local prototype.

### Shared Content Tools harness

The branch already contained:

- a registry for Interject, Redo, and Forge;
- one localhost token-authenticated FastAPI server;
- shared five-level tone configuration;
- sample discovery and per-app local JSON saved-run storage;
- a landing page and lazy engine imports.

The landing page and all three registered tool pages loaded in browser smoke tests. The current run store is appropriate for a single local process, not concurrent writers or multi-user hosting.

Recommended next tests:

1. Add explicit per-tool request schemas so malformed product inputs return precise 4xx responses rather than the server's generic engine 502.
2. Use atomic run-file writes and collision-safe IDs before enabling concurrency.
3. Validate and encode saved-run identifiers if the API is ever exposed beyond localhost.
4. Consolidate safe external-link rendering across the three tool pages.

### Deutsch Interject

The branch already contained the full parse → segment → route/ground/judge → generate → quote-check → render pipeline, with labeled virtual turns, provenance, disclosures, skipped/no-position rows, three fidelity modes, and JSON/Markdown output.

The review verified citation filtering, quote-regeneration/drop behavior, agreement inclusion, ordering of inserted turns, saved runs, and the shared server path.

Recommended next tests:

1. Build a small hand-labeled evaluation set with expected claims, verdicts, citations, insertion locations, and acceptable interjections.
2. Run real generation in all three fidelity modes and treat `voice` output as the highest-risk mode.
3. Revisit the current quote check's eight-word threshold; shorter fabricated quoted spans are not rejected by that specific guard.
4. Decide what quote-mode behavior should be when the fetched corpus is absent and only question/label grounding is available.

### Content Redo

The branch already contained a grounded plan-and-rewrite pipeline with three remix degrees, three reading levels, citation/claim gates, unchanged-turn preservation, length retry/skip behavior, marked additions, diffs, change lists, provenance, and sidecars.

The review verified degree filtering, plan citation filtering, child-level concept injection, unchanged-turn identity, length guards, request/sample handling, sidecar completeness, and the browser default.

Recommended next tests:

1. Human-review real outputs at each remix degree, especially whether degree 2 reframes without changing the author's substantive position more than intended.
2. Add publishing-safe excerpt mode before using copyrighted material outside private educational workflows.
3. Add golden cases for corrections, reframes, additions, no-position claims, and unacceptable style/meaning drift.
4. Test long documents for batching consistency and cross-paragraph coherence.

### Content Forge

The branch already contained description routing, widened routing fallback, graph grounding, format/length/tone prompts, a long-output retry, inline citation parsing, unknown-citation stripping, section coverage flags, provenance, and Markdown/JSON sidecars.

No Forge implementation change was needed during this review. Its tests and browser page passed.

Recommended next tests:

1. Human-score generated essays, lessons, and dialogues for factual grounding, useful structure, tone, and honest gap statements.
2. Enforce or at least flag “valid graph citation but outside this run's retrieved package”; the current design validates against the whole graph, as its README already documents.
3. Add an outline pass only if long-form coherence proves weak enough to justify the extra latency and prompt surface.
4. Keep audio/video/interactive exports deferred until text grounding and citation evaluation are reliable.

## Verification record

### Passing scoped checks

| Check | Result |
|---|---|
| Six Deutsch suites together | 91 passed |
| `tests/test_deutsch_graph.py` | 28 passed |
| `tests/test_worldview_mirror.py` | 27 passed |
| `tests/test_content_forge.py` | 6 passed |
| `tests/test_content_redo.py` | 10 passed |
| `tests/test_deutsch_interject.py` | 10 passed |
| `tests/test_dgraph_services.py` | 10 passed |
| Python `compileall` across the six app areas | passed |
| Graph production build | passed |
| Graph production validation | zero errors |
| Dry-build tree compared with committed regenerated tree | identical, excluding the separately generated export directory |
| `build_graph.py stats` and topic lookup | passed |
| Worldview Mirror, Content Tools, Interject, Redo, and Forge CLI self-tests | passed |
| Graph viewer browser smoke | Explore loaded; Research showed 367 nodes/880 edges; search returned optimism results; no console errors |
| Worldview Mirror browser smoke | UI, lenses, profile controls, and atlas loaded; no console errors |
| Content Tools browser smoke | landing page found all three tools |
| Interject, Redo, and Forge browser smoke | each tool page loaded with expected defaults and no console errors |

The five warnings in the combined Deutsch test run are known dependency deprecations: Starlette's current TestClient/httpx compatibility warning and FastAPI `on_event` deprecation warnings.

### Broader repository checks that are not green

These failures are outside the Deutsch diff and were not changed:

- Default repository discovery stops on `apps/qrag/web/local_dev/flask_test.py` because `flask_cors` is absent from this venv.
- `pytest tests` ran 661 passing tests and 24 skipped tests, then reported:
  - five lesson-logger extraction-eval failures because the tests reference a removed/moved Hermes script path;
  - four `tests/test_fileops.py` collection errors because module-level functions declare a `self` fixture;
  - two transcription failures that attempt live YouTube access or no longer mock the active Google API path.
- `pip check` reports pre-existing shared-venv version drift involving NumPy, Matplotlib, SciPy, and yt-dlp.

These are repository test/dependency maintenance items, not evidence of a Deutsch regression.

## Suggested return-to-work order

1. Re-run the 91 offline Deutsch tests and the graph build/validate commands.
2. Use one real OpenAI-backed sample through Interject, Redo, and Forge; inspect every citation and sidecar before judging prose quality.
3. Run a short Worldview Mirror session and inspect/delete the inferred profile entries.
4. Create small hand-labeled evaluation sets for graph routing/divergence and each content product.
5. Address safe-link rendering, atomic local persistence, and FastAPI lifespan migration.
6. Only then decide whether to deploy, add accounts, expand formats, or change the storage/inference architecture.

This order separates deterministic data/code correctness from subjective LLM output quality and finally from hosted-product security.

## Codex response
Major fixes included:
  - Restored five runtime configuration modules silently excluded by .gitignore.
  - Enforced verbatim source grounding for extracted claims.
  - Rejected unsupported divergence judgments and uncited interjections.
  - Added Worldview Mirror API state validation.
  - Corrected Content Redo’s UI/runtime default mismatch.
  - Prevented binary PDFs from being decoded as essay Markdown.
  - Rebuilt and deterministically verified the production graph.
  - Added regression tests for each problem.

  Final remote snapshot verification:

  91 passed, 5 known deprecation warnings
  graph validation: valid
  git diff --check: clean

  The final PR is 264 files and 29,397 additions with no deletions. It does not modify
  core/, apps/qrag/, or web-shared/.

  The broader repository still has unrelated pre-existing failures: 661 tests pass, 24 skip,
  7 fail, and 4 error; default collection also encounters a missing flask_cors dependency.
  These and deferred live-LLM/UI testing recommendations are documented in the audit.
