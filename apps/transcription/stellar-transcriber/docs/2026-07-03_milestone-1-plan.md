file: apps/transcription/stellar-transcriber/docs/2026-07-03_milestone-1-plan.md
title: Stellar Transcriber — Milestone 1 plan: foundation and groundwork
last-updated: 2026-07-03_0727
ai: Cursor - Fable 5
session: `Stellar Transcriber — Milestone 1 kickoff`

Milestone 1 of the Stellar Transcriber project. Background and full project context: `2026-07-03_project-notes.md` (cleaned) and `2026-07-03_initial-voice-prompts.md` (raw dictation). Milestones run serially — the Milestone 2 plan is written only after Milestone 1 coding and execution are complete. Working branch: `stellar-transcriber-start`.


## Milestone 1 objective
Establish the foundation for the project: intake the current state of the code and corpora, produce reusable reference/specification files for the core conventions, and produce the design groundwork for the evaluation scoring system. No pipeline or eval implementation happens in this milestone — implementation begins in Milestone 2 with the eval harness.


## Phases

### Phase A — Docs and code intake (complete)
Executed at milestone kickoff (2026-07-03):
- Fixed the app folder name to `apps/transcription/stellar-transcriber/`.
- Merged `origin/feature/transcribe-diarize-dg-latest` into `stellar-transcriber-start` (merge commit `6a1d85e`, merge-base `206a5c3` verified). `core/transcribe.py` now uses `diarize_model="latest"` in all four Deepgram call paths and tags transcript metadata with the `-dl` source suffix. Correction discovered during intake: this code lived on `feature/transcribe-diarize-dg-latest`, not `feature/admin-automation-skills` as dictated.
- Recorded branch ancestry in `plans/git/branch-map.md`.
- Cleaned the dictated project notes into `2026-07-03_project-notes.md` and wrote this plan.

### Phase B — Corpus and eval-pair inventory
Build the catalog of usable eval pairs from the S3 manifests in `plans/2026-04-09_repos-reorg/s3_manifests/` (deutsch, pv, sovereign-child). This is read-only over the committed manifests — no S3 `build`/`refresh` operations (those require explicit user confirmation per repo rules).
- Write a script (proposed: `apps/transcription/stellar-transcriber/scripts/build_corpus_inventory.py`) that scans the three corpus manifests and pairs raw transcripts (`_nova2gen`, `_dgwhspm`, older `_nova2`/`_nova2meet`/`_enhmeet`) with references (`_qafixed`, `_vrb`, `_cemanual`) by date+title stem.
- Output a generated catalog (CSV or JSONL, committed since it is derived from committed manifests and contains no bulk data) recording: corpus, stem, available raw suffixes, available reference suffixes, presence of paired `.json`, S3 keys.
- Write the reference spec `apps/transcription/stellar-transcriber/references/corpus-inventory.md` documenting per-corpus counts, coverage gaps (episodes with raw but no reference and vice versa), and which reference suffix is authoritative per corpus.
- Note for the future audio goal: record in the spec that source MP3s are absent from S3 for these corpora.

### Phase C — Conventions reference specs
Create the reusable, platform-agnostic specification files the rest of the project will rely on, under `apps/transcription/stellar-transcriber/references/`:
1. `transcript-file-conventions.md` — filename stem pattern (`YYYY-MM-DD_<Title>_<suffix>.md`), the full suffix vocabulary (raw model suffixes, human-reference suffixes, pipeline-stage suffixes like `_spasgn`/`_convertnums`, `_yt`), metadata header fields, and the `-dl` transcript-source tag convention (metadata tag, not a filename suffix; wholesale switch to diarize-latest as of early July 2026).
2. `eval-corpus-profiles.md` — per-corpus profile definitions: which reference suffix is ground truth (deutsch: `_qafixed`/`_vrb`; pv: `_cemanual`; sovereign-child: mixed), corpus type (interview vs meeting), and placeholders for per-corpus eval policy choices (disfluency handling etc.) to be filled in during Milestone 2 design work.

### Phase D — transcript_eval review and scoring design
Read-and-document pass over `core/transcript_eval.py` (~4k LOC) producing a design spec (proposed: `apps/transcription/stellar-transcriber/references/eval-scoring-design.md`). Design only — implementation is Milestone 2.
- Document the current pipeline: `evaluate_transcript` orchestration, the five metric steps (segment alignment, WER, quotations, proper names, speaker consistency), CSV/log outputs, batch helpers.
- Design the **composite overall score**: weighting of the per-dimension metrics, normalization, and how a single number is reported per transcript and per corpus.
- Enumerate **disfluency-handling options** (strip/keep/normalize fillers, repeats, false starts) and other normalization choices, and design how policy choices are tracked per corpus and per profile so variations can be applied and compared.
- Design the **per-corpus config** mechanism replacing hardcoded Deutsch paths/suffixes in the `mrun_*` runners.
- List concrete implementation gaps for Milestone 2: `evaluate_transitions` (WIP/aborted), interactive prompts blocking batch runs, spacy-optional handling.


## Next Milestone Planning (M2 and beyond)
Short descriptions only; each milestone gets its own plan document when its predecessor is complete. Details that surface early go into supporting notes/spec files, not into premature execution.

M2 — Eval harness implementation: composite score, disfluency/normalization policy config, and per-corpus profiles as designed in Phase D; de-interactive the batch path; baseline eval runs across the three corpora using the Phase B catalog.

M3 — De novo pipeline: single- and multi-raw-transcript modes on diarize-latest output — end-to-end audio/link → raw diarized transcript(s) → cleaned draft transcript, including the (to-be-designed) merge of multiple model outputs; scored with the M2 harness.

M4 — Corpus-informed enrichment: leverage the corrected corpus and supporting files (proper names, people titles) to improve output on corpus-adjacent recordings.

M5 — Speaker identification integration: wire `core/speakerid.py` (SpeechBrain ECAPA) into the pipeline — enrollment sets per corpus, matching diarized speaker labels to names.

M6 — Audio archival and local ASR: save source MP3s to S3 (coordinated with the manifest/re-key procedures); explore local diarizing-ASR models as an alternative to Deepgram.


## To-dos (Milestone 1)
- [x] Phase A: rename app folder, merge diarize-latest branch, update branch-map ledger, clean dictated notes, write this plan
- [x] Phase B: build corpus inventory script and generated eval-pair catalog; write `references/corpus-inventory.md`
- [x] Phase C: write `references/transcript-file-conventions.md` and `references/eval-corpus-profiles.md`
- [x] Phase D: review `core/transcript_eval.py`; write `references/eval-scoring-design.md` (composite score, disfluency policy, per-corpus config design)
