file: plans/2026-06-24_content-studio.md
title: Content Studio — design and architecture
last-updated: 2026-07-27_2149
ai: Codex - GPT-5
session: `PR review #59`


## Problem
We want to generate media from verbal descriptions — short GIF-like animations from a still
image, longer video clips (text- or image-driven), and audio (speech, music, sound effects) —
without shipping the garbage generative models routinely produce. One-shot prompting
(ChatGPT/Claude chat, raw provider calls) has no quality gate: image-to-video clips come back
with "extra janky arms," fused/melted features, or characters that morph mid-clip; TTS renders
can garble or drop words.

The app lives at `apps/content_studio/` (started 2026-06-24 as `apps/animation/`, broadened and
renamed 2026-07-07). This doc captures the architecture and the decisions behind it.

Scope note: the later `model3d/` mesh → Blender → validated-GLB scaffold is summarized in the
app README and AGENTS file. This design document remains focused on the generate→verify media loop.


## Approach: a closed verify-and-regenerate loop
The core idea is to stop trusting a single generation and instead **inspect every candidate and
regenerate the bad ones**:

1. **Generate** a candidate (provider-swappable backends; fal.ai and Replicate are the two
   primary aggregator accounts, covering Seedance video, MiniMax speech, and many more).
2. **Verify** with a media-appropriate verifier:
   - visual (animation/video): sample N frames evenly, show a vision LLM the reference image
     (when there is one), the description, and the frames; force a structured verdict against an
     anatomical-correctness rubric;
   - audio (speech): transcribe the output (fal-hosted Whisper) and compare against the
     requested text; music/sfx get structural checks (duration/tolerance, non-trivial file).
3. **Policy** turns each verdict into pass/fail with fixed, inspectable rules.
4. On fail, **regenerate** — for visuals, folding the verifier's specific complaints into the
   negative prompt. Keep the best-scoring candidate across all attempts (best-of-N supported).


## Architecture
Capability-dispatched providers + injectable per-media verifiers, wired by a pure loop.

- **Requests** (`models.py`): `MediaRequest` base with `AnimationRequest`, `VideoRequest`,
  `AudioRequest` subclasses (`media_kind` drives everything downstream).
- **Providers** (`providers/`): `MediaProvider.generate()` dispatches to
  `generate_<media_kind>()`; a provider supports a kind by implementing the method. `fal` and
  `replicate` implement all three kinds behind their uniform queue/prediction APIs; `runway` is
  an optional image-to-video extra; `mock` synthesizes everything offline (PIL visuals, stdlib
  WAV audio) and can inject a "janky extra limb" defect to exercise the verifier.
- **Verifiers**: `VisualVerifier` (frame sampling + Claude-vision asker + pure `apply_policy`)
  and `AudioVerifier` (transcriber + pure `audio_policy`). Askers/transcribers are injectable;
  tests use fakes.
- **Pipeline** (`pipeline.py`): `generate_and_verify` runs the loop; `default_verifier_for`
  picks the verifier by media kind. Depends only on injected objects — fully testable offline.
- **Imaging** (`imaging.py`): the only pixel-touching module (Pillow): GIF/WebP I/O, mp4/webm
  decode (imageio/cv2, lazy), frame→base64, `FileCodec`.


## Key decisions
- **Policy over vibes.** Pass/fail is rule-based, not the model's own judgement. Visual hard
  gates: extra-limbs flag, any `critical` issue, anatomy < 7, identity < 6, temporal < 5
  (0-10 scales), else overall ≥ 70/100. Speech hard gate: transcript similarity ≥ 0.80 after
  normalization. Strict, inspectable, unit-testable.
- **Reference-grounded visual verification.** The verifier sees the original image alongside
  output frames, so it judges identity preservation, not just per-frame plausibility.
  Text-to-video (no reference) falls back to internal-consistency identity judging.
- **Speech verified by round-trip.** TTS output is transcribed and compared to the requested
  text — the audio equivalent of the extra-arm check. Uses the same FAL_KEY as generation.
  Music/sfx content judgement is a roadmap item (needs an audio-understanding model).
- **Two aggregators, one interface.** fal and Replicate each expose one uniform job API across
  hundreds of models, so one provider class each covers video + animation + audio. Model ids
  are config defaults (Seedance 2.0 for video) overridable per call; model-specific input
  fields ride in `request.extra`.
- **Two layers of visual anti-jank.** A baseline negative prompt seeds every visual request;
  the verifier's per-run `recommended_negative_prompt` is merged in on retries.
- **Dependency-light imports.** `import apps.content_studio` pulls in no Pillow / anthropic /
  requests; each loads lazily where needed.
- **Mock-first testability.** The whole loop runs offline (mock provider + stub verifiers), so
  the suite needs no keys; mock audio needs only the stdlib.
- **snake_case package dir + tracked config.** `content_studio` (not kebab) because the package
  is imported; `config.py` needed a scoped `.gitignore` negation because the root credential
  rule (`**/config.py`) silently swallows it — found the hard way when the first push shipped
  without the file.


## Verification rubrics
Visual (five dimensions, issues carry severities; dimension 1 is why the app exists):
1. **Anatomy / structure** — extra/duplicated/missing/fused/melted limbs, impossible joints,
   floating parts, malformed faces → trips the `extra_limbs_detected` flag.
2. **Identity preservation** — same species/colors/proportions as the reference (or internal
   consistency for t2v).
3. **Temporal consistency** — stable character across frames.
4. **Motion / artifacts** — warping, ghosting, smearing, tearing, jelly-wobble.
5. **Prompt adherence** — motion matches the description.

Audio: missing/empty file (critical); speech transcript similarity below floor (critical);
duration outside tolerance of an explicit request (major); unverifiable speech is a minor
"unverified" flag by default, a failure with `require_transcription`.


## Default models
| Kind | fal | Replicate |
|------|-----|-----------|
| video (t2v / i2v) | `bytedance/seedance-2.0/text-to-video`, `.../image-to-video` | `bytedance/seedance-2.0` |
| animation (short i2v) | `bytedance/seedance-2.0/fast/image-to-video` | `bytedance/seedance-2.0` |
| speech | `fal-ai/minimax/speech-02-hd` | `minimax/speech-02-hd` |
| music | `fal-ai/lyria2` | `meta/musicgen` |
| sfx | `fal-ai/elevenlabs/sound-effects/v2` | `meta/musicgen` (prompted) |
Speech verification transcriber: `fal-ai/whisper`.


## Roadmap / extensions
- **Image generation** as a fourth media kind (stills, sprites) — the request/dispatch/verifier
  pattern is designed for it (see AGENTS.md → Adding a media kind).
- **Audio content judgement** for music/sfx via an audio-understanding model.
- **Per-model presets** for the aggregators' schema quirks as favorites emerge; possibly typed
  wrappers over `extra`.
- **Frame-montage verification** (single contact-sheet image) to cut vision-token cost.
- **Looping / boomerang export** for sticker-style animations.
- **Eval harness**: a small labeled set of good/janky outputs to measure verifier
  precision/recall and tune thresholds.


## Tests
`tests/test_content_studio.py` — 53 offline tests (frame math, both policies, dispatch,
negative-prompt merge, the retry loop, mock audio synthesis, Pillow-gated end-to-end visual
runs, malformed vision payloads, and multilingual transcript matching), plus an optional
live-Claude test when explicitly enabled with an Anthropic key. `tests/test_model3d.py` adds
9 offline tests for GLB validation and Meshy/Rodin request caching.
Run: `.venv/bin/python -m pytest tests/test_content_studio.py tests/test_model3d.py -q`.
