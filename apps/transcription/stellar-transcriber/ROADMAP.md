file: apps/transcription/stellar-transcriber/ROADMAP.md
title: Stellar Transcriber — roadmap and vision

## Vision
Stellar Transcriber is moving toward a repeatable pipeline that turns raw diarized transcripts, and eventually audio or links, into cleaned draft transcripts whose segmentation, speaker boundaries, and content preservation can be measured against human references. The near-term emphasis is practical transcript repair for existing FOF corpora: build trustworthy eval corpora, score raw and draft variants, and use the alignment ladder plus diff review to decide which draft suffixes are safe to use. Longer term, the app should combine corpus knowledge, speaker identity, source-audio archival, and alternative ASR options into a durable transcription improvement workflow.

## Now / Next / Later
- **Now** — Diarization bench (2026-07-25, `docs/2026-07-25_diarization-bench-plan.md`): field-standard metrics (DER/JER via pyannote.metrics, cpWER via meeteval) and formats (RTTM/UEM/SegLST) over our corpora + the AMI mini benchmark; uniform backend adapters (Deepgram v2, pyannote community-1, ElevenLabs, OpenAI, AssemblyAI, pyannoteAI). Blockers on user: `HF_TOKEN` for pyannote, AssemblyAI/pyannoteAI trial keys, source-MP3 archival for internal-audio runs.
- **Now** — Treat `_draftds` as the usable draft path after the 2026-07-09 BA review, with diff review as the gate for real Deutsch samples.
- **Now** — Keep alignment-first evaluation as the primary development loop: absolute segment-error counts, reduction percentages, and word accuracy as the content-damage guard.
- **Now** — Continue tightening single-transcript repair where it earns its keep, especially transition-local cases where deterministic cleanup and `_draftls` differ.
- **Next** — Build conservation-checked merge/split repair so the pipeline can handle missing/spurious block errors without allowing content drift.
- **Now** — Iterate dual prompts against the `dual-chunks` triple files and validate the 2026-07-11 word-anchored `_draftld` redesign on more episodes (see `docs/2026-07-11_dual-merge-redesign.md`); dual now beats `_draftds` on PV/EPC but not on clean podcast pairs.
- **Next** — Promote and review additional pv reference candidates (`_pub`, `_postce`, `_partialcemanual`) before using them as ground truth.
- **Next** — Add a friendlier one-stem eval wrapper for common real-episode commands.
- **Later** — Add corpus-informed enrichment using corrected corpus material, proper-name support files, and people/title metadata.
- **Later** — Integrate speaker identification with `core/speakerid.py` and enrollment sets per corpus.
- **Next** — Archive source MP3s to S3 so diarization backends can run end-to-end on our own corpora (promoted from Later by the diarization-bench work; external benchmarks with audio are the interim proving ground).
- **Later** — GPU-server bakeoff candidates from the 2026-07-25 research: MOSS-Transcribe-Diarize, NVIDIA Sortformer + Multitalker Parakeet, Tiron (Apple MPS), DiariZen (eval-only license).

## Idea inbox
- 2026-07-10 — Per-transition LLM repair calls around suspect speaker boundaries, so the model sees the exact local context instead of whole chunks.
- 2026-07-10 — Chunk-overlap strategy for `_draftls` so important transitions do not land on chunk joins.
- 2026-07-10 — `denovo-v3` prompt variants focused on missed splits, with one prompt version stamped into draft metadata for comparable runs.
- 2026-07-10 — Explicit word-conservation validation for future merge/split repairs, including segment-accounting checks before accepting LLM output.
- 2026-07-10 — Deterministic dual `_draftdd` review pass remains unexercised in the latest BA notes.
- 2026-07-10 — End-to-end audio/link smoke path should be revisited when `DEEPGRAM_API_KEY` and source audio are available.
- 2026-07-10 — Composite eval and disfluency-policy gaps noted in prior docs should be checked against current `core/transcript_eval.py` before more scoring changes.
