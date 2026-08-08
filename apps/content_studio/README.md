# Content Studio

Generate **short animations, video clips, and audio** (speech / music / sound effects) from
verbal descriptions — and **verify every output** so broken results get caught and regenerated
instead of shipped.

This app exists because one-shot prompting of generative media models routinely returns garbage:
image-to-video clips that "grew extra janky arms," characters that morph mid-clip, speech with
garbled words. The fix here is a **closed loop**: generate → inspect every candidate with a
verifier suited to its media type → reject the broken ones → regenerate (for visuals, with the
verifier's specific complaints folded into the negative prompt) → keep the best result.

Primary generation backends: **fal.ai** and **Replicate** — the two aggregator accounts this
studio assumes. One provider class per aggregator covers all media kinds, with **Seedance 2.0**
as the default video model. Runway is wired as an optional extra, and an offline `mock` provider
runs the whole loop without keys.


## How it works

```
request (animation | video | audio)
   │
   ▼
provider.generate ──▶ candidate media ──▶ media-appropriate verifier
   ▲                                            │
   │                                            ▼
stronger negative prompt (visual)        pass/fail policy
   │                                            │ fail
   └────────────────────────────────────────────┘
                                                │ pass
                                                ▼
                                         ship the result
```

- **Visual verifier** (`verify.py`, `prompts.py`): samples N frames from the clip and shows a
  vision model (Claude Opus 4.8) the reference image (when there is one), the description, and
  the frames. A forced tool call returns a structured verdict; a fixed, inspectable **policy**
  hard-fails on any extra-limb / critical-issue / low-anatomy / identity-drift signal rather
  than trusting the model's gut call.
- **Audio verifier** (`verify_audio.py`): speech is **transcribed (fal-hosted Whisper) and
  compared against the requested text** — wrong or garbled words fail. Music/sfx get structural
  checks (exists, non-trivial, duration within tolerance).
- **Pipeline** (`pipeline.py`) runs the generate→verify→regenerate loop (best-of-N optional)
  and keeps the best candidate.


## Quick start

```bash
# Install deps into the project venv
.venv/bin/pip install -r apps/content_studio/requirements.txt

# Keys: the two aggregators + the verifier
export FAL_KEY=...                  # fal.ai (generation + speech-verify transcription)
export REPLICATE_API_TOKEN=...      # Replicate (alternate backend)
export ANTHROPIC_API_KEY=...        # visual verifier (ANTHROPIC_API_KEY_LOCAL also works)

# Animation: still image -> short verified GIF loop
.venv/bin/python -m apps.content_studio.cli animate \
    --image dragon.png --prompt "the dragon gently flaps its wings and blinks" \
    --out out/dragon.gif

# Video: text-to-video (Seedance 2.0) — add --image for image-to-video
.venv/bin/python -m apps.content_studio.cli video \
    --prompt "a pink dragon soars over a castle at sunset" --duration 5 --out out/flight.mp4

# Audio: speech (verified by transcribe-and-compare), music, or sfx
.venv/bin/python -m apps.content_studio.cli audio --kind speech \
    --text "Welcome back, adventurer!" --out out/welcome.mp3
.venv/bin/python -m apps.content_studio.cli audio --kind sfx \
    --prompt "a magical sparkle chime" --duration 3

# Verify an existing file (visual clip or speech audio)
.venv/bin/python -m apps.content_studio.cli verify --file out/dragon.gif \
    --image dragon.png --prompt "the dragon flaps its wings"
.venv/bin/python -m apps.content_studio.cli verify --file out/welcome.mp3 \
    --text "Welcome back, adventurer!"
```

Offline demo without any keys: add `--provider mock --no-verify` to any generate command
(`mock` synthesizes clips/audio locally; `--defect extra_limb` injects a janky arm to see the
verifier catch it when a verifier key is available).


## Library use

```python
from apps.content_studio import (
    AnimationRequest, VideoRequest, AudioRequest,
    generate_and_verify, get_provider,
)

provider = get_provider("fal", output_dir="out")     # or "replicate" / "runway" / "mock"

clip = generate_and_verify(provider, VideoRequest(
    prompt="a pink dragon soars over a castle at sunset", duration_s=5))
speech = generate_and_verify(provider, AudioRequest(
    text="Welcome back, adventurer!", audio_kind="speech"))

print(clip.to_json())    # verdict + scores + issues
print("ship:" if clip.passed else "best-effort:", clip.output_path)
```

Verifiers are injectable (`VisualVerifier(asker=...)`, `AudioVerifier(transcriber=...)`), so the
vision/transcription backends swap without touching the pass/fail policies. See
`apps/content_studio/AGENTS.md` for the module map and how to add a provider or media kind.


## Model3d scaffold

`python -m apps.content_studio.model3d.cli` exposes the prototype image → generated mesh →
Blender rig/animate/export → GLB validation path. Rodin and Meshy are the mesh backends; Blender
4.5+ performs the rigging and preview steps. Generated meshes, sidecars, and previews stay under
`_data/model3d/`.

`model3d ... mcp-launch` starts Blender with the vendored Blender MCP add-on listening on
`localhost:9876`. A connected client can execute arbitrary Python inside Blender, so this is a
trusted-local developer tool—not a sandbox. Keep it on loopback, save work before connecting, and
do not attach untrusted prompts or remote clients. Provenance, checksum, license, and telemetry
notes are in `model3d/blender/VENDORED.md`.


## Providers, models, and keys

| Provider   | Env var               | Video default            | Speech default          | Music / SFX default        |
|------------|-----------------------|--------------------------|-------------------------|-----------------------------|
| `fal`      | `FAL_KEY`             | `bytedance/seedance-2.0/{text,image}-to-video` | `fal-ai/minimax/speech-02-hd` | `fal-ai/lyria2` / `fal-ai/elevenlabs/sound-effects/v2` |
| `replicate`| `REPLICATE_API_TOKEN` | `bytedance/seedance-2.0` | `minimax/speech-02-hd`  | `meta/musicgen` (both)      |
| `runway`   | `RUNWAYML_API_SECRET` | `gen4_turbo` (image-to-video only) | —              | —                           |
| `mock`     | — (offline)           | local synthesis          | stdlib WAV beeps        | stdlib WAV tones            |

Every model id is a config default (`config.py`) and overridable per call via `--model` /
`model=`; model-specific input fields pass through `--extra key=value` / `extra={}`.
Verifier key: `ANTHROPIC_API_KEY` (falls back to `ANTHROPIC_API_KEY_LOCAL`).

Outputs default to `apps/content_studio/_data/` (gitignored). Pass `--out` to choose a path.

Consumer apps (e.g. math-quiz dragon game) have tracked specs in `apps/content_studio/profiles/`;
generated assets for a project go under `_data/profiles/<slug>/`. The `_data/` folder is a
canonical local-files mount shared across worktrees — see `docs/worktrees-guide.md`.
