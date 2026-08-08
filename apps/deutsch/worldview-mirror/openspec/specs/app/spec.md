# Worldview Mirror Specification

## Purpose
Worldview Mirror is a local self-reflection chat app that helps a person articulate their own worldview and see it next to a chosen lens worldview — by default David Deutsch's deep optimism, cited to the deutsch-graph. It contains the Worldview Atlas: a hand-curated taxonomy of worldview axes and named worldview profiles that supplies both the lens options and the coordinate system for the user's own visible profile. This single `app` capability is the S1-dev baseline for the whole application.
## Workflows
### Workflow: Hold a Mirrored Conversation
Start the local server -> open the tokenized page -> send a message -> receive a tone-controlled, source-grounded reply with citations -> review the mirror chips and updated profile.
Exercises requirements: Local Server and Session Security, Conversation Turn Pipeline, Grounded Citations, Tone Knob, Belief Extraction Into the Profile, Mirror Comparison

### Workflow: Inspect and Edit the Worldview Profile
Open the Profile tab -> review aggregated positions and observed beliefs -> delete observations, set or clear direct axis positions, or erase the whole profile.
Exercises requirements: Transparent Profile Store, Profile Editing Rights, Mirror Comparison

### Workflow: Explore the Worldview Atlas
Open the Atlas tab -> browse axes and worldview profiles -> open a profile to read positions with evidence -> swap any profile in as the chat lens.
Exercises requirements: Worldview Taxonomy, Graph-Cited Deutsch Profile, Lens Swapping

### Workflow: Verify App Readiness
Run the selftest -> validate the taxonomy against the committed deutsch-graph -> report corpus and API-key readiness.
Exercises requirements: Taxonomy Validation, CLI Entry Points
## Requirements
### Requirement: Worldview Taxonomy
The system SHALL ship a hand-curated taxonomy of worldview axes and named worldview profiles under `taxonomy/`, loadable by the engine.

#### Scenario: Axes are loaded
- **WHEN** `wvmirror.atlas.load_atlas()` runs
- **THEN** it returns the axes from `taxonomy/axes.jsonl`, each with an `axis:` id, label, question, two poles with labels and definitions, supporting frameworks, and source URLs.

#### Scenario: Profiles are loaded
- **WHEN** the atlas is loaded
- **THEN** every `taxonomy/profiles/*.json` file becomes a profile with a `profile:` id, label, summary, sources, variants note, and positions in the shared -2.0..+2.0 scale, where omitting an axis means the profile takes no position on it.

### Requirement: Taxonomy Validation
The system SHALL validate taxonomy structure and graph-cited evidence and refuse to serve an invalid taxonomy.

#### Scenario: Evidence nodes resolve
- **WHEN** `validate_atlas` runs with the committed deutsch-graph nodes
- **THEN** every profile-position evidence entry that names a `node` must exist in the graph, and unknown axes, duplicate or out-of-range positions, and missing summaries are reported as errors.

#### Scenario: Server refuses invalid taxonomy
- **WHEN** the server starts with a taxonomy that fails validation
- **THEN** startup raises an error instead of serving.

### Requirement: Graph-Cited Deutsch Profile
The system SHALL include a deep-optimism profile whose every position carries evidence node ids from the deutsch-graph.

#### Scenario: Deep optimism is graph-cited
- **WHEN** `taxonomy/profiles/deep-optimism.json` is loaded
- **THEN** it is marked `cited_from_graph: true` and each of its positions lists at least one evidence entry whose `node` resolves in the committed graph.

### Requirement: Local Server and Session Security
The system SHALL serve the app on localhost only and require a per-run session token for API access.

#### Scenario: API requires the token
- **WHEN** any `/api/` path is requested without the correct `X-WVM-Token` header
- **THEN** the server responds 401 without processing the request.

#### Scenario: Page carries the token
- **WHEN** `GET /` is requested
- **THEN** the served hand-authored page has the session token injected in place of `__WVM_TOKEN__`, and the server binds 127.0.0.1 only.

### Requirement: Conversation Turn Pipeline
The system SHALL answer each chat message by routing it against the deutsch-graph, grounding from graph content, and generating a lens-aware reply.

#### Scenario: A turn is processed
- **WHEN** `POST /api/chat` receives a message
- **THEN** the engine makes one structured routing/extraction LLM call (topics, categories, concept needles, beliefs), assembles grounding (top-starred QA with verbatim answers when the corpus is fetched, category claims with excerpts, book-term concepts), makes one reply LLM call whose system prompt includes the safety preamble, mirror duty, tone instruction, lens positions, and the user's visible profile, and persists both messages to the thread.

#### Scenario: Corpus is not fetched
- **WHEN** verbatim answer files are absent under `data/deutsch/`
- **THEN** grounding degrades to questions, labels, and definitions from the committed graph and the state endpoint reports `corpus_available: false`.

### Requirement: Grounded Citations
The system SHALL return machine-readable citations for graph node ids referenced in a reply.

#### Scenario: Citations are extracted
- **WHEN** a reply contains node ids in square brackets such as `[qa:<work>:<NNN>]`
- **THEN** the response includes citation objects with id, type, label, and — for QA nodes — the timestamped YouTube URL and work label, deduplicated in order of first appearance.

### Requirement: Tone Knob
The system SHALL support five tone levels from gentle to critical that change the reply's system-prompt instruction.

#### Scenario: Tone is applied
- **WHEN** a thread's tone setting is an integer 1 through 5
- **THEN** the corresponding tone instruction is included in the system prompt, defaulting to level 3 for invalid or missing values.

### Requirement: Belief Extraction Into the Profile
The system SHALL extract beliefs the user asserts and record axis-mapped observations in the user profile.

#### Scenario: Beliefs become observations
- **WHEN** the routing call returns beliefs with a known axis id
- **THEN** each is appended to the profile as an observation with belief text, axis, clamped position (-2..+2), clamped confidence (0..1), verbatim quote, source `chat`, and thread id, and the profile is saved.

#### Scenario: Unmappable beliefs are surfaced but not scored
- **WHEN** an extracted belief has no fitting axis
- **THEN** it is returned to the UI in `observed` with a null axis and is not added as a scored observation.

### Requirement: Transparent Profile Store
The system SHALL store the user profile as fully visible local files with deterministic aggregation.

#### Scenario: Profile is persisted readably
- **WHEN** the profile is saved
- **THEN** it is written as pretty JSON plus a regenerated human-readable markdown mirror in the corpus FIELD: value block grammar, under the app's gitignored `data/profiles/`.

#### Scenario: Positions are aggregated
- **WHEN** aggregated positions are computed
- **THEN** each axis with observations gets a confidence-weighted mean position, and a direct axis override wins over observations for that axis.

### Requirement: Profile Editing Rights
The system SHALL let the user edit and erase everything the app believes about them.

#### Scenario: Observation is deleted
- **WHEN** `DELETE /api/profile/observation/{id}` is called for an existing observation
- **THEN** the observation is removed and the profile re-saved.

#### Scenario: Direct axis position is set or cleared
- **WHEN** `POST /api/profile/axis` is called with a known axis and a position or null
- **THEN** the override is set or cleared and returned in aggregated positions.

#### Scenario: Profile is erased
- **WHEN** `DELETE /api/profile` is called
- **THEN** both stored profile files are deleted and a fresh empty profile is returned.

### Requirement: Mirror Comparison
The system SHALL compare the user's aggregated positions against any atlas profile axis by axis.

#### Scenario: User versus lens
- **WHEN** `GET /api/compare?lens=<profile-id>` is called
- **THEN** rows are returned for every axis either side has a position on, with both positions, the absolute delta, and an alignment label (aligned under 0.7, leaning-apart under 1.5, else divergent; unknown when either side lacks a position), sorted most-divergent first.

#### Scenario: Chat turn mirrors touched axes
- **WHEN** a chat turn extracts beliefs on known axes
- **THEN** the response's `mirror` rows cover exactly those touched axes.

### Requirement: Lens Swapping
The system SHALL let any atlas profile serve as the conversation lens.

#### Scenario: Lens is changed
- **WHEN** a chat request names a lens profile id that exists in the atlas
- **THEN** that profile's positions ground the reply's lens sections and the thread's settings record it; unknown ids fall back to the deep-optimism default.

### Requirement: Thread Storage
The system SHALL store conversations as local JSON thread files with list, read, create, and delete operations.

#### Scenario: Threads round-trip
- **WHEN** a message is appended to a thread
- **THEN** the thread file under `data/threads/` is updated with the message, role, and timestamp, the first user message becomes the thread title, and the threads listing returns newest-first summaries.

#### Scenario: Accounts are out of scope
- **WHEN** the app runs in this baseline
- **THEN** there is exactly one anonymous local user; accounts and server-side storage remain placeholders documented in the README.

### Requirement: Safety Posture
The system SHALL frame itself as a non-medical self-reflection tool with crisis guidance.

#### Scenario: Safety text is always present
- **WHEN** any reply system prompt is assembled or the UI is rendered
- **THEN** the non-therapist framing and crisis-line pointer (988 in the US) are included, and the UI discloses that messages are sent to the OpenAI API while all stored data stays local.

### Requirement: CLI Entry Points
The system SHALL provide serve, selftest, and chat commands.

#### Scenario: Selftest reports readiness
- **WHEN** `python apps/deutsch/worldview-mirror/run_mirror.py selftest` runs
- **THEN** it prints axis/profile/graph counts, taxonomy validity (exiting nonzero when invalid), corpus availability, and API-key presence.

#### Scenario: One-shot chat works headless
- **WHEN** `run_mirror.py chat "<message>"` runs with a valid key
- **THEN** it performs one full turn in a new thread, prints the reply, citations, and observed beliefs, and updates the stored profile.
