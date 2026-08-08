file: apps/content_studio/AGENTS.md
title: content studio — Agent Instructions

Per-app overrides and orientation for `apps/content_studio/`. Repo-wide rules in the root
`AGENTS.md` still apply (Python style, branch discipline, commit granularity, etc.).

Naming note: this directory is snake_case (not the usual kebab-case app-dir convention)
because it is an importable Python package — the repo's own naming rules say dashes are not
importable. Its `config.py` is tracked via a scoped `!apps/content_studio/config.py` negation
in the root `.gitignore` (the global `**/config.py` rule targets credential files; this module
holds model ids and thresholds only — keep secrets in env vars, never in this file).


## What this app is
Media generation with a verification loop, across three media kinds:
- **animation** — still image → short GIF/WebP-style loop;
- **video** — text- or image-to-video clip (Seedance 2.0 default);
- **audio** — speech (TTS), music, or sound effects.
Every candidate is checked by a media-appropriate verifier (vision LLM for visuals; Whisper
transcribe-and-compare for speech) and regenerated on failure. Primary backends: fal.ai and
Replicate. See `README.md` for the user-facing intro.


## Module map
- `config.py` — defaults: per-kind providers/models (Seedance 2.0, MiniMax speech, Lyria,
  ElevenLabs sfx, MusicGen), verifier model (`claude-opus-4-8`), thresholds. One source of truth.
- `models.py` — data holders: `MediaRequest` base + `AnimationRequest` / `VideoRequest` /
  `AudioRequest`; `MediaResult`; `FrameIssue` / `VerifyResult` / `PipelineResult`.
- `frames.py` — pure frame-index math (`evenly_spaced_indices`). No PIL.
- `prompts.py` — the visual verifier's system prompt + forced-tool JSON schema + negative-prompt
  augmentation. **This is where the "what does janky look like" knowledge lives.**
- `verify.py` — `VisualVerifier` (frame sampling + asker + policy), pure `apply_policy`, and the
  default `anthropic_vision_asker` (Claude vision; handles reference-less t2v too).
- `verify_audio.py` — `AudioVerifier` (speech: transcribe-and-compare via fal Whisper; music/sfx:
  structural checks), pure `audio_policy`, `text_similarity`, `wav_duration_s`.
- `imaging.py` — the only module that touches pixels (Pillow): GIF/WebP I/O, mp4/webm decode
  (lazy imageio/cv2), frame→base64, and `FileCodec` for the visual verifier.
- `providers/` — `base.py` (`MediaProvider` with generate_<kind> dispatch + shared HTTP helpers),
  `fal.py` / `replicate.py` (full multi-kind aggregators), `runway.py` (optional, i2v only),
  `mock.py` (offline synth: PIL visuals, stdlib WAV audio; can inject defects),
  `__init__.py` (`get_provider` registry).
- `pipeline.py` — `generate_and_verify`: the generate→verify→regenerate loop, best-of-N,
  keep-best; `default_verifier_for` picks the verifier by media kind.
- `cli.py` — subcommands: `animate`, `video`, `audio`, `verify`.
- `profiles/` — tracked consumer asset specs (what to generate, formats, prompts, delivery
  paths). Generated media goes under `_data/profiles/<slug>/` (local only).
- `model3d/` — image → rigged/animated GLB pipeline (its own CLI:
  `python -m apps.content_studio.model3d.cli`). Mesh providers: Hyper3D Rodin free trial
  (default, no key) and Meshy (`MESHY_API_KEY`, paid). Blender 4.5+ runs headless for
  rig/animate/export (`blender/rig_dragon.py`), preview renders (`blender/render_previews.py`),
  and hosts the vendored Blender MCP add-on (`blender/blender_mcp_addon.py`, localhost:9876;
  `cli mcp-launch` starts a UI session with the server up). `validate_glb.py` is a pure-stdlib
  GLB contract checker. `blender/VENDORED.md` records the add-on's provenance, license, checksum,
  and security boundary. Tests: `tests/test_model3d.py`.


## Consumer asset profiles
Specs for generating media that another app will consume. Each profile is a markdown file in
`profiles/`; outputs land under `_data/profiles/<slug>/{reference,staging,approved}/`.

`apps/content_studio/_data/` is a canonical local-files mount (see `scripts/local_files_mounts.txt`)
so generated assets are shared across worktrees via `_LOCAL_FILES`.

Workflow: read profile → place reference stills → generate with CLI (`--out` into `staging/`) →
verify → move to `approved/` → copy into the consumer app's asset folder (listed in the profile).
Consumer branches may not exist in every worktree; profiles are still valid here.


## Design rules specific to this app
- **Keep the decision logic pure.** `apply_policy` / `audio_policy` and the pipeline take
  injected `asker` / `transcriber` / `verifier` / `codec`, so the whole loop is testable without
  a live model, Pillow, or audio files. Don't move network or PIL calls into them.
- **Heavy deps are lazy.** Importing `apps.content_studio` must not require Pillow, anthropic,
  or requests. PIL lives behind `imaging.py` (and mock visual paths); `anthropic` is imported
  inside the asker; `requests` inside provider methods. Keep it that way.
- **The policy is the gate, not the model's opinion.** Visual: hard fail on extra limbs, any
  critical issue, or anatomy/identity/temporal below floors, even if the model said shippable.
  Speech: transcript similarity below `MIN_SPEECH_SIMILARITY` is a critical fail. Tune
  thresholds in `config.py`.
- **Providers are thin.** Send only the broadly-shared input fields per kind; anything
  model-specific rides in `request.extra` (CLI `--extra key=value`). Model ids are config
  defaults overridable per request — don't hardcode ids in provider logic.
- **No `data/` for source.** Generated media goes under `_data/` (gitignored). Don't add a
  source-code `data/` package (root `.gitignore` would swallow it — same trap as `config.py`).
- **Treat Blender MCP as trusted-local code execution.** The loopback socket can execute
  arbitrary Python inside Blender with the process's host permissions. Keep it on localhost,
  save work before connecting, and do not attach untrusted prompts or remote clients. The
  external MCP server is not vendored here and may have separate telemetry behavior; see
  `model3d/blender/VENDORED.md`.

## Adding a provider
1. Subclass `MediaProvider` in `providers/<name>.py`; implement `generate_animation` /
   `generate_video` / `generate_audio` for the kinds it supports, each returning a `MediaResult`
   (set `output_path` to a downloaded file, or `frames` for in-memory visuals).
2. Use `file_data_uri()` / `extract_output_url()` / `download_to_file()` / `slug_for()` from
   `providers/base.py`; lazy-import `requests` inside methods.
3. Register it in `providers/__init__.py:get_provider` and add it to `PROVIDER_NAMES`.
4. If it returns mp4/webm, `imaging.read_any_frames` already decodes it (needs imageio).

## Adding a media kind
1. Add a `MediaRequest` subclass in `models.py` (set `media_kind`, extend `to_kwargs`).
2. Implement `generate_<kind>` on the providers that support it (dispatch is automatic).
3. Add a verifier with an `assess(result, request)` method and wire it into
   `pipeline.default_verifier_for`; keep its pass/fail rules in a pure policy function.
4. Add a CLI subcommand and tests for the policy + an offline mock path.


## Tests
Offline; no API key or network needed. Opt-in live vision requires
`CONTENT_STUDIO_LIVE_VISION=1` plus an Anthropic key.
```bash
.venv/bin/python -m pytest tests/test_content_studio.py tests/test_model3d.py -q
# or: .venv/bin/python -m unittest discover -s tests -p 'test_content_studio.py'
```
Coverage (`tests/test_content_studio.py`): frame sampling; the visual policy
(clean, extra-limbs, critical issue, low anatomy/identity/temporal/overall, configurable
thresholds, JSON-string score/issue coercion) and `VisualVerifier` sampling/reference
wiring (incl. reference-less t2v); the audio policy (similarity pass/fail, missing file,
duration tolerance, unverified-speech leniency + `require_transcription`), `AudioVerifier`
with fake transcribers, and mock WAV synthesis for all three audio kinds;
requests/dispatch (copy_with subclass fidelity, AudioRequest validation, unsupported-kind
ProviderError, default verifier selection); negative-prompt merging; the
generate→verify→retry loop (first-pass, retry-then-pass with negative strengthening,
never-pass best-effort, best-of-N, audio-not-seeded-with-negative, video-with-stub); and
Pillow-gated end-to-end runs (clean animation passes and writes a real GIF; injected
`extra_limb` defect rejected; mock t2v produces frames). The optional `TestLiveVision`
runs the real Claude verifier only when `CONTENT_STUDIO_LIVE_VISION=1` and
`ANTHROPIC_API_KEY` (or `ANTHROPIC_API_KEY_LOCAL`) is present.
