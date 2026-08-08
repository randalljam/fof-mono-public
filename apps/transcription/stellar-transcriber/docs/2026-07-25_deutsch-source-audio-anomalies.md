file: apps/transcription/stellar-transcriber/docs/2026-07-25_deutsch-source-audio-anomalies.md
title: Deutsch source-audio recovery — anomalies for EA follow-up
last-updated: 2026-07-25_1535
ai: Cursor - Grok 4.5
session: `deutsch audio recovery + S3 archive`


## Purpose
Track Deutsch corpus source-MP3 recovery gaps for executive-assistant follow-up. Recovered audio lives at `data/deutsch/f0_source_audio/` (repo-local, S3-manifested under area `deutsch`). Duration is verified against the original Deepgram raw JSON `metadata.duration` (±5s or 1%).


## Status snapshot (2026-07-25)
| Status | Count | Notes |
|--------|------:|-------|
| **verified** (local mp3 present, duration matches Deepgram) | **95** | From local DD Corpus Macbook folder (moved) + YouTube re-download |
| **on S3 + in `manifests/deutsch.manifest.jsonl`** | **95 mp3s + inventory** | Uploaded and size-verified 2026-07-25 (`s3://[S3-FILES-BUCKET]/data/deutsch/f0_source_audio/`) |
| **needs EA recovery** | **4** | Listed below — not local and not on S3 until recovered |
| Deutsch eval sessions total | 99 | `data/diarbench/datasets/deutsch/sessions.jsonl` |

Local source used for most older episodes (then **moved**, not copied, into the repo data folder):
`/Users/randytrue/Documents/_David Deutsch/DD Corpus - Main Randy Macbook/1) .mp3 Audio Files/`


## Action needed — recover these 4 mp3s
Place each file at:
`data/deutsch/f0_source_audio/<exact-stem-below>.mp3`

Then tell an agent to re-run duration verification and S3 refresh for area `deutsch`.

### 1. Gad Saad — Quantum Computing / Turing / Multiverses
| Field | Value |
|-------|-------|
| **Stem (filename)** | `2024-10-23_Gad Saad - Quantum Computing Turing Machines and Multiverses.mp3` |
| **Expected duration** | **3889.7 s** (~1h 5m) |
| **Transcript link** | https://youtu.be/S7GS_T_2dyE |
| **Failure** | YouTube download blocked (403 / DRM / SABR). yt-dlp retries with multiple player clients failed. |
| **Where to look** | Google Drive Deutsch audio archive; any local download from the YouTube/podcast page; alternate host if Randy saved one. |

### 2. Theory of Anything — Interview with David Deutsch
| Field | Value |
|-------|-------|
| **Stem (filename)** | `2024-12-23_Theory of Anything - Interview with David Deutsch.mp3` |
| **Expected duration** | **8845.4 s** (~2h 27m) |
| **Transcript link** | https://open.spotify.com/episode/1gqWjEjLboIBX9i4u4F598 |
| **Failure** | Spotify episode — DRM protected; not downloadable via yt-dlp. |
| **Where to look** | Original recording file used for Deepgram; Google Drive; Spotify download if available under Randy's account. |

### 3. Sam Harris 3 — Strange Truths
| Field | Value |
|-------|-------|
| **Stem (filename)** | `2025-05-13_Sam Harris 3 - Strange Truths.mp3` |
| **Expected duration** | **9612.6 s** (~2h 40m) |
| **Transcript link** | none (`link: NO LINK` in transcript metadata) |
| **Failure** | No source URL in the transcript file. |
| **Where to look** | Google Drive; Making Sense / Sam Harris episode audio; any private file Randy used for the Deepgram run. |

### 4. Alex Springer Award — Sam Altman and David Deutsch discuss AGI
| Field | Value |
|-------|-------|
| **Stem (filename)** | `2025-09-24_Alex Springer Award - Sam Altman and David Deutsch discuss AGI.mp3` |
| **Expected duration** | **439.8 s** (~7m 20s) |
| **Transcript link** | https://youtu.be/WZ22AJmuKKQ |
| **Failure** | YouTube download blocked (403 / DRM). Same class of failure as #1. |
| **Where to look** | Google Drive; short event clip / award video download; alternate mirror. |


## Verification rule (after EA drops files in)
Duration of the mp3 must match the Deepgram duration above within **5 seconds or 1%** (whichever is larger). If it matches, status becomes `verified` and the file can be S3-archived. If it is close but outside tolerance, flag as `duration_mismatch` (do not silently use it for bench runs).


## Machine-readable ledger
Per-episode statuses: `data/deutsch/f0_source_audio/audio-inventory.jsonl`


## Local leftovers (not needed for the 99-session eval set)
These remain in the Macbook DD Corpus audio folder because they do **not** match a current deutsch eval-session stem (different episodes / naming). No action required for the S3 deutsch audio archive unless Randy wants them ingested separately:

- `2011-09-01_AirTalk interview with David Lazarus.mp3`
- `2011-10-01_What Now interview with Ken Rose.mp3`
- `2018-04-18_John Horgan interview.mp3`
- `2019-02-12_Innovation Show interview with Aidan McCullen.mp3`
- `2021-06-25_TED interview 2 with Chris Anderson - The Limitless Potential of Human Knowledge.mp3`


## Note on naming mismatches already resolved
Several Macbook filenames differed from repo stems (e.g. Sci-Fi London dated `2011-09-01` locally vs `2011-09-28` in-repo; Tyler Cowen title wording). Those were matched by title/duration and **moved** into the repo under the **repo stem** name. No further EA work on those.
