file: 2026-07-25_diarization-bench-plan.md
title: Diarization bench — standards adoption, dataset registry, and multi-backend eval plan
last-updated: 2026-07-25_1120
ai: Claude Code - Fable 5
session: `diarz-landscape — diarization bench build-out`


## Why
The 2026-07-25 research compilation (`apps/transcription/2026-07-25_diarization-research.md`) shows the diarization field moved substantially since our last survey: joint speaker-aware ASR models (MOSS, Tiron), a new open-source baseline (pyannote community-1), credible Deepgram challengers (AssemblyAI Universal-3.5 Pro, pyannoteAI Precision-2), and mature community tooling for evaluation (pyannote.metrics, meeteval). Our existing eval harness (`core/transcript_eval.py`) rolls its own segment-error accounting and has **no DER, cpWER, RTTM, or SegLST anywhere** — which means we cannot compare our results to any published number, and we cannot swap ASR/diarization services in and out and score them uniformly. This plan builds that apparatus without reinventing the wheel.

## Standards we adopt (and from whom)
**The leading open-source group in this space is pyannote** (pyannote.audio, pyannote.metrics, pyannote.database; the community-1 pipeline is the current open-source diarization baseline, per both research responses). The multi-talker ASR scoring standard is **meeteval** (fgnt/meeteval, from the CHiME challenge community). We adopt their conventions wholesale:

| Concern | Standard | Source of truth |
|---------|----------|-----------------|
| Diarization ground truth | **RTTM** (`SPEAKER <uri> 1 <start> <dur> <NA> <NA> <spk> <NA> <NA>`) | NIST via pyannote; example: `AMI-diarization-setup/only_words/rttms/` |
| Scored-region masks | **UEM** files | pyannote / DIHARD convention |
| Corpus packaging | per-corpus folder with `lists/` (train/dev/test URIs), `rttms/`, `uems/`, audio fetched by script — exactly the **pyannote/AMI-diarization-setup** layout | `_EXTERNAL-CLONES/_TRANSCRIPTION/AMI-diarization-setup` |
| Diarization metrics | **DER** and **JER** via `pyannote.metrics`, reported under two named protocols: `strict` (collar 0.0, overlap scored) and `lenient` (collar 0.25, overlap scored) | pyannote model-card protocol |
| Speaker-attributed WER | **cpWER / tcpWER / ORC-WER** via `meeteval`, on the **SegLST** JSON format (one record per segment: `session_id`, `speaker`, `words`, `start_time`, `end_time`) | meeteval / CHiME |
| Episode↔session naming | our stem (`YYYY-MM-DD_<Title>`) becomes the SegLST `session_id` / RTTM `uri` | this repo |

Rule: **never report a DER/cpWER without naming the protocol** (collar, overlap, which reference, which normalization policy). This is the single biggest comparability trap called out in the research.

## Where things live
- **External clones** (read-only references): `/Users/randytrue/Documents/Code/_EXTERNAL-CLONES/_TRANSCRIPTION/` — pyannote-audio, AMI-diarization-setup, meeteval, voxconverse, whisperX, DiariZen (see its README for provenance).
- **New core modules** (shared logic, snake_case per repo rules):
  - `core/diar_formats.py` — RTTM/UEM/SegLST read+write; converters: transcript markdown → SegLST/RTTM; Deepgram raw JSON → SegLST/RTTM (word-level, so tcpWER works); normalized hypothesis JSON → all formats.
  - `core/diar_metrics.py` — thin, protocol-pinned wrappers over `pyannote.metrics` (DER/JER, strict+lenient) and `meeteval` (cpWER/tcpWER); returns flat dicts ready for the run log.
  - `core/diar_backends.py` — uniform backend adapters: `run_backend(name, audio_path, opts) -> normalized result` (segments with speaker/start/end + words when available). Each backend declares `is_available()` (package importable / API key present).
- **App config**: `apps/transcription/stellar-transcriber/config/diar-datasets.json` — the dataset registry; `config/diar-backends.json` — backend registry with pinned model revisions/params (no ambiguous `latest` in scored runs).
- **Runner scripts** (thin, in `apps/transcription/stellar-transcriber/scripts/`):
  - `build_diar_dataset.py` — build RTTM/SegLST references from our corpus transcript files into the registry layout.
  - `fetch_diar_benchmark.py` — fetch external benchmark audio (AMI mini via the official mirror URLs; VoxConverse later).
  - `run_diar_bench.py` — run backends × datasets, write hypotheses (normalized JSON + RTTM + SegLST) under `data/diarbench/runs/`, score, append to the stellar run log, render a results table.
- **Data** (gitignored, S3-manifest world): `data/benchmarks/ami/` (external corpora), `data/diarbench/` (built references, hypotheses, run outputs).

## Dataset registry
`diar-datasets.json` registers each dataset with: `kind` (internal corpus | external benchmark), reference source (which suffix / rttm dir), audio location + availability, session lists, and the eval protocol defaults.

| Dataset | Kind | Reference | Audio | Metrics available |
|---------|------|-----------|-------|-------------------|
| `deutsch` | internal (101 ref pairs) | `_qafixed`/`_vrb` md → SegLST; segment-level RTTM (approximate boundaries) | **absent** (MP3 archival is a Later item) | cpWER family vs refs for existing raw arms (`_nova2gen`, `_dgwhspm`); DER only as approximate |
| `pv` | internal (19 ref pairs, hardest diarization) | `_cemanual` md → SegLST | absent | same as deutsch |
| `sovereign-child` | internal (7 pairs, held-out) | mixed refs → SegLST | absent | same |
| `fda` | internal, **deferred to a later phase** | started from published PDF transcripts (not audio) with heavy copy-edit/name cleanup; transcripts live only in `exchanges/qrag_fda-c19-townhalls` (S3); audio recovery is its own project | absent | — |
| `ami` | external benchmark | `AMI-diarization-setup/only_words/rttms` + `uems` (true fine-grained ground truth) | **present**: official `mini` split wavs under `data/benchmarks/ami/amicorpus/` | DER/JER (true), full backend bakeoff |
| `voxconverse` | external benchmark (later) | RTTMs in clone | fetchable | DER/JER |

Key insight from the corpus survey: because our corpora had no local audio at build time, **internal corpora score transcripts (cpWER family, plus the existing custom harness), while external benchmarks with audio+RTTM are where we actually *run* new backends end-to-end**. The two meet as source audio is recovered.

### Source audio recovery (added 2026-07-25, after review)
Decision: reference corpora need their source audio (typically mp3), stored in S3 (`[S3-FILES-BUCKET]`, manifest-keyed like all corpus data) with local copies under `data/<corpus>/.../f0_source_audio/` for processing. Flow, per corpus:
1. `scripts/fetch_corpus_audio.py --dataset <name>` — downloads each episode's audio from its transcript-metadata YouTube link and **verifies duration against the raw Deepgram JSON `metadata.duration`** (tolerance 5s or 1%), so we know it is the same audio the raw transcripts came from. Ledger: `<audio_dir>/audio-inventory.jsonl` (statuses: verified / duration_mismatch / download_failed / no_link / no_dg_duration).
2. Some Deutsch episodes may be unrecoverable from YouTube (expired links, non-standard downloads); Randy previously stored Deutsch mp3s in Google Drive — that is the fallback source for failed/mismatched episodes.
3. S3 archival via `core/s3_archive.py` (build → upload with `--execute`) — run only with explicit user confirmation per repo rules; then fresh checkouts pull local copies on demand.
4. Priority: **deutsch and pv are the two development corpora.** FDA townhalls are deferred to a later phase — that corpus started from published PDF transcripts (not audio), needed heavy cleanup of copy/edit and name errors, and its matching audio recovery is its own project.

## Backend matrix
| Backend id | Type | Needs | Status |
|------------|------|-------|--------|
| `deepgram-nova2` / `deepgram-nova3` × `diarize_model=v2` | API | `DEEPGRAM_API_KEY` (present) | ready — supersedes deprecated `diarize=true` |
| `pyannote-community1` (+ any ASR) | local | `pyannote.audio` (installed), gated HF model → **needs `HF_TOKEN`** | blocked on token |
| `whisperx` / `mlx-whisper` + pyannote | local | pip installs; HF token for diarization | later |
| `assemblyai-universal35pro` | API | **needs `ASSEMBLYAI_API_KEY`** | blocked on key |
| `elevenlabs-scribe2` | API | `ELEVENLABS_API_KEY` (present) | ready |
| `openai-4o-transcribe-diarize` | API | `OPENAI_API_KEY` (present) | ready |
| `pyannoteai-precision2` | API | **needs pyannoteAI key** (150 free hours trial) | blocked on key |
| MOSS-Transcribe-Diarize / Tiron / Sortformer+Parakeet | local GPU | NVIDIA server (MOSS/NVIDIA) or MPS harness (Tiron) | phase 3 |
| DiariZen v2 | local, CC-BY-NC | eval-only (license) | phase 3 |

## Execution phases
1. **Now (this session)** — clones + installs done; formats/metrics/backends modules + registry + converters + tests; fetch AMI mini subset; smoke-run available backends (Deepgram at minimum) on AMI test.mini; first DER numbers in `references/diar-bench-results.md`; cpWER for existing deutsch/pv raw arms vs refs.
2. **Next** — user supplies HF token (pyannote community-1 local runs on AMI + eventually our audio), AssemblyAI + pyannoteAI trial keys; archive source MP3s for a 5–10 hr internal bakeoff slice per the research doc's recipe (clean 2-person, similar voices, rapid backchannels, meetings); add VoxConverse.
3. **Later** — GPU-server candidates (MOSS, Sortformer+Multitalker Parakeet, Tiron on MPS), DiariZen eval-only ceiling; longitudinal/correction-propagation track (Track B in the research doc) once per-file bench is stable.

## Relationship to the existing harness
The custom alignment-first metrics (`seg_error_count_strict`, misalign windows, dual recovery) remain the **repair-loop** instrumentation — they answer "can we fix our existing raw transcripts". The new bench answers a different question — "which service/model/pipeline should produce raw transcripts going forward" — in the field's own units so published numbers (community-1 AMI DER 17.0 strict, etc.) become directly comparable sanity checks. `run_diar_bench.py` logs to the same `stellar-run-log.jsonl` ledger.

## User actions needed
- ~~Create a Hugging Face token, accept the `pyannote/speaker-diarization-community-1` gate, add `HF_TOKEN=` to `.env`.~~ **Done 2026-07-25** (verified via `whoami`).
- ~~ffmpeg for torchcodec/pyannote audio loading.~~ **Done 2026-07-25**: root cause was an arch mismatch (only Intel Homebrew at `/usr/local`, x86_64 ffmpeg libs vs arm64 Python); Apple Silicon Homebrew installed at `/opt/homebrew` with native ffmpeg 8.1.2; ensure bench shells keep `/opt/homebrew/bin` first on PATH. torchcodec 0.15.0 now imports clean. (The backend also loads waveforms via soundfile, so it works either way.)
- Env note 2026-07-25: numpy 2.5.1 / scipy 1.18.0 now in the shared venv (pyannote-metrics requirement); this conflicts with declared langchain/llama-index pins — leave as-is unless QRAG breaks. Diar test suite green under both stacks.
- (Optional, phase 2) AssemblyAI key; pyannoteAI trial key (150 free hrs); FDA corpus promotion decision (deferred).
