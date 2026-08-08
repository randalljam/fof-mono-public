file: apps/transcription/stellar-transcriber/docs/2026-07-03_project-notes.md
title: Stellar Transcriber — cleaned project notes
last-updated: 2026-07-03_0727
ai: Cursor - Fable 5
session: `Stellar Transcriber — Milestone 1 kickoff`

Cleaned and organized version of the dictated project notes in `2026-07-03_initial-voice-prompts.md` (kept as-is for provenance). Corrections and code-verified findings are noted inline.


## Goal
Create high-quality, diarized transcripts from audio files or links. The system must work across the full spectrum:
- **De novo mode** — no associated corpus; a new recording with no supporting material.
- **Corpus-informed mode** — a large body of manually corrected, annotated transcripts plus supporting files (proper names, titles for people) is available and should be leveraged.

Additionally, the pipeline should support operating from a **single raw diarized transcript or from multiple** raw transcripts of the same audio:
- Historical standard: two Deepgram models per recording — `nova-2-general` (`_nova2gen`) and `whisper-medium` (`_dgwhspm`) — with the judgment that merging the two could produce higher-quality speaker segmentation. (Note: no fusion code exists yet; `model='both'` in `core/transcribe.py` runs the two models as separate passes.)
- Future option: a **local model** with high-quality diarization (candidate models TBD — unclear which open-source ASR models provide good diarization; separate exploration thread).

Stellar Transcriber is **not** building a diarization engine — it builds on provider diarization (Deepgram) and improves the downstream transcript quality.


## Deepgram diarize-latest status
- Deepgram updated its diarizer; the API now takes `diarize_model="latest"` (replacing the deprecated `diarize=true`), routing to their v2 batch diarizer.
- **Correction to the dictation:** this code was on `feature/transcribe-diarize-dg-latest`, not on EA's `admin-automation-skills` branch (which has no `core/` changes). It was merged into `stellar-transcriber-start` on 2026-07-03 (merge commit `6a1d85e`).
- The change updates all four Deepgram call paths in `core/transcribe.py` (sync, sync SDK, callback lambda, callback presigned-S3) and appends **`-dl`** to the `transcript source` metadata field (e.g. `deepgram nova-2-general-dl`) rather than introducing new filename suffixes. Plan of record: switch wholesale to diarize-latest; transcripts from ~beginning of July 2026 onward use it.


## Eval corpora (ground truth)
The S3 manifests in `manifests/` catalog the transcript corpora (data lives in S3 bucket `[S3-FILES-BUCKET]`, keyed by repo-relative path). Best corpora for eval, pairing raw Deepgram output against human-corrected finals:

| Corpus | Type | Approx. episodes with raw + reference | Reference suffixes |
|--------|------|--------------------------------------|--------------------|
| Deutsch | Interviews | ~105 | `_qafixed`, `_vrb` |
| PV / EPC | Meetings | ~85 | `_cemanual` |
| Sovereign Child | Interviews | ~9 | `_qafixed`, `_vrb`, `_cemanual` |

Suffix conventions observed:
- **Raw machine-diarized:** `_nova2gen` (Deepgram nova-2-general), `_dgwhspm` (Deepgram whisper-medium), older `_nova2`, `_nova2meet`, `_enhmeet`; raw runs usually have a paired `.json`.
- **Human-edited references:** `_qafixed` (QA-fixed final), `_vrb` (verbatim human reference; used by `core/transcript_eval.py` as `REF_SUFFIXPAT`), `_cemanual` (copy-edited manual final).
- **Other stages:** `_yt` (YouTube captions), `_spasgn` (speaker-assignment pass), `_convertnums`.
- Filename stem pattern: `YYYY-MM-DD_<Title>_<suffix>.md`.


## Audio archival (future goal)
Source MP3s are currently NOT archived to S3 (only 2 stray mp3 in deutsch; none in pv or sovereign-child). Future goal: save MP3s to S3 alongside transcripts so splicing, editing, and custom raw-audio processing become possible. MP3s are larger than markdown but modest (not video-scale).


## Transcript eval module (`core/transcript_eval.py`)
A key component to review and improve. Target: an **overall composite score** from comparing the transcriber's automatic diarized output against the human-edited ground truth.

Current state: per-dimension metrics only — segment alignment, WER/word accuracy, quotations, proper names, speaker consistency — written to `eval_metrics.csv`. Orchestrated by `evaluate_transcript`; batch helpers `evaluate_raw_with_std_suffixes`, `create_best_rows_in_metrics_csv`.

Known gaps to address:
- No single composite/overall score.
- No policy for **disfluencies** (and similar normalization choices) — many defensible options; the choice must be tracked and configurable **per corpus and potentially per profile**, so variations can be applied consistently.
- Hardcoded Deutsch paths/suffixes in the `mrun_*` runners; no per-corpus config.
- `evaluate_transitions` is WIP/aborted; interactive prompts on CSV mismatch hinder batch use.


## Speaker identification module (`core/speakerid.py`)
Open-source voice recognition using **SpeechBrain** (ECAPA-TDNN, `speechbrain/spkrec-ecapa-voxceleb`). Creates speaker embeddings from transcript-timestamped audio clips; supports enrollment-set generation and intra-speaker similarity scoring. Think of it as an additional module whose job is **matching voice to name** (actual speaker identification, beyond diarization's anonymous speaker labels).

Current state: early prototype — no speaker-to-name assignment wired into the pipeline, no integration with Deepgram diarization labels. Deps: torch, torchaudio, speechbrain, pydub; weights under `pretrained_models/` (local-only).


## Working method: milestone-based planning
- The project runs as **serial milestones**, each with its own planning document. The next milestone's plan is not created until the current milestone's coding and execution are finished.
- Each milestone plan contains: detailed explanations/descriptions of all **phases** of the current milestone (phases correspond to the to-dos); then, directly above the to-dos, a **Next Milestone Planning (M# and beyond)** section with shorter descriptions of the future milestones (format: `M# — Title: details`); then the phases summarized as **to-dos** at the very end.
- Details for future milestones that surface early get captured in supporting markdown files (notes/specs) so nothing is lost but nothing is executed out of order.
- Along the way, create **reusable reference and specification files** for the project's components.


## Key files to review
- `core/transcribe.py` — Deepgram pipeline (now with diarize-latest)
- `core/transcribe_mtests.py` — manual test harness
- `core/transcript_eval.py` — eval/scoring
- `core/speakerid.py` — SpeechBrain speaker ID


## Related notes (later milestones)
- `2026-07-09_BA-iteration-notes.md` — Jul 2026 diff-review pass on `_draftds`, prompt guardrails for `_draftls`/`_draftld`, Deutsch sample episodes, and current ship recommendation
