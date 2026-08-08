file: apps/deutsch/deutsch-graph/docs/use-cases.md
title: Deutsch Graph — downstream use cases (Randy's notes, summarized and analyzed)
last-updated: 2026-07-07_0845
ai: Claude Code (cloud)
session: `Create new app deutsch-graph`

Randy's voice-dictated notes (verbatim source: `apps/deutsch/deutsch-graph/docs/initial-prompt.md`) describe five downstream applications. The Deutsch Graph is the shared substrate: a superset of David Deutsch's primary-source content plus layered extractions that all five apps traverse. This doc summarizes each use case, then analyzes how it would be built from what exists in this repo today.

Shared repo assets every use case builds on:
- **Corpus** — `data/deutsch/` in S3 (`[S3-FILES-BUCKET]`, ~962 MB): 88 fully processed interviews (`_qafixed` + `_qa-multi` + `_vrb` in `f8_done_qafixed_and_vrb/`), talks (`f8_qafixed_talks/`, `f8_vrb_talks_only/`), both books chapterized (`books/`), 55 essay-type works including 41 Taking Children Seriously posts (`essays/tcs/dd/`), topic matrix (309 topics), curated top-stars selections.
- **QRAG serving stack** — Pinecone index (`deutsch-transcript-qrag-*`, one vector per question, `text-embedding-3-small`), two Chalice Lambdas (`apps/qrag/api/qrag-routing/`, `qrag-llm/`), routing prompts (`core/rag_prompts_routes.py` → `ROUTES_DICT_DEUTSCH_M1`), JWT auth + HMAC PII hashing, exchange capture to `[S3-BUCKET]`.
- **Core library** — `core/llm.py` (provider-swappable), `core/rag.py`, `core/vectordb.py`, `core/structured.py` (QA block grammar), `core/transcribe.py` (new-interview ingestion).
- **This app** — the graph itself: content index, QA-item nodes with topics/stars/timestamps, concept definitions, per-item pointers into verbatim text and YouTube timestamps, cross-references to Pinecone vector IDs (see `graph-spec.md`).


## 1. Worldview Mirror — self-analysis / self-therapy worldview explorer

**Working name: `worldview-mirror`.** (Alternatives: `deep-mirror`, `inner-compass`, `worldview-lab`; "Deep Optimism Mirror" as a public-facing title. Rationale: the tool reflects the user's own worldview back to them next to Deutsch's — it mirrors, it doesn't preach, matching Deutsch's "it's the ideas that matter, not the originator.")

### Summary of Randy's notes
- The most important use case. A tool for someone to articulate and explore **their own worldview**, then compare it against the worldview expressed across Deutsch's interviews and books — the stance Randy calls **deep optimism**.
- A **self-therapy flavor**: provably confidential/secure, so users feel free to share their deepest ideas and stay open to criticism of their deepest beliefs.
- Interaction is a normal chatbot: accounts, threads. Responses can be delivered as text, **audio, or video** — sometimes actual interview clips or TTS of book selections, sometimes AI-processed custom content.
- Personalization tied to problems the user is working on in their life — always user-directed.
- The system builds a **worldview/belief profile** of the user from what they share, and that profile is fully visible to the user (no hidden analysis). Users can swap in **other profiles** (other worldviews) and see how answers would differ under them.
- Design values: **high transparency, high customizability**. A **tone knob** from super-gentle to short/curt/almost-critical.

### Analysis and build path
- **What the graph provides:** the comparison target. "Deutsch's worldview" becomes traversable data instead of vibes: topic-organized, star-ranked QA items with verbatim answers, timestamped YouTube links (for clip delivery), book chapter summaries and term definitions (for TTS delivery), and later the L5 worldview-axis layer (`graph-spec.md`) that scores where Deutsch stands on each axis with citations.
- **Conversation loop:** the existing QRAG two-step (routing → LLM) is the skeleton. The delta is (a) a persistent user profile object that accumulates beliefs the user has expressed, each mapped to the same worldview axes / topics the graph uses, so user-vs-Deutsch comparison is a structured diff, not a one-off prompt; (b) a divergence detector (below, shared with use case 3); (c) the tone knob = a parameterized system-prompt dimension — same mechanism as QRAG's route preambles, one more axis in `routes_dict`.
- **Clip/TTS delivery:** QA nodes carry `youtube_ts_url` (clip start) — a clip service needs only end-timestamps, derivable from the next `_vrb` segment. TTS exists in `apps/voice/` (OpenAI / ElevenLabs / Kokoro). Video generation is speculative; treat as a later phase.
- **Profile transparency:** store the profile as human-readable structured markdown/JSON the user can open, edit, and delete — same block grammar as the corpus (`FIELD: value`), which keeps it LLM-parseable with existing code.
- **Confidentiality ("provably secure"):** hardest requirement, and it's infrastructure, not graph. Existing pieces: HMAC hashing of PII and the `[S3-BUCKET]` bucket split. A credible ladder: (1) client-side encryption with user-held keys, server sees ciphertext except during inference; (2) explicit no-retention inference calls; (3) local/on-device inference for the profile step (the graph is small enough to ship to the client). "Provable" beyond that (enclaves, zero-knowledge) is a research project — recommend claiming "end-to-end encrypted, user-owned data, auditable open code" rather than "provable" in v1.
- **Biggest gaps:** user accounts + thread storage (QRAG has no accounts today — only hashed user IDs on exchanges); the worldview-axis taxonomy (L5) does not exist yet and must be authored/extracted; safety posture for a therapy-adjacent tool (disclaimers, crisis referrals, non-medical framing).

## 2. Worldview Atlas — general worldview explorer + taxonomy of worldviews

**Working name: `worldview-atlas`.**

### Summary of Randy's notes
- A generalized sibling of the Mirror: a **taxonomy of worldviews** — "almost like another graph" — spanning the aspects along which worldviews differ. Users explore worldviews in general, not just their own vs Deutsch's. Other profiles from this atlas are what the Mirror lets users swap in.

### Analysis and build path
- **Structure:** a second small graph that shares infrastructure with the Deutsch graph: nodes = worldview **axes** (epistemology: fallibilism↔justificationism; progress: optimism↔pessimism; agency, morality-objectivity, authority, risk posture, …), **positions** on axes, and **named worldview profiles** (deep optimism, precautionary environmentalism, Bayesian rationalism, religious traditionalism, …) as bundles of positions with supporting sources.
- **Deutsch's profile is the first fully-cited entry:** every position links to QA items / book passages in the Deutsch graph as evidence. That makes the atlas format concrete before any other worldview is added, and it IS the L5 layer of this app.
- **Build mechanics:** LLM extraction over the star-ranked QA layer ("which axis does this answer bear on, which direction, how strongly, quote the evidence") → human review → curated overlay files (`overlays/` in this app), exactly the add/review workflow in `architecture.md`. Other worldviews can be seeded from public philosophical taxonomies and refined the same way.
- **Gaps/risks:** taxonomy design is genuinely hard and contestable — keep axes few (~8–15), orthogonal-ish, and revisable; every profile claim must carry citations or it degrades into caricature. This is the use case where wiki-style review discipline matters most.

## 3. Deutsch Interjector — insert Deutsch into other content

**Working name: `deutsch-interject`.**

### Summary of Randy's notes
- Take a transcript of someone else's interview/podcast (or expository content: book, article) and insert Deutsch as a virtual third participant: "Well, that's not quite true — our best theories actually suggest…"
- Core operation: **identify where the speakers' ideas diverge from Deutsch's**, then generate corrections/insertions.
- Control knobs: direct quotes ↔ light paraphrase ↔ fully customized voice; tone controls as in the Mirror.

### Analysis and build path
- **Pipeline:** (1) ingest external transcript — `core/transcribe.py` + the existing suffix chain if audio, or plain text; (2) segment into claims; (3) **divergence detection**: embed each claim, retrieve nearest Deutsch QA items from Pinecone, classify agree/diverge/no-position with an LLM judge citing the retrieved items; (4) for divergences, generate the interjection at the chosen quote-fidelity and tone; (5) render as an annotated transcript (`_vrb` grammar already supports a third speaker with timestamps — output can literally be a `_vrb.md` with "David Deutsch (virtual)" turns).
- **What the graph adds over raw QRAG:** precision and honesty. Retrieval alone finds *similar* content; the graph's topic edges + star rankings select the *canonical* statement of Deutsch's position, and its verbatim pointers let "direct quote" mode be exactly that — a real quote with a timestamped YouTube citation, not a paraphrase hallucinated as a quote. The no-position route matters: the graph can show Deutsch never addressed a topic (no nodes), and the tool should then say so.
- **Existing precedent in-corpus:** `essays/about deutsch/` (e.g. Dwarkesh Patel's "Contra David Deutsch on AI", Kasra's "The Deutschian deadend") are natural first test inputs — critiques whose divergence points are known.
- **Gaps/risks:** claim segmentation quality; ethical/legal framing (clearly label virtual-Deutsch as synthetic; he's a living person — quote-mode with citations is the defensible default); needs an eval set (hand-marked divergences on 2–3 transcripts) before trusting it.

## 4. Content Redo — optimistic remix of existing content

**Working name: `content-redo`.**

### Summary of Randy's notes
- Take an existing piece — an article, even a **children's book** (education work is a driver) — and remix it: insert Deutsch's ideas, correct divergences, and produce the **more optimistic improved version**.
- Knobs: tone, **degree of remixing** (light touch ↔ full rewrite).

### Analysis and build path
- **Relationship to #3:** same front half (ingest, claim extraction, divergence detection). The back half differs: instead of inserting a third voice, it **rewrites** — a divergence-aware rewrite plan (keep structure, replace pessimistic/inductivist/authority-based framings with knowledge-creation framings), then a constrained generation pass, then a diff view showing what changed and why, each change linked to its supporting graph node (that's the transparency knob that makes this education-grade rather than propaganda-grade).
- **Degree-of-remix knob:** maps to which claim classes get rewritten (only outright contradictions → also framing → also additions), and is exactly the kind of policy an LLM follows well when the divergence list is structured input rather than something it must find itself.
- **Children's-book mode:** reading-level parameter + Deutsch-graph "concept" nodes (BOI terms with definitions) as the vocabulary to teach; `apps/family/` reading work suggests the audience already exists.
- **Gaps/risks:** copyright — remixing others' content is fine for private education use, dicey to publish; the output should carry provenance metadata (source work, transformation description) baked in from day one.

## 5. Content Forge — new content from Deutsch's ideas

**Working name: `content-forge`.**

### Summary of Randy's notes
- Not remixing: **create new content from a description** — "make X about topic Y based on Deutsch's ideas" — in text, audio, video, or interactive-website formats, at varying lengths.

### Analysis and build path
- **This is graph-conditioned generation:** the description selects a subgraph (topics → best QA items, chapter summaries, term definitions → citations), and generation is grounded in that package rather than in the model's memory of Deutsch. The graph query API (`dgraph/query.py`: neighbors, top-starred-by-topic, subgraph export) is the retrieval layer; QRAG's large-context file (`deutsch_large_context_v1.md`) already demonstrates the "curated context bundle" pattern this generalizes.
- **Formats:** text first (essay, lesson, dialogue); audio via `apps/voice/` TTS; interactive website = static page generation with embedded graph excerpts (the viewer in this app is a seed); video last.
- **Quality control:** every generated piece should emit a **citations sidecar** (which graph nodes grounded which sections) — cheap to produce, makes review tractable, and distinguishes this from generic "write like Deutsch" prompting.
- **Gaps/risks:** none structural — this is the most straightforward consumer of the graph. The main dependency is graph coverage/quality (levels L2–L4 populated, which the current build already partially delivers).


## Common infrastructure the graph must therefore provide
Derived from the five use cases, in priority order:
1. **Stable addressing** — every QA item, chapter, concept, topic has a permanent ID + text pointer + (where applicable) timestamped media link. (Done in v0.1.)
2. **Quality ranking** — stars/top-stars propagated onto nodes so "Deutsch's canonical statement on X" is a query. (Done for top-stars; per-item stars sparse in source.)
3. **Topic taxonomy** — curated topic set with merge/alias support (topics review log shows this is an active curation practice). (v0.1 ships raw topics + alias overlay hook.)
4. **Divergence detection service** — shared by #1, #3, #4: claim → nearest Deutsch positions → agree/diverge/no-position verdict with citations. (Design in `architecture.md` §Roadmap; builds on existing Pinecone index.)
5. **Worldview-axis layer (L5)** — shared by #1, #2: axes, positions, cited profile of Deutsch. (Not built; first authoring pass is roadmap item R3.)
6. **Delivery adapters** — clip cutting (timestamps exist), TTS (`apps/voice/`), profile store with encryption (new). (Later phases, per-app.)
