file: apps/transcription/2026-07-25_diarization-research.md
title: Diarization research — Claude + ChatGPT chat compilation
last-updated: 2026-07-25_0945
ai: various
session: various


# Prompt 1 - diarization landscape
Do an exhaustive search and what I want you to figure out is what the best option for local automatic speech recognition that includes diarization is currently, you know, what state of the art, what's the best model and way that I can get high quality conversations transcribed where it does accurate speaker segmentation for several years now, focusing on conversations and diarizations. I've been using Deep Gram primarily comparing multiple models developing a lot of code to do this. They have a new Deep Gram has a new improved diarization flag. I'm blanking on what what you do, but you set a flag to I think it's diarization equals latest or something in the API call. But so I have that and I'm aware of that. I don't want to use an API third party service. I'm hoping that something like what a whisper, you know, from open AI includes now includes diarization and I can run that model locally or spin up a private server to run it if it's a larger model and my MacBook Pro has trouble running it, but I run super whisper and have for years. I think it may even offer a local option. So search for search super whisper for its current capabilities. It's a Mac OS mini bar app. It's had quite a bit of development. It's been offering the diarization for quite some time and I tried it a while ago and it didn't didn't work very well. So, Yeah, I want to know everything about the progress in the space. There's a lot more models out there now. I think Nvidia has a model. A lot of these models are focused on just word error rate. But I need to know who and what models are focused on diarization because that to me is the crux pulling out good speaker segmentation where a human reviewing the audio and the and the transcripts, you know, thinks they can't do much better than what what the you know model plus tech and it could be deterministic code wrapped around, you know, outputs of these models. But if there's anybody offering this as a service that's better than deep deep grams latest, then I want to know about that too. So it's not that I'm not interested in the third party API service services. I think D script or somebody is often recommended. I've done waves of research on this. It's just been a little while since I've done it and I need to get up to speed on that. The latest and I'm going to make a push now to to work on this and I want to I want to do so with with the latest tech at my fingertips. So do this exhaustive search. And summarizes for me in a good way and deliver both a complete report and a TLDR summary at the bottom of that for me.

# ChatGPT (5.6 Sol Extra High) response - diarization landscape
**Local ASR with speaker diarization: state of the art, July 24, 2026**

## Bottom line

There is no single uncontested winner yet. The field has improved substantially, however, and the best new systems no longer treat transcription and diarization as completely separate tasks.

My recommendations are:

1. **Best new local batch-transcription candidate:** **MOSS-Transcribe-Diarize 0.9B**. It jointly produces words, speakers, and timestamps; handles recordings up to 90 minutes in one long-context pass; supports 50+ languages; is Apache-2.0; and currently has the strongest evidence among deployable open models for complete meeting transcription. It is only two weeks old, so I would call it the leading candidate—not a settled production champion. [Model and code](https://huggingface.co/OpenMOSS-Team/MOSS-Transcribe-Diarize)

2. **Best Mac-native open candidate:** **Tiron**. It uses a modified Whisper large-v3 architecture, outputs speaker turns and timestamps jointly, and its official whole-meeting harness supports Apple Silicon through MPS. It is faster and easier to run locally than the official MOSS stack, but MOSS currently beats it on most same-harness meeting benchmarks. [Tiron model](https://huggingface.co/Trelis/tiron), [meeting harness](https://github.com/TrelisResearch/tiron)

3. **Best mature, commercially usable open diarizer:** **pyannote Community-1**, combined with your preferred ASR and word aligner. It is the safest modular choice for a production system you control. It is not the absolute research leader, but it is well documented, offline, CC-BY-4.0, widely used, and supports both overlap-aware output and an “exclusive” output designed for assigning ASR words to one speaker. [Community-1 model and benchmarks](https://huggingface.co/pyannote/speaker-diarization-community-1)

4. **Best open diarization-only model for research quality:** **DiariZen Large v2**. It reports materially lower DER than pyannote 3.1 across AMI, AliMeeting, DIHARD3, VoxConverse, and other corpora and can represent up to four overlapping speakers. The problem is licensing: the weights are CC-BY-NC-4.0, so they are not suitable for a commercial product. [DiariZen v2 model card](https://huggingface.co/BUT-FIT/diarizen-wavlm-large-s80-md-v2)

5. **Best local solution for real-time audio and serious overlap:** **NVIDIA Streaming Sortformer v2.1 plus Multitalker Parakeet**. Unlike an ordinary diarization-plus-ASR pipeline, Multitalker Parakeet runs a speaker-conditioned transcription path for each speaker, allowing it to recover both sides of heavily overlapped speech. This is the quality-oriented choice for a private NVIDIA GPU server, not a Mac-first stack. [Sortformer v2.1](https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2.1), [Multitalker Parakeet](https://huggingface.co/nvidia/multitalker-parakeet-streaming-0.6b-v1)

6. **Best turnkey, commercially supported on-device Mac option:** **Speechmatics On-Device**. It runs with CoreML on M1-or-newer Macs, includes diarization and speaker identification, and supports batch and real-time processing. It is enterprise/contact-sales software, and Speechmatics does not publish a sufficiently detailed diarization benchmark, so insist on a pilot against your own corpus. [Speechmatics On-Device](https://www.speechmatics.com/speech-to-text/on-device)

7. **Most credible API challenger to Deepgram:** **AssemblyAI Universal-3.5 Pro**. AssemblyAI’s current same-dataset cpWER benchmark shows it outperforming Deepgram Nova-3, ElevenLabs Scribe v2, Speechmatics, Soniox, Gladia, and Voxtral. But AssemblyAI does not document whether its Deepgram run used the new V2 diarizer, so this is not yet proof that it beats properly configured Deepgram V2. [Universal-3.5 Pro results](https://www.assemblyai.com/blog/universal-3-5-pro-async)

## The Deepgram flag you were remembering

The new parameter is:

```text
diarize_model=latest
```

For batch audio, `latest` currently resolves to V2. You can pin it with:

```text
diarize_model=v2
```

The old:

```text
diarize=true
```

is deprecated and remains pinned to V1. Do not send both parameters. V2 is batch-only; streaming `latest` still resolves to V1. It works with Nova-1/2/3, Enhanced, and Base, but not Deepgram’s hosted Whisper model. [Deepgram diarization documentation](https://developers.deepgram.com/docs/diarization)

Deepgram says V2 uses a new embedding model plus improved segmentation and clustering. In its 158-vote human comparison, V2 was preferred 63.3% of the time, V1 19%, and 17.7% had no preference. That is encouraging, but Deepgram only publishes confusion-error graphics and human preference—not a reproducible DER/cpWER table against competing systems. [Deepgram’s V2 announcement](https://deepgram.com/learn/introducing-batch-diarization-v2)

V2 can also be licensed for Deepgram self-hosted deployment. If preserving your existing Deepgram integration is valuable and enterprise licensing is feasible, self-hosted Nova-3 plus Diarization V2 is arguably your lowest-risk private-deployment option.

## What happened with Whisper

### Open-source Whisper still does not contain diarization

The locally downloadable OpenAI Whisper models perform ASR, translation, language identification, and related speech processing. They do not natively determine speaker identity or produce speaker-attributed transcripts. The repository remains MIT-licensed and locally runnable, but diarization must come from another model. [OpenAI Whisper repository](https://github.com/openai/whisper)

WhisperX does not change the Whisper model itself. It is an orchestration layer that combines faster-whisper, forced alignment, and—currently—pyannote Community-1. It then associates aligned words with speakers using timestamp overlap. That is a useful baseline, but simple maximum-overlap assignment is exactly where short backchannels and simultaneous speech can be misattributed. [WhisperX](https://github.com/m-bain/whisperX)

### OpenAI now has diarization—but only as an API model

`gpt-4o-transcribe-diarize` is a distinct hosted model. It returns `diarized_json` containing speakers, start times, and end times. You can provide short reference clips for as many as four known speakers, which is a valuable speaker-identification feature. It is not an open-weight or locally deployable version of Whisper. [Model documentation](https://developers.openai.com/api/docs/models/gpt-4o-transcribe-diarize), [speech-to-text guide](https://developers.openai.com/api/docs/guides/speech-to-text)

So the direct answer is: **OpenAI has added diarized transcription to its API product, but has not added local diarization to open-source Whisper.**

## The leading local systems

| System | Strength | Main weakness | Deployment |
|---|---|---|---|
| MOSS-Transcribe-Diarize | Strongest new open long-form “who/when/what” candidate | Extremely new; vendor-led evaluation; no standard DER table | Officially CUDA/server-oriented |
| Tiron | Official Apple MPS support; fast; Apache-2.0; reproducible meeting harness | 30-second native windows; global speakers depend on ECAPA linking | Mac, CUDA, or CPU |
| pyannote Community-1 + ASR | Mature, modular, tunable, commercially usable | ASR/diarization reconciliation remains a failure point | CPU or CUDA; Mac CPU practical |
| DiariZen v2 + ASR | Excellent pure diarization results; overlap-aware | Noncommercial weights | Local research/CUDA |
| Sortformer + Multitalker Parakeet | Best open design for streaming and transcribing both overlapping speakers | CUDA-oriented; up to four speakers; compute scales per speaker | NVIDIA GPU server |
| VibeVoice-ASR | One-pass 60-minute transcripts, 50+ languages, MIT | 8B model; explicitly misses secondary speech in overlap | Large GPU server |
| SoulX-Transcriber | Strong emerging joint ASR/diarization model | Qwen3-Omni 30B architecture; Chinese/English; heavy infrastructure | Large CUDA server |
| Speechmatics On-Device | Turnkey CoreML, real-time, diarization and identification | Closed enterprise licensing and opaque benchmarks | M1+ Mac or Windows |

### MOSS-Transcribe-Diarize

MOSS is the most consequential development I found. It uses a Whisper-style audio encoder and a small Qwen-style text decoder, then generates timestamped speaker-attributed text such as:

```text
[0.48][S01]Welcome everyone[1.66]
[12.26][S02]The pipeline is ready[13.81]
```

Important properties:

- Apache-2.0 weights and code.
- 50+ languages.
- Hotword/context prompting.
- Up to 90 minutes in a 128K context.
- Trained on real conversations and simulated mixtures containing as many as 12 speakers and substantial overlap.
- Local web UI plus JSON, SRT, and ASS output.
- OpenAI-compatible local transcription endpoint through SGLang or vLLM.
- No streaming yet. [Technical report](https://arxiv.org/pdf/2601.01554)

The most useful cross-check comes from Tiron’s newly published identical-harness comparison. Across 17 whole meetings from AMI, ICSI, and NOTSOFAR-1, macro cpWER was:

- MOSS: 25.44
- Tiron: 30.71
- AssemblyAI Universal-3.5 Pro: 36.31

MOSS led on AMI and NOTSOFAR; MOSS and Tiron were effectively tied on ICSI. The evaluation is small, produced by Tiron’s developer, and does not include Deepgram V2, but the meetings, references, and replication tools were published. It is considerably more useful than comparing unrelated vendor charts. [Tiron’s benchmark details](https://huggingface.co/Trelis/tiron)

MOSS’s official optimized serving stack is CUDA-first. Community MLX conversions already exist for Apple Silicon, but they are only days old and have not been properly validated. I would deploy MOSS on a private NVIDIA server for the first serious evaluation.

### Tiron

Tiron is based on Whisper large-v3 with added speaker and timestamp tokens. Each 30-second window can contain up to eight speakers. For whole meetings, its harness performs:

- Windowed decoding.
- A staggered second pass.
- ECAPA voice embeddings.
- Cross-window clustering.
- Meeting-global speaker labels.
- JSON/SRT/VTT output.

Its major advantage for you is official Apple Silicon/MPS support. The model card reports 3–12 GB of GPU memory and approximately 43× real-time on its GPU evaluation, although Mac performance will naturally be lower. It is an excellent first Mac experiment and a useful contrast to MOSS’s long-context approach.

Its risk is the 30-second boundary: speaker numbers inside each window are local, so the harness must correctly link the same voice across windows. Long-context MOSS avoids that particular failure mode.

### pyannote Community-1

Community-1 remains the best dependable modular default. Its published no-collar, overlap-included DER includes:

- AMI IHM: 17.0
- AMI SDM: 19.9
- AliMeeting: 20.3
- DIHARD3: 20.2
- VoxConverse: 11.2

It accepts an exact, minimum, or maximum speaker count. Providing the known count when available can materially reduce split/merge errors.

It returns two timelines:

- Regular diarization, which can contain overlapping active speakers.
- `exclusive_speaker_diarization`, where only the speaker most likely to have produced the transcribed words is active.

Exclusive output is valuable for word assignment, but it intentionally collapses overlap. Preserve the regular output too; otherwise you lose the information that two people spoke simultaneously. [Community-1 explanation](https://www.pyannote.ai/blog/community-1)

### DiariZen v2

DiariZen’s reported zero-collar DER is impressive:

- AMI: 13.9
- AISHELL-4: 10.1
- AliMeeting: 10.8
- NOTSOFAR-1: 16.7
- DIHARD3: 14.5
- VoxConverse: 9.1

It supports up to four simultaneous speakers and is computationally pruned. These results make it the strongest diarization-only open-weight research candidate I found.

The noncommercial license is decisive. Use it to estimate the quality ceiling or for noncommercial work, but do not quietly embed it in a commercial pipeline.

### NVIDIA Sortformer plus Multitalker Parakeet

Sortformer v2.1 is a true streaming diarizer with a speaker cache and 80 ms activity frames. It supports up to four speakers. With a high-latency configuration it reports:

- AMI IHM DER: 15.90
- AMI SDM: 17.80
- AliMeeting near/far: 11.73/13.55
- DIHARD3 with four or fewer speakers: 14.84

Those evaluations include overlap. A roughly one-second latency configuration is slightly less accurate. Performance degrades above four speakers and on very long, noisy, or non-English recordings.

Multitalker Parakeet consumes Sortformer’s per-speaker activity and runs one ASR instance per speaker. Each instance hears the original mixture but focuses on one speaker. That means it can transcribe both speakers during complete crosstalk instead of merely labeling the dominant one. The price is compute: two speakers require two ASR paths, four require four.

If interruptions and crosstalk are the crux of your use case, this is the open local system I would evaluate on a private GPU server.

### VibeVoice, SoulX, TellWhisper, and other research

Microsoft’s **VibeVoice-ASR** is an 8B MIT-licensed model that processes up to 60 minutes in one pass and outputs words, speakers, and timestamps in 50+ languages. It is useful, but its authors explicitly acknowledge that serialized output does not properly handle simultaneous speakers: it tends to transcribe the dominant speaker and miss the secondary one. [Model](https://huggingface.co/microsoft/VibeVoice-ASR-HF), [overlap limitation](https://arxiv.org/pdf/2601.18184)

**SoulX-Transcriber** is an Apache-2.0 Chinese/English model built on Qwen3-Omni-30B-A3B. Its reported results are strong, but it is too heavy and immature to be the first system I would deploy. [Repository](https://github.com/Soul-AILab/SoulX-Transcriber)

**TellWhisper/Hyper-SD** and **TagSpeech** are important 2026 research. Both directly integrate speaker and time information into the speech encoder and report improvements on rapid turns and overlap. However, usable public checkpoints are not currently available, so they are research to watch rather than options for your implementation. [TellWhisper paper](https://aclanthology.org/2026.acl-long.861/), [TagSpeech paper](https://aclanthology.org/2026.acl-long.1938/)

**Audar-Diarization-V1** extends Sortformer from four to eight speakers. It is very new, has a custom community/enterprise license, and its headline benchmark uses a 250 ms collar while ignoring overlap. That makes its claimed advantage difficult to compare with overlap-inclusive results. [Audar model](https://huggingface.co/audarai/Audar-Diarization-V1)

## Superwhisper today

Superwhisper has improved considerably since your earlier test.

Its current local ASR choices include NVIDIA Parakeet V2/V3 and several Whisper variants up through large-v3/large-v3-turbo. These are genuinely on-device; audio does not leave the computer. [Current model list](https://superwhisper.com/models)

For diarization:

- Offline speaker separation has worked with every ASR model since October 2024.
- July 2025 brought faster diarization and improved speaker/timestamp accuracy.
- October 2025 brought “major diarization improvements.”
- The current macOS version is 2.16.6, released July 22, 2026. [Changelog](https://superwhisper.com/changelog)

However, its own documentation says that although every voice model supports speaker separation, the cloud **Nova** models provide the most accurate and reliable results. [Speaker-separated meetings guide](https://superwhisper.com/docs/modes/speaker-separated-meetings)

My interpretation:

- Superwhisper’s offline diarization is a separate internal engine, not a new capability inside Whisper or Parakeet.
- Superwhisper does not disclose which diarization model it uses.
- It publishes no DER, cpWER, tcpWER, speaker-count, or overlap benchmark.
- Its recommendation of cloud Nova implies its local combination still does not match its best cloud path.
- Its documentation does not say whether Nova file transcription now requests Deepgram `diarize_model=v2`.

Therefore, **retest it**, because there have been real improvements. But treat it as a convenient application and comparison point—not as an evidence-backed SOTA engine. For its Nova mode, ask Superwhisper whether it explicitly sends `diarize_model=v2` or `latest`. If not, its result may still be using Deepgram V1.

MacWhisper is another useful GUI comparator and supports local speaker grouping, but likewise does not disclose a diarization model or publish benchmarks. [MacWhisper speaker recognition](https://docs.macwhisper.com/article/32-automatic-speaker-recognition-in-macwhisper)

## Services that may beat Deepgram

### AssemblyAI Universal-3.5 Pro

This is the strongest current service challenger. AssemblyAI reports average cpWER of:

- Universal-3.5 Pro: 30.17
- ElevenLabs Scribe v2: 35.26
- Gladia: 36.87
- Voxtral Mini Transcribe V2: 37.52
- Deepgram Nova-3 English: 37.92
- Soniox v5: 44.58

The benchmark includes AMI, CALLHOME, DiPCo, and NOTSOFAR. Universal-3.5 Pro jointly predicts transcript content and speaker changes rather than aligning two independent streams. That architecture is particularly relevant to your short-turn and interruption problem.

The unresolved issue is Deepgram’s configuration. AssemblyAI identifies the competitor as “Nova-3 English” but does not disclose `diarize_model=v2`. Since `diarize=true` silently selects V1, I would not accept the ranking until you rerun both using explicit Deepgram V2.

### ElevenLabs Scribe v2

Scribe v2 supports 90+ languages, word timestamps, up to 32 speakers, keyterm prompting, and optional speaker libraries/known-speaker roles. [ElevenLabs STT documentation](https://elevenlabs.io/docs/overview/capabilities/speech-to-text)

It is worth including in your bakeoff. AssemblyAI’s benchmark places it second overall and ahead of Deepgram’s tested configuration, though it performs unevenly across meeting and far-field sets.

### OpenAI GPT-4o Transcribe Diarize

Include this because the known-speaker reference clips may substantially improve attribution when participants are known. There is not enough public benchmark data to call it a leader, and it remains API-only.

### pyannote Precision-2

Precision-2 is a premium diarization engine rather than a complete ASR system. Pyannote reports that it is 28% more accurate on average than Community-1, with significant improvements on CALLHOME, DIHARD3, AMI, and RAMC. It supports confidence scores, voiceprints, speaker identification, and enterprise self-hosting. [Precision-2 comparison](https://docs.pyannote.ai/models)

If speaker segmentation is more important than using one unified vendor, combining Precision-2 with your preferred ASR may beat general-purpose transcription APIs. It deserves a place in the evaluation.

### Speechmatics and Soniox

Speechmatics remains attractive for multilingual and private deployments, particularly its new local CoreML product. Soniox v5 is a worthwhile multilingual/code-switching dark horse. Neither publishes enough reproducible current diarization data to rank above the primary candidates.

### Descript

Descript automatically detects voices and provides an excellent human correction interface. It can remember labels as a project is edited. [Descript speaker detection](https://help.descript.com/hc/en-us/articles/10249423506061-Detect-and-label-speakers-in-your-transcript)

It does not disclose its underlying diarization model, publish serious benchmarks, or provide a local/private model stack. I would consider it as a review/editor experience, not as the engine around which to build your pipeline.

## The most important architectural distinction: diarization is not overlap transcription

Four different capabilities are often conflated:

- **Diarization:** when each anonymous speaker was active.
- **Speaker identification:** mapping an anonymous cluster to a known person.
- **Speaker-attributed ASR:** assigning recognized words to speakers.
- **Speech separation/multitalker ASR:** recovering what both people said simultaneously.

A system can have excellent DER and still lose one speaker’s words during overlap. Conversely, an end-to-end system can assign most words correctly while producing imprecise turn boundaries.

This is why I would not select a winner using WER or DER alone. Your main metric should be **cpWER**, supplemented with **tcpWER** and overlap-specific tests.

## The best implementation approach for your use case

For maximum private batch quality, I would build a hybrid “joint model plus acoustic verifier” pipeline:

1. **Preserve separate channels whenever possible.** If Zoom, a recorder, or the conferencing system can provide one track per participant, keep them separate. This removes most of the diarization problem and is more valuable than swapping models.

2. **Primary transcript:** run MOSS-Transcribe-Diarize on the full conversation. On a Mac-only workflow, start with Tiron.

3. **Independent diarization:** run pyannote Community-1 regular and exclusive outputs. For research evaluation, substitute DiariZen; for enterprise, trial Precision-2.

4. **Word alignment:** run forced alignment so each word has reliable start/end times. WhisperX’s alignment component is useful even if WhisperX is not the final diarizer.

5. **Map speaker namespaces:** use total time overlap plus speaker embeddings and a Hungarian assignment to map MOSS/Tiron speaker labels onto acoustic diarization clusters.

6. **Use acoustic evidence for boundaries and joint-model evidence for attribution.** Prefer the diarizer for exact turn starts/ends; prefer MOSS/Tiron where timestamp alignment would obviously assign a complete phrase to the wrong person.

7. **Handle overlap separately.** Mark regions where regular diarization has multiple speakers. If preserving both speakers’ words matters, send only those regions through Multitalker Parakeet or a target-speaker ASR path.

8. **Apply conservative smoothing:** merge micro-segments, add speaker-change hysteresis, and prevent a speaker from flipping for a single low-confidence word. Do not smooth away legitimate “yeah,” “right,” and other backchannels.

9. **Use an LLM only for punctuation, names, and formatting.** Do not let it invent speaker reassignment without acoustic evidence.

10. **Expose uncertainty:** flag low speaker confidence, model disagreement, unexpected speaker count, heavy overlap, and label fragmentation for human review. This is how you get close to “a human cannot improve much” without pretending the model is infallible.

## How I would run the bakeoff

Use at least 5–10 hours of your actual material, divided into:

- Clean two-person conversations.
- Similar-sounding speakers.
- Rapid back-and-forth and short acknowledgments.
- Far-field/noisy rooms.
- Phone/online calls.
- Three-to-eight-person groups.
- Deliberately overlap-heavy segments.
- Speakers who disappear and return much later.

Score:

- DER with zero collar and overlap included.
- JER.
- cpWER.
- tcpWER.
- Speaker-count error.
- Speaker fragmentation and incorrect merging.
- Backchannel attribution.
- Overlap recall and transcription of the quieter speaker.
- Human correction time per audio hour.
- Blind human preference.

Run this shortlist:

**Local/private**

- MOSS-Transcribe-Diarize.
- Tiron.
- WhisperX or your best ASR + pyannote Community-1.
- DiariZen + the same ASR, evaluation-only if commercial.
- NVIDIA Sortformer + Multitalker Parakeet.
- Speechmatics On-Device pilot.

**Cloud reference points**

- Deepgram Nova-3 with explicit `diarize_model=v2`.
- AssemblyAI Universal-3.5 Pro.
- ElevenLabs Scribe v2.
- OpenAI GPT-4o Transcribe Diarize.
- Pyannote Precision-2 plus your best ASR.

Pin every exact model revision and parameter. Do not benchmark anything using an ambiguous `latest`, except as a separate rolling-production test.

## Final verdict

If I were beginning your push today:

- I would deploy **MOSS-Transcribe-Diarize on a private NVIDIA server** as the primary new challenger.
- I would retain **pyannote Community-1** as an independent acoustic segmentation track and forced-alignment source.
- I would use **NVIDIA Multitalker Parakeet selectively on overlap regions**.
- I would run **Tiron locally on the Mac** because it is the easiest serious new Apple-Silicon candidate.
- I would immediately rerun **Superwhisper offline diarization**, but I would not rely on it until it beats the transparent stacks on your corpus.
- I would benchmark **AssemblyAI Universal-3.5 Pro against Deepgram Nova-3 with `diarize_model=v2` explicitly set**.
- If you want a supported Mac deployment instead of maintaining models, I would request a **Speechmatics On-Device** evaluation license.

The strongest likely final system is not one model. It is a joint speaker-aware transcription model, checked against a dedicated acoustic diarizer, with special handling for overlap and a review queue driven by disagreement.

## TL;DR

- Open-source Whisper still does **not** include diarization. OpenAI’s diarized model is API-only.
- Deepgram’s new flag is `diarize_model=latest` or `diarize_model=v2`; `diarize=true` still uses V1.
- Best new local batch candidate: **MOSS-Transcribe-Diarize 0.9B**.
- Best new Apple-Silicon candidate: **Tiron**.
- Best mature open commercial diarizer: **pyannote Community-1**.
- Best research diarizer: **DiariZen v2**, but its weights are noncommercial.
- Best streaming/overlap system: **NVIDIA Sortformer v2.1 + Multitalker Parakeet**.
- Best turnkey local Mac product to trial: **Speechmatics On-Device**.
- Best API challenger to Deepgram: **AssemblyAI Universal-3.5 Pro**, but its Deepgram benchmark may not have used V2.
- Superwhisper has improved substantially and now supports local diarization with all models, but it does not disclose or benchmark its diarizer.
- For the highest quality, use **MOSS/Tiron + pyannote/DiariZen + forced alignment + explicit overlap handling**, rather than trusting a single output.


# Claude (Fable5 High) response - diarization landscape
**State of the Art in ASR + Speaker Diarization for Multi-Speaker Conversations (July 2026)**

## TL;DR
- **Best local free stack:** Whisper/Parakeet (via `mlx-whisper` or `whispermlx`/WhisperX on Apple Silicon) for the transcript + **pyannote.audio 4.0 with the `community-1` pipeline** for diarization, reconciled using community-1's new *exclusive speaker diarization* output. This is the strongest fully-free, local, conversation-focused stack and runs on your MacBook Pro.
- **Best self-hosted paid option:** **pyannoteAI Precision-2** (self-hosted enterprise license, or its hosted API at €0.096–0.112/hr). It is the measured diarization accuracy leader — an independent ETH Zurich study puts the pyannoteAI API at 11.2% DER, best of any system tested — and is ~28% more accurate than the free community-1 model.
- **Best API alternative to Deepgram:** **AssemblyAI Universal-3.5 Pro** for joint transcription+diarization (30.17% cpWER vs Deepgram Nova-3's 37.93% on AssemblyAI's own benchmark), *or* **pyannoteAI Precision-2** as a pure-diarization specialist to pair with your existing Deepgram/local ASR. **Skip:** superwhisper's diarization, Descript-as-an-API, Google STT diarization, and streaming-only Sortformer for offline long-form work.

## Key Findings
1. **Whisper still has no native diarization.** Local Whisper outputs text + timestamps only; you must add a separate diarizer. In 2026 OpenAI shipped a hosted `gpt-4o-transcribe-diarize` model, but that is a cloud API product, not part of local Whisper.
2. **pyannote.audio 4.0 + `community-1` is the new open-source baseline** — materially better than the old 3.1 pipeline on speaker counting/assignment — and it adds an *exclusive speaker diarization* output built specifically to fix STT-timestamp reconciliation, which is exactly the pain point in your use case.
3. **pyannoteAI Precision-2 is the accuracy king.** An independent ETH Zurich benchmark measured the pyannoteAI (Precision-2) API at the best 11.2% DER, ahead of all open-source competitors.
4. **NVIDIA's ecosystem is powerful but NVIDIA-GPU-centric and 4-speaker-capped** for its Sortformer diarizer and joint multitalker-Parakeet ASR. Great on a rented GPU; awkward on a Mac and unsuitable as-is for 5–6 speaker meetings.
5. **On APIs, AssemblyAI now beats Deepgram on diarization** by its own head-to-head cpWER benchmark; ElevenLabs Scribe v2, Speechmatics, and Gladia are credible but their diarization claims are largely self-reported.
6. **superwhisper's diarization remains weak** (it's fundamentally a dictation app); better on-device Mac diarization now exists in apps like Resonant (on-device Sortformer) and open tools (senko, scribe, macparakeet).

## Details

### 1. Local / Open-Source State of the Art

**Whisper native diarization — confirmed status:** None. Local OpenAI Whisper produces transcript + segment/word timestamps but no speaker labels; diarization (speaker embedding + clustering) is a separate task requiring a separate model family. OpenAI's 2026 `gpt-4o-transcribe-diarize` is a hosted API, not local.

**pyannote.audio 4.0 + `community-1`:** Released September 2025, `community-1` is the current open-source SOTA diarization pipeline. Licensed **CC-BY-4.0** (free for research and commercial use; gating on Hugging Face exists for usage tracking, not payment). It is gated — accept the model conditions and authenticate with a free HF token — and supports **fully offline use** after a one-time `git clone` of the repo. It exposes `num_speakers`, and `min_speakers`/`max_speakers` hints to constrain speaker counting. Architecture: powerset multi-class segmentation + WeSpeaker embeddings + **VBx (Bayesian HMM x-vector) clustering**.

DER (reported under a **strict protocol: fully automatic, no forgiveness collar, no skipping overlap**) vs the legacy 3.1 pipeline and commercial Precision-2:

| Benchmark | legacy 3.1 | community-1 | precision-2 |
|---|---|---|---|
| AMI (IHM) | 18.8 | 17.0 | 12.9 |
| AMI (SDM) | 22.7 | 19.9 | 15.6 |
| CALLHOME (part 2) | 28.5 | 26.7 | 16.6 |
| DIHARD 3 (full) | 21.4 | 20.2 | 14.7 |
| MSDWild | 25.4 | 22.8 | 17.3 |
| VoxConverse (v0.3) | 11.2 | 11.2 | 8.5 |
| AliMeeting (ch1) | 24.5 | 20.3 | 15.2 |
| RAMC | 22.2 | 20.8 | 10.5 |
| AISHELL-4 | 12.2 | 11.7 | 11.4 |

The headline new feature: **exclusive speaker diarization** (`output.exclusive_speaker_diarization`), per the community-1 model card, "backported from our latest commercial model that simplifies the reconciliation between fine-grained speaker diarization timestamps and (sometimes not so precise) transcription timestamps." This directly addresses your requirement for clean reconciliation of diarization with word-level transcript timestamps and clean handling of overlap/backchannels.

**Running on Apple Silicon (MPS) vs NVIDIA:** pyannote runs on CPU by default; `pipeline.to(torch.device("cuda"))` for NVIDIA. MPS (Apple GPU) support is partial and historically has "hung" or silently fallen back to CPU for some ops. On a MacBook Pro, expect diarization to run largely on CPU — usable for offline batch (order of a few minutes of compute per hour of audio) but noticeably slower than an NVIDIA GPU. For reference, self-hosted Precision-2 on an H100 runs ~14s per hour of audio; community-1 ~31s/hr on AMI-class files on the same hardware.

**pyannoteAI Precision-2 (commercial):** ~28% more accurate than community-1 on average; ~14% better than Precision-1; and pyannoteAI/Picovoice framing states the commercial model "achieves 28% lower DER than pyannote 3.1 (open-source) on the same benchmarks." The strongest independent evidence: ETH Zurich's **arXiv 2509.26177, "Benchmarking Diarization Models" (Sept 2025)**, which evaluated five SOTA diarizers across four datasets (196.6 hours, five languages) and concluded verbatim: *"Overall, we find that PyannoteAI achieves the best performance at 11.2% DER, while DiariZen provides a competitive open-source alternative at 13.3% DER... the primary cause of diarization errors stem from missed speech segments followed by speaker confusion."* Note this independent study compared pyannoteAI only against open-source models, not Deepgram/AssemblyAI.

Hosted pricing: **€0.035/hr** (community-1 hosted), **€0.096/hr** (Precision-2, Starter plan), **€0.112/hr** (Precision-2, Developer plan). Plans: €19/mo (Developer, 125 hrs), €99/mo (Starter, 825 hrs, 3 concurrent seats/jobs), Enterprise custom **with self-hosted Precision-2 deployment**. Precision-2-only extras: speaker identification, voiceprinting (€0.015 each), exclusive-diarization mode, confidence scores. Free trial: 150 hours for 30 days, no credit card. Public customers include Descript, Gladia, Synthesia, HeyGen, and Abridge.

**NVIDIA NeMo ecosystem:**
- **Streaming Sortformer 4spk v2 / v2.1:** end-to-end neural diarizer using an **Arrival-Order Speaker Cache (AOSC)**; FastConformer/NEST encoder (17 layers) + 18-layer transformer. **Hard 4-speaker maximum**; performance degrades at 5+. v2.1 adds robustness for meeting speech. DER with overlap: DIHARD III eval (1–4 spk) ~13.24–14.76%; CALLHOME-part2 all-speaker ~13.32% (streaming AOSC, beating prior streaming EEND systems). Even at 0.32s latency, degradation is modest (~19.3% DIHARD, ~11.5% CALLHOME). Offline Sortformer is limited to ~12 min per pass on a 48GB RTX A6000 due to quadratic attention memory. Requires NVIDIA NeMo + PyTorch and effectively assumes an NVIDIA GPU (though a `parakeet-rs` ONNX port runs Sortformer v2/v2.1 on CPU/WebGPU).
- **multitalker-parakeet-streaming-0.6b-v1:** a 600M-param RNNT joint multitalker ASR that consumes Sortformer's diarization output as conditioning ("speaker kernel injection" into the FastConformer pre-encode layer). It runs **one model instance per detected speaker**, so it transcribes accurately even during fully overlapped speech, with no speaker enrollment required. Best-in-class overlap handling — but NVIDIA/NeMo-centric.
- **Canary-Qwen-2.5B:** tops the Hugging Face Open ASR Leaderboard at **5.63% average WER** (released July 17, 2025; CC-BY-4.0; SALM architecture pairing a FastConformer encoder with an unmodified Qwen3-1.7B LLM decoder; trained on ~234K hours; RTFx ~418). English-only, and slower than Parakeet. It is **pure ASR, not a diarizer** — followed by IBM Granite Speech 3.3 8B (~5.85% WER) and Microsoft Phi-4 Multimodal.
- **Parakeet TDT 0.6B v2/v3:** throughput leaders (RTFx in the thousands, e.g. v2 ~3,386), CC-BY-4.0; v3 is multilingual (25 European languages, auto language ID). The best ASR to pair with a separate diarizer when speed matters.

**WhisperX and related pipelines:**
- **WhisperX** (m-bain) remains the reference recipe: faster-whisper backend + wav2vec2 forced alignment for word-level timestamps + pyannote diarization + VAD. Actively maintained; an MLX backend has been contributed for Apple Silicon (reported ~4.4× speedup).
- **whispermlx** (KalebJS, released June 2026): a WhisperX fork with the inference backend replaced by mlx-whisper, running natively on Apple Silicon via MLX. Retains word-level timestamps (wav2vec2 forced alignment), VAD, and diarization — and it **requires acceptance of the `speaker-diarization-community-1` agreement**, i.e. it is on the new pyannote 4.0 line. This is the most convenient one-tool MLX-native Whisper+diarization option for your Mac.
- **mlx-whisper** is the fast default on M-series (Metal + unified memory). **faster-whisper** (CTranslate2) has no Metal backend, so on Mac prefer mlx-whisper.
- Community repos **parakeet-diarized** and **parakeet-v3-diarized** wrap Parakeet 0.6B (v2/v3) + pyannote behind a Whisper-style API.

**Newer end-to-end / joint speaker-attributed ASR models (2025–2026):**
- **DiCoW (Diarization-Conditioned Whisper)**, BUT Speech@FIT (Computer Speech & Language, 2026): injects frame-level diarization signals into Whisper's encoder for target-speaker/speaker-attributed ASR. On NOTSOFAR-1 it reduces ORC-WER ~11% absolute vs separation/diarization cascades; with ground-truth diarization its cpWER/ORC-WER/tcWER beat standard Whisper and speaker-embedding systems. Follow-ups: **SE-DiCoW** (Self-Enrolled, ICASSP 2026) and **SA-DiCoW** (serialized output training, models up to 8 speakers). Uses DiariZen as the front-end diarizer; CC-BY-4.0. Real-world performance is bounded by upstream diarization quality (missed speech propagates).
- **DiariZen** (BUT-FIT): hybrid EEND + WavLM embeddings + pyannote clustering; the best open-source system in the ETH benchmark at 13.3% DER.
- Other ASR releases relevant as *transcript engines* (not diarizers): **Mistral Voxtral**, **IBM Granite Speech 3.3 8B**, **Microsoft Phi-4 Multimodal**, **Qwen3-ASR**, **Kyutai** streaming STT, **Rev Reverb**.

**Best local recipe for maximum diarization quality on 2–6 speaker conversations:**
1. **Transcript:** mlx-whisper large-v3 (accuracy) or Parakeet TDT v3 (speed) on Apple Silicon, with VAD to skip silence and reduce hallucination.
2. **Diarization:** pyannote.audio 4.0 `community-1`, passing `min_speakers`/`max_speakers` (or `num_speakers` when known) to constrain speaker counting.
3. **Reconciliation:** use community-1's **`exclusive_speaker_diarization`** output to assign each word to exactly one speaker, resolving overlap zones deterministically against the word-level timestamps.
4. **Overlap handling:** community-1/Precision-2 model overlap directly; for heavy overlap, the NVIDIA multitalker-Parakeet path (per-speaker instances) is stronger but needs an NVIDIA GPU.
5. **Hardware:** the full Whisper+pyannote stack runs on a MacBook Pro (M-series, 16GB+ recommended), roughly a few× real-time for offline batch. For Precision-2-class quality, Sortformer + multitalker-Parakeet, or large-batch throughput, rent an NVIDIA GPU (A6000/H100), where diarization drops to ~14–31s per hour of audio.

### 2. macOS Apps

**superwhisper (2026):** Offers local Whisper + Parakeet (incl. Parakeet Realtime, added Jan 2026) plus cloud (Deepgram, ElevenLabs Scribe, Gemini, Grok). It added speaker-name editing and file-transcription with diarization, but diarization is a secondary feature and — consistent with your past experience — is not its strength; it is fundamentally a dictation app. Pro is $8.49/mo or $249.99 lifetime. **Verdict: keep it for dictation, don't rely on it for serious diarization.**

**MacWhisper:** File-transcription-focused; Whisper + Parakeet; has pyannote-based diarization. Solid for file transcripts, but built around file workflows rather than live use.

**Newer local-first diarization apps (the ones doing it well):**
- **Resonant (onresonant.com):** free, 100% on-device, uses **NVIDIA Sortformer diarization on Apple Silicon** (via FluidAudio/CoreML) with dual-channel recording (mic + system audio on separate channels), plus Parakeet TDT v3 / Qwen3-ASR for ASR (<4% WER claimed on English). The clearest example of "diarization done well on-device" on a Mac.
- **MacParakeet / macparakeet (open source, GPL-3.0):** Parakeet TDT on the Apple Neural Engine via FluidAudio, with diarization; ~53–79s per hour of audio total (ASR ~23s + diarization ~30–56s), exclusive-output overlap trimming, and stable S1/S2 speaker IDs.
- **senko:** a very fast diarization pipeline (modified Alibaba 3D-Speaker), CoreML on Mac — ~1 hr of audio in **7.7s on an M3**; 13.5% DER on VoxConverse, 26.5% on AMI-IHM. Pairs with the **Zanshin** media player for visualization.
- **scribe (Trail of Bits):** a local CLI combining senko + parakeet-mlx into speaker-attributed transcripts on Apple Silicon.
- **Spokenly:** free local Parakeet/Whisper + BYOK cloud; **FluidAudio** is the underlying Swift/CoreML framework several of these apps use for on-device Parakeet + diarization.

### 3. Third-Party API Services

**Deepgram (your baseline):** Nova-3 is the flagship (Flux is a separate voice-agent turn-taking model). Diarization via `diarize=true`; it detects speaker count automatically with no documented maximum. Deepgram's diarization is honest but weaker on overlapping speech and crowded multi-party audio, and it does not do speaker *identification* (only separation). Pricing: batch $0.0043/min, streaming $0.0077/min. Claimed 5.26% batch WER; independent tests measure 7–10% real-world.

**AssemblyAI (beats Deepgram on diarization):** Universal-3.5 Pro (pre-recorded, $0.21/hr) solves transcription and diarization *jointly* rather than bolting on a separate diarizer. AssemblyAI's public /benchmarks page reports **average cpWER across DiPCo, CALLHOME, NOTSOFAR, and AMI** as: **AssemblyAI Universal-3.5 Pro 30.17%**, Azure 30.35%, ElevenLabs Scribe V2 35.26%, Speechmatics 36.60%, Gladia 36.88%, Mistral Voxtral 37.52%, **Deepgram Nova-3 37.93%**, Grok 42.58%, Google 50.64%, Soniox 114.81% (Soniox is an outlier, almost certainly a normalization artifact). Per-dataset, Universal-3.5 Pro vs Deepgram: CALLHOME 17.18% vs 23.70%; NOTSOFAR test 37.02% vs 48.24%; AMI 27.36% vs 29.28%; DiPCo 33.48% vs 38.31%. A streaming diarization upgrade claims 66% fewer false-alarm speakers and per-word speaker labels; `max_speakers` supports 1–10. This is the clearest "beats Deepgram on diarization" evidence, though it is vendor-published.

**pyannoteAI Precision-2 API (pure-diarization specialist):** the measured accuracy leader. Pair it with any ASR (keep Deepgram/Whisper for the words, swap in world-class diarization for the speakers). Best choice if you want to change only the diarization layer.

**ElevenLabs Scribe v2 / Scribe v2 Realtime:** Scribe v2 (batch) does diarization for up to 32–48 speakers and claims 98% speaker-label accuracy; Scribe v2 Realtime (~150ms) has **no diarization**. Diarization quality claims are self-reported; on AssemblyAI's benchmark Scribe V2 was 35.26% cpWER (behind AssemblyAI and Azure). Files up to 3 GB / 10 hours.

**Speechmatics (Melia-1 / Ursa):** Melia-1 led an independent aggregate-WER test at 6.4% (VexaScribe, July 2026, 14 models); its Enhanced tier claims strong broadcast diarization (~8.6% VoxConverse DER). On AssemblyAI's cpWER benchmark Speechmatics was 36.60%. Offers on-prem deployment.

**Gladia (Solaria-1/3):** bundles diarization at no extra cost; self-reports "3× lower DER" on conversational speech, sub-103ms partials, 100+ languages, ~$0.55/hr. Independent verification is lacking. 36.88% cpWER on AssemblyAI's benchmark. Real-time diarization is not yet production for Gladia (batch/async only).

**Soniox, Rev AI (Reverb), Google Chirp 3, Azure, AWS Transcribe:** all offer diarization. On AssemblyAI's cpWER table Azure was strong (30.35%) and Google weak (50.64%). Picovoice's independent "State of Speaker Diarization in 2026" found Big Tech DER spanning **11.1% (Amazon) to 50.2% (Google)**; its Falcon VoxConverse JER comparison lists Falcon 19.9% ahead of pyannote 27.4%, Amazon 29.8%, Azure 30.1%, and Google Enhanced 57.6%.

**Descript:** an editor/app, not a serious diarization API — not relevant to your API-integration workflow.

### 4. Benchmarks and Evaluation

**Standard conversational DER (leading systems; note the protocols differ):**
- **community-1 (open):** AMI-IHM 17.0, DIHARD3 20.2, CALLHOME 26.7, VoxConverse 11.2 (strict: no collar, overlap included).
- **Precision-2:** AMI-IHM 12.9, DIHARD3 14.7, CALLHOME 16.6, VoxConverse 8.5 (same strict protocol); ~11.2% aggregate DER in independent ETH testing.
- **Sortformer v2 streaming:** DIHARD3 ~13–15%, CALLHOME ~13.3% (≤4 speakers, with overlap; 0.25s collar on CALLHOME/CH109, 0s on DIHARD).
- **DiariZen (open):** ~13.3% aggregate DER (ETH benchmark).
- **pyannote 3.1 (legacy reference):** DIHARD III ~21.7%, AMI ~18.8%, VoxConverse ~11.2%.

**Crucially, evaluation conditions dominate the numbers.** The forgiveness collar (0 vs 0.25s) and whether overlapping speech is scored swing DER by many points. pyannote's own table uses the *strict* no-collar/overlap-included protocol, so its numbers look worse than collar-based vendor claims for the *same* model. Always compare within one protocol.

**Metrics beyond DER for your "who said what" goal:**
- **DER** = (missed + false-alarm + speaker-confusion) / total speech — segmentation only.
- **JER** (Jaccard error rate) — per-speaker balanced view.
- **WDER / cpWER / tcpWER / ORC-WER** — jointly score words *and* speaker attribution. **cpWER (concatenated minimum-permutation WER) is the right top-line metric for your goal** and is the standard used by AssemblyAI, CHiME, and the DiCoW line; tcpWER adds time constraints.
- **Missed-entity rate** for high-value tokens (names, numbers, IDs) where downstream workflows fail first.

**Building your own eval harness:**
1. Hand-label 3–5 representative recordings of your real audio (RTTM for diarization; speaker-tagged transcript for cpWER).
2. Use **pyannote.metrics** for DER/JER — set the collar and `skip_overlap` explicitly, and report both a strict (0 collar, overlap included) and a lenient (0.25s collar) variant.
3. Use **meeteval** for cpWER/tcpWER/ORC-WER (the multi-talker ASR standard).
4. Explicitly probe overlap, backchannels, and correct speaker counting; report speaker-count confusion as a separate line item.
5. Always test on YOUR audio — the accuracy spread between top systems on your specific recordings will exceed the leaderboard spread and may reorder the models.

## Recommendations

**Stage 1 — Build the free local stack first (this week):**
- Install `pyannote.audio` 4.0, accept the `community-1` HF gate, and run **mlx-whisper large-v3 + community-1** on your MacBook Pro. Use `exclusive_speaker_diarization` for word-to-speaker mapping and pass `min_speakers=2, max_speakers=6`.
- Alternatively, use **whispermlx** to get WhisperX-style word alignment + community-1 diarization in one MLX-native tool.
- Benchmark it on your own labeled audio with pyannote.metrics (DER) + meeteval (cpWER). This establishes your baseline and is likely already better than anything you've run before.

**Stage 2 — If community-1 isn't "human-level" on your hardest audio:**
- Add **pyannoteAI Precision-2** (hosted API, €0.096/hr) as a one-line drop-in swap and re-measure. If the cpWER/DER gain justifies it, this is your best paid diarizer, and it lets you keep ASR local (or on Deepgram) while upgrading only the diarization layer.
- For strict data-locality, negotiate the **self-hosted Precision-2 enterprise** license.

**Stage 3 — For overlapping/multi-party audio or high throughput:**
- Spin up a rented **NVIDIA GPU (A6000/H100)** and run **Sortformer v2.1 + multitalker-Parakeet** (≤4 speakers) for overlap-robust speaker-attributed transcription, or run **Precision-2 self-hosted** for 5–6+ speaker meetings.

**On APIs vs Deepgram:**
- For a single API that beats Deepgram's diarization, move to **AssemblyAI Universal-3.5 Pro** (joint diarization, ~20% relative cpWER improvement over Nova-3 on AssemblyAI's benchmark).
- To keep Deepgram for words, bolt on **pyannoteAI Precision-2** for diarization.

**Thresholds that would change these recommendations:**
- If measured **cpWER on your audio with community-1 is within ~2–3 points of Precision-2**, stay free/local.
- If you routinely have **>4 simultaneous speakers or heavy overlap**, prefer Precision-2 or the NVIDIA multitalker path over Sortformer (which is hard-capped at 4 speakers).
- If you need **real-time** diarization, only Sortformer-streaming, AssemblyAI streaming, or Deepgram apply — pyannote/Precision-2 are batch, and ElevenLabs Realtime/Gladia realtime currently lack diarization.

**What to skip:** superwhisper diarization (weak), Descript-as-an-API, Google STT diarization (worst DER in independent tests), and streaming-only tools for offline long-form work.

## Caveats
- **Vendor benchmarks dominate the API comparisons.** The Deepgram-vs-AssemblyAI cpWER numbers are AssemblyAI's own; pyannoteAI's "beats Deepgram/AssemblyAI" claim is on its own benchmark (per-provider DER values there are published only as images and could not be independently extracted). The one strong *independent* number — ETH Zurich's 11.2% DER for pyannoteAI — compares only against open-source models, not Deepgram/AssemblyAI. No single independent benchmark places Deepgram, Precision-2, and AssemblyAI in one table with exact numbers.
- **DER/cpWER numbers are protocol-sensitive.** Collar (0 vs 0.25s) and overlap handling change results by many points; compare only within the same protocol, and prefer your own harness for decisions.
- **Apple Silicon GPU (MPS) support for pyannote is imperfect** — expect CPU fallback for parts of the pipeline and slower-than-CUDA throughput. FluidAudio/CoreML-based tools (senko, Resonant) are the more mature "on-device accelerated" route on Mac, but they use different (often lighter) diarization models than pyannote 4.0, so re-benchmark accuracy before switching to them for quality-critical work.
- **Several 2026 WER/latency figures come from vendor pages and SEO aggregator sites of variable reliability** (e.g., VexaScribe/NovaScribe, elevenlabsmagazine). Treat single-source claims cautiously and re-verify on your data.
- **Sortformer and its multitalker-Parakeet partner are hard-capped at 4 speakers** — unsuitable as-is for 5–6 speaker meetings; use Precision-2 or community-1 there.
- **DiCoW-family joint models depend heavily on upstream diarization quality** — with real (not ground-truth) diarization, missed-speech errors propagate and inflate WER, so they are research-grade rather than turnkey for your use case today.


# Prompt 2 - metrics and benchmarks
Okay, so I want to hone in now on the evaluations for diarization and I want you to explain what the key metrics are and then what the key benchmarks are and what data sets those benchmarks use. How large are those data sets? What kind of content are they? I'm assuming the raw form of those is audio You know what types of meetings or conversations are they from how long are those? How many speakers do they have? How many files in total? And what is involved with the data sets or benchmarks in terms of being kind of de novo or one-off versus being a set? Do any of them involve performance on a set? Of files that is for say like an organization's that have you know where this speaker where it has You know overlapping or the same Speakers and Then a key thing I'm wondering is if you know Do any of the processes code or benchmarks involve? like propagating Extracting into a propagating Changes made to a transcript That involves diurization to two other ones Because part of my thesis is it that If you have a human correct the diurized transcript then there's really valuable information that they can then be propagated and used by AI to greatly improve the quality of In a cleanup step for other ones In in a corpus.

# ChatGPT (5.6 Sol Extra High) response - metrics and benchmarks
The central finding is that diarization evaluation has three distinct levels, and most leaderboards measure only the first:

1. **Per-recording segmentation:** Did the system divide this recording among anonymous speakers correctly?
2. **Speaker-attributed transcription:** Did it recover who said which words, including overlap?
3. **Longitudinal corpus intelligence:** Does it recognize the same person across recordings and improve after human correction?

DER and most established benchmarks cover level 1. Newer metrics such as tcpWER cover level 2. Your idea—using corrected transcripts to improve other recordings in a collection—is level 3. There is credible research supporting it, but almost no mainstream benchmark measures the complete workflow.

## 1. The key diarization metrics

| Metric | What it measures | Important blind spot |
|---|---|---|
| **DER** | Speaker-time assigned incorrectly | Usually allows speaker identities to be remapped independently in every recording |
| **JER** | Per-speaker intersection-over-union error | Still session-local; says nothing about recognized words |
| **Purity / coverage** | Whether clusters merge different people or fragment one person | Does not directly measure timing or transcription |
| **WDER** | Percentage of recognized words attributed to the wrong speaker | Must be interpreted alongside WER |
| **cpWER** | Combined transcription and speaker-attribution error, after optimally permuting speaker labels | Discards temporal order within each speaker’s concatenated transcript |
| **tcpWER** | Speaker-attributed WER with time constraints | More representative, but less universally reported |
| **DIR at FAR** | Correctly identifying enrolled speakers while rejecting unknown speakers | Requires persistent/global identities and enrollment audio |
| **Human correction effort** | Time or operations needed to produce a usable transcript | Rarely reported on conventional leaderboards |

### DER: the traditional core metric

Diarization Error Rate is:

\[
DER = \frac{Missed\ speaker\ time + False\ alarm\ time + Speaker\ confusion\ time}{Reference\ speaker\ time}
\]

- **Miss:** someone was speaking, but the system detected no speaker.
- **False alarm:** the system labeled speech where the reference says there was none.
- **Confusion:** speech was detected but assigned to the wrong speaker.

The mapping between anonymous output labels such as `SPEAKER_01` and reference speakers is found automatically to minimize error. That is sensible for a one-off recording—but it means a system receives no extra credit for knowing that `SPEAKER_01` in Monday’s meeting is the same person as `SPEAKER_03` on Wednesday.

Overlap makes DER especially important to interpret correctly. If two people speak simultaneously for one second, that is two reference speaker-seconds. A system that can output only one active speaker must miss at least one of them.

DER can also exceed 100% if the system generates enough false-alarm or duplicate-speaker time.

The [DIHARD III evaluation plan](https://catalog.ldc.upenn.edu/docs/LDC2022S12/third_dihard_eval_plan_v1.2.pdf) is one of the clearest formal definitions.

### The scoring collar problem

Many older results forgive errors within approximately 250 ms of each reference boundary. That is called a **collar**.

A 250 ms collar can make results look substantially better when conversations contain:

- fast turn-taking;
- backchannels such as “yeah” and “mm-hmm”;
- interruptions;
- adjacent speakers with almost no silence.

DIHARD uses **no collar** and evaluates overlapping speech. VoxSRC and M2MeT commonly use a 250 ms collar. Consequently, their published DER values are not directly interchangeable.

Every reported result should specify:

- collar duration;
- whether overlap is scored;
- whether speech detection is supplied or predicted;
- whether the true speaker count is supplied;
- whether the score is calculated per recording or over the total duration;
- microphone/channel condition;
- exact dataset release and split.

Without those, “DER 8%” is not a complete claim.

### JER

Jaccard Error Rate calculates an intersection-over-union error for each reference speaker and averages across speakers. Unlike ordinary aggregate DER, it gives a short-speaking participant similar weight to a dominant participant.

That is valuable for meetings where one person talks for 80% of the time and several people contribute only occasionally. A system can obtain a respectable aggregate DER while mishandling the quieter speakers.

DIHARD reports both DER and JER. Its [overview describes the scoring and domain composition](https://dihardchallenge.github.io/dihard3workshop/slide/DIHARD_III_Overview.pdf).

### Purity and coverage

These expose the two primary clustering failure modes:

- **Low purity:** a system cluster contains speech from several actual people. The system has merged speakers.
- **Low coverage:** one actual person has been split across several system clusters. The system has fragmented a speaker.

Typical interpretations:

- Too few output speakers → lower purity, higher coverage.
- Too many output speakers → higher purity, lower coverage.

These are particularly important for your use case. Fragmentation may produce a modest DER but make a transcript frustrating to edit because “Alice” appears under five different temporary speaker labels. The [pyannote metrics documentation](https://pyannote.github.io/pyannote-metrics/reference.html) defines these metrics and the standard diarization error components.

### WDER: word diarization error

Word Diarization Error Rate asks: among words that ASR recognized or substituted, how many were attributed to the wrong speaker?

The original formulation is approximately:

\[
WDER =
\frac{Correctly\ recognized\ words\ with\ wrong\ speaker +
Substitutions\ with\ wrong\ speaker}
{Correctly\ recognized\ words + Substitutions}
\]

It is closer to the transcript-editing experience than DER. But it excludes or handles ASR insertions and deletions imperfectly, so it must be reported with WER. A system cannot receive a meaningful speaker attribution for a word it never recognized. See the original [Interspeech WDER paper](https://www.isca-archive.org/interspeech_2019/shafey19_interspeech.pdf).

### cpWER and tcpWER

**Concatenated permutation WER**, or cpWER, concatenates all words attributed to each speaker, then finds the speaker-label permutation producing the lowest WER. It jointly penalizes:

- incorrect ASR;
- missing and inserted words;
- words assigned to the wrong speaker.

Its weakness is that concatenation discards local timing. A word can be attributed to the right person but placed in a temporally implausible part of the conversation.

**Time-constrained permutation WER**, or tcpWER, adds time compatibility. It therefore gets closer to “who said what when.” A recent attempt to unify these definitions is described in [MeetEval: A Toolkit for Computation of Word Error Rates for Meeting Transcription Systems](https://arxiv.org/abs/2508.02112); the earlier formal treatment is [Time-Constrained Minimum-Permutation WER](https://arxiv.org/abs/2211.16112).

For conversation transcription, I would consider tcpWER the best single primary metric—but still not sufficient by itself.

### Supporting metrics I would always report

For serious evaluation, add:

- output speaker-count absolute error;
- turn-boundary precision, recall and F1 at stated tolerances;
- boundary timing error;
- overlap-detection precision, recall and F1;
- DER and tcpWER specifically within overlap;
- short-turn/backchannel error;
- identity fragmentation and unintended merges;
- human correction minutes per audio hour;
- number of label changes, boundary edits and text edits required.

## 2. The major datasets and benchmarks

A “file” is ambiguous for multichannel corpora. One meeting may generate a headset file for every participant, six microphone-array files, video files and annotations. The meaningful benchmark unit is therefore usually the **session or recording**, not the raw WAV-file count.

### Core diarization datasets

| Dataset | Size and recordings | Speakers | Content and recording conditions | Cross-recording identity? |
|---|---:|---:|---|---|
| **DIHARD III** | Development: 254 recordings/34.15 h; evaluation: 259/33.01 h. Mostly 5–10 min | Approximately 1–10 per recording | Eleven difficult domains: meetings, telephone calls, clinical interviews, courtrooms, restaurants, field interviews, broadcast, web video and others; mono 16 kHz | Generally treated as recording-local |
| **AMI** | 171 meetings, approximately 100 h; average roughly 33–35 min | Usually 4; range approximately 3–5 | English product-design meetings; headset, lapel and microphone-array audio plus video | **Yes.** Global participant IDs and four-meeting series |
| **ICSI** | 75 meetings, approximately 72 h; average roughly 58 min | Average about 6; 53 unique participants | Natural recurring research-group meetings; headworn and tabletop microphones | **Yes.** Strong recurring-speaker structure |
| **CALLHOME diarization** | 500 short telephone recordings; common two-fold evaluation totals about 17 h | 2–7, usually two dominant speakers | Unscripted multilingual calls among family and friends; 8 kHz telephone audio | Ordinarily scored recording-locally |
| **AISHELL-4** | 211 Mandarin sessions, 120 h; 191 train/107.5 h and 20 evaluation/12.72 h; about 30 min each | 4–8; 60 unique speakers | Real meetings in ten rooms; eight-channel array plus headsets; business, education, medicine and everyday subjects | Nearly disjoint train/evaluation speakers |
| **AliMeeting / M2MeT** | Approximately 118.75 h; original release: 212 training sessions/104.75 h, 8 development sessions/4 h and 10 h hidden test; 15–30 min | 2–4 | Mandarin meetings in 13 rooms; array and headset audio; unusually heavy overlap | Train and evaluation speakers are disjoint |
| **VoxConverse** | 448 clips, approximately 63.8 h: 216 development/20.3 h and 232 test/43.5 h | 1–21; average about 5.5 | YouTube talk shows, panels, debates, news and interviews; edited, noisy, uncontrolled | Public figures can recur, but scoring is recording-local |
| **CHiME-6** | 20 dinner parties, approximately 50 h: 16 train, 2 development, 2 evaluation; at least 2 h each | Exactly 4 per party | Real friends cooking, eating and talking in homes; six four-microphone arrays plus binaural microphones | Participants persist within a party, not across the benchmark |
| **DiPCo** | 10 sessions, roughly 5.3 h; 15–47 min | 4 | Natural dinner-table conversations; five seven-microphone arrays plus close-talk | Small, session-local evaluation |
| **NOTSOFAR-1** | Original paper: 315 meetings, about 30 h; 20–60 min is not typical here—most clips are around 6 min. Current open release counts differ after legal/quality removals | 4–8; 35 unique people | Real English business-style meetings in 30 conference rooms; motion, distance variation, interruptions and overlap | **Yes, people recur**, although standard scoring is still session-local |
| **TST-Bench** | 300 synthetic sessions, approximately 200 h; 20–60 min | 8–30 per session; 350 total identities | Simulated noisy sessions built from English audiobook speech; known and unknown speakers | **Yes. Explicit global identity benchmark** |

Sources and important qualifications follow.

### DIHARD III: broad robustness benchmark

DIHARD is the best-known heterogeneous stress test. It deliberately mixes radically different acoustics and interaction types rather than representing one organization.

Its development and evaluation sets are divided into “full” and balanced “core” subsets. Scored regions are identified using UEM files, normally covering the recording except excluded private information. Reference annotation was unusually expensive—roughly 15–30 times real time—and boundaries were annotated with high temporal precision. See the official [DIHARD III plan](https://catalog.ldc.upenn.edu/docs/LDC2022S12/third_dihard_eval_plan_v1.2.pdf).

It tests generalization. It does not test organizational memory or learning from corrected earlier meetings.

### AMI: probably the most useful established meeting corpus

AMI contains about 100 hours across 171 meetings. Roughly two-thirds are scenario meetings in which a fictional product-development team conducts a sequence of four related meetings. The `a/b/c/d` meeting suffixes identify sessions in the same series.

AMI has:

- global participant IDs;
- speaker-aligned transcription;
- overlap annotations;
- dialogue acts, summaries and other metadata;
- synchronized close-talk, far-field and video recordings.

The official scenario split contains approximately 98 training, 20 development and 20 evaluation meetings; other widely used recipes use different selections, so “AMI DER” is incomplete without the split and microphone condition. See the [AMI corpus overview](https://groups.inf.ed.ac.uk/ami/corpus/overview.shtml), [meeting-series identifiers](https://groups.inf.ed.ac.uk/ami/corpus/meetingids.shtml) and [official dataset splits](https://groups.inf.ed.ac.uk/ami/corpus/datasets.shtml).

AMI is structurally well suited to your thesis. The limitation is that normal benchmark scoring throws away its cross-session identity structure.

### ICSI: the strongest older example of an actual organization

ICSI contains 75 naturally occurring research-group meetings rather than acted scenarios. They cover recurring teams working on speech recognition, meeting recording, language processing, networking and related research.

It has approximately:

- 72 hours;
- 53 unique participants;
- six participants per meeting on average;
- 15 “Even Deeper Understanding” meetings;
- 29 “Meeting Recorder” meetings;
- 23 “Robustness” meetings;
- several smaller series.

Many participants recur across weeks and across meeting series. That makes ICSI one of the best existing datasets for testing organization-level identity propagation. Its weakness is the absence of one current, universally followed global-identity leaderboard. See the original [ICSI Meeting Corpus paper](https://www.ee.columbia.edu/~dpwe/pubs/icassp03-janin.pdf).

### CALLHOME: historically important but easier to misuse

The standard diarization benchmark is the NIST SRE 2000 Disk 8 selection: 500 short multilingual telephone recordings, commonly divided into two halves.

It should not be confused with newer CALLHOME releases containing longer calls. Older CALLHOME results often use:

- oracle speech activity;
- known speaker count;
- ignored overlap;
- forgiveness collars.

That makes many legacy numbers considerably easier than a modern fully automatic pipeline. A useful historical review is [A Review of Speaker Diarization](https://sail.usc.edu/publications/files/Park-Diarization-CSL2022.pdf).

### AISHELL-4 and AliMeeting

[AISHELL-4](https://www.isca-archive.org/interspeech_2021/fu21b_interspeech.pdf) is a good real Mandarin meeting benchmark with 211 sessions and 120 hours. Training overlap is reported around 19%, while evaluation overlap is considerably lower, around 9%.

[AliMeeting/M2MeT](https://arxiv.org/abs/2110.07393) is smaller but more overlap-intensive: the training overlap ratio is approximately 42%, with evaluation around 35%. It is therefore a particularly good test for interruption and simultaneous speech. The official M2MeT diarization challenge used DER with a 250 ms collar and included overlap; newer model cards sometimes rescore it with no collar, producing non-comparable values.

### VoxConverse and VoxSRC

[VoxConverse](https://robots.ox.ac.uk/~vgg/publications/2020/Chung20/chung20.pdf) provides “in the wild” broadcast and web video. Its 448 clips range up to about 20 minutes and can contain as many as 21 speakers.

VoxSRC later created additional challenge sets—for example, the 2021 challenge used a separate 264-file test set with up to 25 speakers. The [VoxSRC 2021 challenge page](https://www.robots.ox.ac.uk/~vgg/data/voxceleb/competition2021.html) documents that protocol.

This is valuable for noise, editing, music and numerous speakers. It does not measure persistent person identity, even if the same celebrity happens to appear in multiple clips.

### CHiME-6 and DiPCo

[CHiME-6](https://chimechallenge.github.io/chime6/overview.html) consists of real dinner parties in participants’ homes. Each party involves four friends moving among kitchen, dining and living spaces. The natural interruptions, backchannels, movement and household noise make it much more realistic than scripted meeting datasets.

Its limitation is scale: development and evaluation contain only two parties each, and systems are permitted to know that there are four speakers.

[DiPCo](https://arxiv.org/abs/1909.13447) is another natural dinner-party collection, but only ten sessions. It is helpful as a second acoustic condition, not large enough to establish general robustness by itself.

### NOTSOFAR-1

[NOTSOFAR-1](https://arxiv.org/abs/2401.08887) was specifically designed around real office meeting acoustics. It contains repeated people and is one of the most relevant recent datasets for your intended environment.

There is a versioning trap: the original paper reports 315 meetings, while the [current open repository](https://github.com/microsoft/NOTSOFAR1-Challenge) reports fewer released/usable meetings after legal and quality-related removals—currently 237 in the open material. Results should identify the exact release and partition instead of simply saying “NOTSOFAR-1.”

Its primary transcription evaluation uses tcpWER, which is a major improvement over evaluating ASR and diarization separately.

## 3. Are benchmarks evaluated as sets?

Yes, virtually all benchmarks aggregate performance over a set of recordings. But aggregation is not the same as corpus-level learning.

There are three different arrangements:

### Set-level aggregation with independent recordings

DIHARD, VoxConverse, CALLHOME, AliMeeting and most published AMI recipes calculate errors over many recordings, but speaker-label mapping is solved separately for each recording.

The system does not need to remember anything between files.

### Repeated people exist, but the benchmark ignores that information

AMI, ICSI and NOTSOFAR contain people who appear in multiple recordings. Nevertheless, ordinary DER scoring effectively asks:

> Did you distinguish the anonymous speakers within each recording?

It does not ask:

> Did you consistently recognize Alice across all of her recordings?

This is the largest mismatch between standard diarization benchmarks and your application.

### True global-identity evaluation

A very recent benchmark, [TST-Bench](https://arxiv.org/abs/2606.14091), explicitly addresses this issue through **Target Speaker Tagging**.

It contains:

- 300 synthetic sessions;
- roughly 200 hours;
- 20–60-minute sessions;
- 8–30 speakers per session;
- 350 identities;
- 150 enrolled speakers and 200 unknown speakers;
- each enrolled speaker appearing in 10–30 sessions;
- persistent identities across recordings.

It evaluates identification/detection rate at a fixed false-alarm rate—essentially whether a system correctly recognizes enrolled people and refuses to falsely identify strangers.

It also validates on real ICSI material. But its large primary set uses read audiobook speech and synthetic meeting construction, so it does not fully reproduce interruptions, backchannels, reverberation or real organizational interaction.

Still, it represents an important conceptual shift: speaker labels become global identities, not arbitrary per-file permutations.

## 4. Does anything propagate human corrections?

### Standard benchmarks: no

Conventional benchmark workflows are frozen:

1. Run the system on the evaluation audio.
2. Compare its output with hidden or held-out reference annotations.
3. Calculate DER, JER or WER.

Human corrections are the ground truth used for scoring. They are not fed back into the system, and inspection of evaluation references is normally prohibited.

Therefore, conventional benchmarks do not test your thesis.

### Within one meeting: promising evidence

A 2026 study, [Interactive In-Meeting Speaker Correction with Human Feedback](https://arxiv.org/abs/2509.18377), uses corrected speaker-attributed spans as online enrollment evidence. Once a person’s segment is corrected, its audio helps classify later segments in the same meeting.

On an AMI test set, the paper reports DER falling from 36.32% to 24.70%, a roughly 32% relative improvement. Speaker-attribution error falls even more. Important caveats:

- feedback was largely simulated rather than collected from ordinary users;
- the evaluation included only 16 AMI test meetings;
- it corrects speaker attribution, not lexical ASR or overlap boundaries;
- learning occurs within the current meeting rather than throughout a long-term corpus.

Nevertheless, it validates the principle that a correction is not merely an edit—it is useful enrollment evidence.

### Across a chronological collection: the closest match to your thesis

The most directly relevant work I found is [Active Correction for Incremental Speaker Diarization of a Collection with Human in the Loop](https://www.mdpi.com/2076-3417/12/4/1782).

Its system processes broadcast shows chronologically:

1. Diarize the new show.
2. Compare its speaker clusters with a persistent database of known-speaker embeddings.
3. Ask a human targeted same/different or identity questions.
4. Correct the clusters.
5. Add the resulting information to the database.
6. Use it when processing later shows.

The authors report:

- up to **33.29% relative reduction in incremental cross-show DER**;
- **11.79% relative improvement** in a penalized DER that also prices human intervention.

The associated ALLIES corpus is unusually relevant:

- 1,008 broadcast shows;
- approximately 328 hours of annotated speech;
- 5,901 unique speakers;
- approximately 11.6 speakers per show;
- 49% of the speakers in a show had appeared previously;
- recurring speakers accounted for approximately 42% of annotated speaking time;
- recordings span 1998–2014.

See [Towards Lifelong Human-Assisted Speaker Diarization](https://www.idiap.ch/~aanjos/papers/elsevier-csal-2022.pdf).

This is strong evidence for your hypothesis, although it propagates corrected **speaker clustering and identity information**, not arbitrary corrections to transcript wording and timing.

### Human effort metrics

A related study, [Human-in-the-Loop Speaker Diarization](https://aclanthology.org/anthology-files/pdf/L/L18/L18-1238.pdf), introduced measures based on the actions required to fix diarization:

- create a boundary;
- delete a boundary;
- create a speaker label;
- change a speaker label.

One striking finding was that segmentation corrections represented about 65% of total correction time. That matters because DER does not necessarily predict editing effort: dozens of tiny boundary errors can be more annoying than one long, obvious mislabeled section.

## 5. Your thesis is right, but corrections contain several different kinds of information

The valuable signals should be separated.

### Corrected identity

“This segment is Alice” can be converted into trusted speaker embeddings. That information can propagate very effectively across recordings.

The system should keep several prototypes for Alice—different rooms, microphones, distances and vocal conditions—rather than collapsing everything into one average voiceprint.

### Corrected clustering

“These two segments are the same person” is a **must-link** constraint.

“These two segments are different people” is a **cannot-link** constraint.

Those constraints can improve clustering across both current and historical recordings.

### Corrected boundaries

“This turn begins 400 ms earlier” is training information for speech activity and speaker-change detection. It will not automatically generalize merely by storing an embedding. It normally requires model adaptation, calibration or retrieval of similar acoustic examples.

### Corrected overlap

“Alice and Bob are both talking here” is multi-label acoustic evidence. Transcript text by itself cannot recover a quieter overlapping voice that the acoustic model failed to detect.

### Corrected words

A lexical correction—such as a name, acronym or product term—belongs primarily to ASR adaptation:

- custom vocabulary;
- retrieval of organizational terminology;
- language-model rescoring;
- pronunciation dictionaries;
- controlled fine-tuning.

It may help semantic speaker attribution—“only Alice normally reports these figures”—but should not be allowed to override contrary acoustic evidence automatically.

The full product should therefore propagate corrections into separate memories for identity, clustering, boundary/overlap behavior and vocabulary.

## 6. The benchmark I would build for your project

Use two complementary test tracks.

### Track A: frozen per-file quality

On a manually verified set, report:

- no-collar, overlap-included DER;
- miss, false alarm and confusion separately;
- JER;
- purity and coverage;
- speaker-count error;
- turn-boundary F1;
- overlap-detection F1;
- WER;
- WDER;
- tcpWER and tcORC-WER;
- human correction minutes per audio hour.

The difference between tcpWER and speaker-agnostic tcORC-WER helps isolate the cost of speaker attribution from underlying recognition errors.

### Track B: longitudinal learning

Build a chronological collection where speakers recur:

- 50–200 meetings;
- 10–20 recurring core people;
- unknown guests who appear once or occasionally;
- multiple rooms, microphones and remote-call conditions;
- 2–8 people per meeting;
- abundant short turns, interruptions and overlap.

Run the process chronologically. At meeting \(n\), the system may use corrections from meetings \(1\ldots n-1\), but never information from future meetings.

Measure:

- **Global-ID DER:** no independent remapping of enrolled people inside every file.
- **DIR at fixed FAR:** correct known-person recognition while rejecting guests.
- **Cross-file identity switches.**
- **Corpus-level purity/coverage or B-cubed clustering scores.**
- **Globally identified tcpWER.**
- **Human minutes per audio hour.**
- **Learning curve:** quality versus number of corrected sessions or corrected minutes.
- **Correction recurrence:** how often a previously fixed class of error returns.
- **Retroactive propagation precision:** what percentage of automatic changes to older files are correct.
- **Catastrophic propagation:** number of recordings damaged by an incorrect identity merge.
- **Net human-time savings:** review time saved minus time spent correcting propagation mistakes.

A critical experimental control is to compare:

1. no memory;
2. voice enrollment only;
3. voice enrollment plus must-link/cannot-link constraints;
4. full correction memory including vocabulary and contextual information.

That will tell you which part of the human correction actually produces the improvement.

## Bottom line

DER remains necessary, but it is not a sufficient metric for high-quality conversational transcription. For your use case, the best evaluation stack is:

- no-collar, overlap-included DER and JER;
- purity/coverage and speaker-count error;
- tcpWER plus WER/WDER;
- short-turn and overlap-specific slices;
- human correction time;
- a separate longitudinal global-identity benchmark.

AMI, ICSI and NOTSOFAR-1 contain the recurring-speaker structure you care about, but their conventional leaderboards mostly ignore it. TST-Bench now explicitly evaluates persistent identity, although much of it is synthetic.

Most importantly, your propagation thesis already has supporting evidence: interactive correction has improved later speaker attribution within meetings, and the ALLIES incremental collection work achieved roughly a one-third relative reduction in cross-show DER. What is still missing is a mature benchmark combining global speaker memory, corrected transcript text, boundary and overlap corrections, retroactive corpus cleanup, and measured human-time savings. That gap is real—and it is precisely where a thoughtfully designed system could offer something materially better than today’s standard diarization pipeline.

# Claude (Fable5 High) response - metrics and benchmarks
Great set of questions — and your last one touches on a real gap in the field, so let me take these in order.

## The metrics

**DER (Diarization Error Rate)** is the canonical metric. It's computed as (missed speech + false alarm speech + speaker confusion) ÷ total ground-truth speech time. Pure segmentation — words don't enter into it. Two protocol knobs swing results dramatically: the **forgiveness collar** (a window, typically 0 or 0.25s, around each reference boundary that's excluded from scoring, forgiving small boundary disagreements) and whether **overlapping speech is scored or skipped**. A system reporting 11% DER with a 0.25s collar and overlap skipped might be 18%+ under the strict protocol (0 collar, overlap scored). This is the single biggest source of apples-to-oranges confusion in vendor claims.

**JER (Jaccard Error Rate)** averages error per speaker rather than per unit of speech time, so a quiet participant who barely talks counts as much as the dominant speaker. Useful complement when you care about not losing the person who only interjects backchannels.

**Speaker counting accuracy** is often reported separately — did the system find 4 speakers when there were 4? Clustering-based systems historically over- or under-count, and a miscount poisons everything downstream.

Then the joint transcript+speaker metrics, which are what actually match your "human can't do better" goal:

**cpWER (concatenated minimum-permutation WER)** — concatenate all words attributed to each speaker, find the speaker-label permutation that minimizes WER against the reference, and score. It jointly punishes transcription errors *and* misattribution. This is the standard top-line metric for multi-talker ASR now (CHiME challenges, AssemblyAI's benchmark page, the DiCoW papers). **tcpWER** adds a time constraint so you can't get credit for the right words attributed to the right speaker at wildly wrong times. **ORC-WER** (optimal reference combination) is a related variant that's more forgiving about how utterances are split across output streams. **WDER (word diarization error rate)** is simpler: the fraction of correctly-transcribed words assigned to the wrong speaker.

For your evaluation harness: `pyannote.metrics` for DER/JER, `meeteval` (from the CHiME community) for cpWER/tcpWER/ORC-WER. Report a strict and a lenient DER variant, and treat cpWER as the number you're actually optimizing.

## The benchmark datasets

All of these are raw audio corpora with human-annotated RTTM files (speaker turn start/end times); most also have transcripts. Here's the landscape:

| Dataset | Content | Size | Speakers/file | Conditions |
|---|---|---|---|---|
| **AMI** | Staged design-team meetings (English, instrumented rooms) | ~100 hrs, ~171 meetings, ~30 min each | 3–5 | Headset (IHM) and single distant mic (SDM) variants |
| **ICSI** | Real research-group meetings | ~72 hrs, 75 meetings | 3–10 | Natural, jargon-heavy |
| **DIHARD III** | Deliberately hard, 11 domains: clinical interviews, courtroom, restaurant, web video, maps tasks, audiobooks... | ~34 hrs eval | 1–10 | The stress test; no collar by design |
| **CALLHOME** (NIST 2000, part 2) | Casual telephone calls among family/friends, multilingual | ~250 conversations, 2–5 min scored each | 2–7 (mostly 2) | Telephone, 8kHz |
| **VoxConverse** | YouTube clips — panel debates, talk shows, news | ~50+ hrs; dev 216 + test 232 files | 1–21 | In-the-wild, celebrity voices |
| **MSDWild** | Multi-party in-the-wild video (vlogs, daily conversation) | ~80 hrs | 2–4+ | Heavy overlap, noisy |
| **AliMeeting / AISHELL-4** | Mandarin office meetings, mic arrays | ~120 hrs each | 2–8 | Far-field |
| **CHiME-5/6** | Real dinner parties in homes, binaural + array mics | 20 sessions, ~50 hrs | 4 | Brutally hard: kitchen noise, movement, overlap |
| **DiPCo** | Amazon's dinner-party corpus | 10 sessions | 4 | Similar to CHiME, smaller |
| **NOTSOFAR-1** | Microsoft's real conference-room meetings | ~315 meetings, ~6 min each, ~30 rooms | 4–8 | The most "office-realistic" recent benchmark; used in CHiME-8 |
| **Ego4D** | Egocentric (head-mounted camera) daily life | subset used for diarization | varies | Extremely hard (~40–50% DER even for the best) |

A few characterizations worth internalizing: **AMI is the closest to your use case** (multi-person working meetings, English, moderate overlap) and is why everyone leads with AMI numbers. **DIHARD** exists specifically to punish domain overfitting. **CALLHOME** is the legacy telephone benchmark — 2-speaker-dominant, so good CALLHOME numbers don't guarantee good 5-speaker meeting performance. **CHiME/DiPCo/NOTSOFAR** are where overlap and far-field conditions dominate, and where cpWER (not DER) is the headline metric.

## Recurring speakers across files — mostly a gap

This is the sharp part of your question, and the honest answer is that **standard benchmarks score each file independently with anonymous labels**. "Speaker 1" in file A has no required relationship to "Speaker 1" in file B, even when it's literally the same person. DER and cpWER both permute labels per-file to find the best match, so cross-file identity consistency is *definitionally invisible* to the standard metrics.

Some corpora do *contain* recurring speakers — AMI's scenario meetings are series (ES/IS sessions) where the same 4-person team meets repeatedly across multiple sessions; CHiME parties and NOTSOFAR rooms have repeated participants — but the evaluations don't exploit or test that. The task you're describing has a name in the literature: **speaker linking** (or cross-show/longitudinal diarization), and it was actively benchmarked in older French broadcast evaluations (REPERE, ETAPE had "cross-show" conditions where identity had to be consistent across episodes), but it never became a mainstream track. The metric there shifts from DER to **identification error rate** — you're no longer clustering anonymous voices, you're recognizing enrolled ones.

The modern commercial expression of this is **voiceprinting / speaker identification**: pyannoteAI's Precision-2 API offers it as a paid feature, and it's exactly "enroll a speaker once, get consistent named labels across your whole corpus." That's the productized version of what an organization-scoped benchmark would test — but there's no public academic benchmark I'm aware of that scores "consistent speaker identity across an organization's meeting archive." If you build a harness for that on your own corpus, you'd be measuring something the field largely doesn't.

## Correction propagation — your thesis, and where it maps onto existing tech

No standard benchmark or evaluation protocol involves propagating human corrections from one transcript to improve others. Nothing in AMI/DIHARD/CHiME-land does this. But your thesis is technically well-grounded, and the machinery to implement it exists under different names:

**Corrections as enrollment.** When a human fixes speaker attribution in one transcript, they've effectively produced *verified labeled audio* for each speaker. Extract speaker embeddings from those corrected segments and you have high-quality voiceprints — better than automatic enrollment because a human vouched for them. Those voiceprints then convert the diarization problem on every other file in the corpus from *unsupervised clustering* (hard, error-prone speaker counting) into *supervised identification/detection* (much easier).

**TS-VAD (target-speaker voice activity detection)** is the specific model family built for this: given embeddings for known speakers, it predicts each target speaker's activity frame-by-frame, including through overlap. TS-VAD-style systems have won multiple DIHARD/VoxSRC challenges precisely because knowing who you're looking for beats discovering them. NVIDIA's multitalker-Parakeet is philosophically adjacent (diarization-conditioned per-speaker transcription), and the SE-DiCoW line ("self-enrolled" diarization-conditioned Whisper) is the research frontier of feeding speaker identity into the ASR itself.

**Semi-supervised and active-learning diarization** research also exists — "which segment should the human correct next for maximum corpus-wide improvement" is a studied question, though small and without a shared benchmark.

So the pipeline your thesis implies would be: human corrects file 1 → harvest verified per-speaker embeddings → run TS-VAD or embedding-constrained clustering (or voiceprint-based identification) on files 2–N → optionally have an LLM do a cleanup pass using the now-known speaker identities, names, and speech-pattern priors ("Randy always opens the meeting," "TL is the one who says 'mm-hmm' constantly"). Each additional correction improves the voiceprint bank. That's a genuinely strong loop, and the reason it isn't a benchmark is mostly that academic evaluations are one-shot and corpus-agnostic by design — not that the idea doesn't work. If anything, the lack of a public benchmark means you'd want to measure it yourself: on your own corpus, compare DER/cpWER on files 2–N with and without enrollment from the corrected file 1, with the delta being the value of one human correction. That's a clean experiment, and I'd predict the delta is large — especially on speaker counting and on quiet/similar-sounding speakers, which are exactly where unsupervised clustering fails.
