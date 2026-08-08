## ADDED Requirements
### Requirement: Media Request Types
The system SHALL model animation, video, and audio generation requests with shared fields and kind-specific validation.
#### Scenario: Animation request is created
- **WHEN** a caller creates an animation request with an image path, prompt, duration, and fps
- **THEN** the request records media kind `animation`, preserves common generation fields, and describes the intended motion with its prompt.
#### Scenario: Video request is created
- **WHEN** a caller creates a video request with a prompt and optional image path
- **THEN** the request records media kind `video`, supports text-to-video when no image path is present, and supports image-to-video when an image path is present.
#### Scenario: Invalid audio request is created
- **WHEN** a caller creates a speech request without text, a music or sfx request without a prompt, or an audio request with an unknown kind
- **THEN** the system rejects the request with a validation error.

### Requirement: Provider Registry And Dispatch
The system SHALL construct named media providers lazily and dispatch generation by request media kind.
#### Scenario: Known provider is requested
- **WHEN** a caller asks for `mock`, `fal`, `replicate`, or `runway`
- **THEN** the registry imports only the selected provider and returns an instance of it.
#### Scenario: Unknown provider is requested
- **WHEN** a caller asks for a provider name outside the registered set
- **THEN** the system raises a value error listing the available provider names.
#### Scenario: Provider lacks a media kind
- **WHEN** `generate()` receives a request whose `generate_<kind>` method is not implemented by the provider
- **THEN** the system raises a provider error that identifies the unsupported kind and the provider's supported kinds.

### Requirement: Generation Providers
The system SHALL provide current backends for offline generation, fal.ai, Replicate, and optional Runway image-to-video generation.
#### Scenario: Mock provider generates media
- **WHEN** a caller uses the mock provider for animation, video, or audio
- **THEN** the system synthesizes local media without API keys, using Pillow-backed visual frames when visual output is requested and stdlib WAV output for audio.
#### Scenario: fal or Replicate provider generates media
- **WHEN** a caller uses fal or Replicate for animation, video, speech, music, or sfx
- **THEN** the system submits the provider job with common request fields, merges `request.extra`, polls for completion, downloads the returned media URL, and wraps it in a media result.
#### Scenario: Runway provider generates media
- **WHEN** a caller uses Runway with an image-backed animation or video request
- **THEN** the system submits an image-to-video task and downloads the returned clip; if no image path is present, it rejects the request because Runway is image-to-video only.

### Requirement: Command-Line Generation And Verification
The system SHALL expose command-line commands for generating animations, videos, audio, and for verifying an existing media file.
#### Scenario: Generate command runs with verification
- **WHEN** the user runs `animate`, `video`, or `audio` without `--no-verify`
- **THEN** the CLI builds the corresponding request, runs the generate-and-verify pipeline with the selected provider, prints the JSON pipeline result, materializes the chosen output, and exits nonzero when the result is only best-effort.
#### Scenario: Generate command skips verification
- **WHEN** the user runs a generate command with `--no-verify`
- **THEN** the CLI generates one candidate, materializes it, prints that verification was skipped, and exits successfully if media was produced.
#### Scenario: Existing file is verified
- **WHEN** the user runs `verify` for an audio file or supplies `--text`
- **THEN** the CLI verifies it as speech against the intended text; otherwise it verifies visual media with the supplied prompt and optional reference image.

### Requirement: Verified Generation Loop
The system SHALL generate, verify, retry failed candidates, and keep the best candidate seen.
#### Scenario: First candidate passes
- **WHEN** the verifier passes the first generated candidate
- **THEN** the pipeline returns a passed result with one recorded attempt.
#### Scenario: Visual candidate fails with retry guidance
- **WHEN** a visual candidate fails and the verifier returns a recommended negative prompt
- **THEN** the pipeline merges that guidance into the next visual request's negative prompt before retrying.
#### Scenario: No candidate passes
- **WHEN** all configured attempts and candidates fail verification
- **THEN** the pipeline returns a best-effort result using the highest-scoring candidate.

### Requirement: Visual Verification Policy
The system SHALL verify animation and video candidates by sampling frames, optionally including a reference image, and applying strict policy gates.
#### Scenario: Visual candidate is assessed
- **WHEN** a visual result is assessed
- **THEN** the verifier reads result frames, samples evenly spaced frames, encodes the sampled frames as PNG base64, includes the source image when the request has one, and asks for a structured quality report.
#### Scenario: Visual hard gate is tripped
- **WHEN** the structured report flags extra limbs, any critical issue, low anatomy, low identity, low temporal consistency, or low overall score
- **THEN** the policy fails the candidate even if the model's holistic pass field is true.
#### Scenario: Text-to-video has no reference image
- **WHEN** a video request has no image path
- **THEN** the verifier sends no reference image and judges identity through internal consistency across sampled frames.

### Requirement: Audio Verification Policy
The system SHALL verify speech by transcript similarity and music or sfx by structural checks.
#### Scenario: Speech can be transcribed
- **WHEN** speech output exists and a transcriber is available
- **THEN** the verifier transcribes the file, normalizes the expected text and transcript, computes similarity, and fails the result when similarity is below the configured threshold.
#### Scenario: Speech cannot be transcribed
- **WHEN** speech output exists but no transcriber is available
- **THEN** the verifier passes the file structurally with a minor unverified-content issue unless `require_transcription` is set.
#### Scenario: Audio file or duration fails
- **WHEN** an audio output is missing, empty, or has a measurable WAV duration outside the requested tolerance
- **THEN** the policy records an issue and fails the result.

### Requirement: Media File Handling
The system SHALL read, write, transcode, and materialize generated media according to the current file handling rules.
#### Scenario: In-memory frames are materialized
- **WHEN** a selected result contains visual frames instead of a source file
- **THEN** the CLI writes those frames as GIF or WebP, changing a non-animation output extension to GIF.
#### Scenario: Provider file extension differs from requested output
- **WHEN** a selected result has a file whose extension differs from the requested output
- **THEN** the CLI transcodes visual media to GIF or WebP when possible, otherwise copies the file using the provider source extension.
#### Scenario: Verifier reads visual files
- **WHEN** the visual verifier reads an output path
- **THEN** the codec reads still images, animated GIF/WebP, or video frames and downscales encoded frames for the vision verifier.

### Requirement: Consumer Asset Profiles
The system SHALL keep tracked consumer asset profiles separate from generated local media.
#### Scenario: Profile is stored
- **WHEN** a consumer app needs generated media specifications
- **THEN** the profile is stored as markdown under `apps/content_studio/profiles/` with requested formats, prompts, staging locations, and delivery paths.
#### Scenario: Profile workflow is followed
- **WHEN** assets are generated for a consumer profile
- **THEN** reference, staging, and approved outputs live under `apps/content_studio/_data/profiles/<slug>/`, and approved assets are copied or symlinked into the consumer app outside the profile file.

### Requirement: Model3D Mesh Generation
The system SHALL generate or reuse image-to-3D GLB meshes through Rodin or Meshy providers.
#### Scenario: Rodin mesh generation runs
- **WHEN** the model3d mesh command uses the Rodin provider
- **THEN** the system creates a Rodin task from the source image and optional prompt, polls the subscription until done, downloads the first GLB asset, and records a sidecar JSON cache.
#### Scenario: Meshy mesh generation runs
- **WHEN** the model3d mesh command uses the Meshy provider
- **THEN** the system sends a PNG or JPEG data URI with configured topology, polycount, texture, pose, and format options, polls until success, downloads the GLB and optional thumbnail, and records a sidecar JSON cache.
#### Scenario: Matching mesh cache exists
- **WHEN** a sidecar cache has the same payload hash and `--force` is not set
- **THEN** the mesh provider reuses the existing task or downloaded GLB instead of creating a duplicate provider job.

### Requirement: Model3D Blender Pipeline
The system SHALL run Blender scripts to rig generated meshes, render previews, validate outputs, and launch the vendored Blender MCP server.
#### Scenario: Rig command runs
- **WHEN** the user runs the model3d rig command with an input mesh and output path
- **THEN** the system runs Blender headless, imports the mesh, normalizes it, builds a heuristic dragon armature, authors the configured animation clips, and exports a GLB.
#### Scenario: Build command runs
- **WHEN** the user runs the model3d build command
- **THEN** the system runs mesh generation, rig export, GLB validation, and preview rendering in sequence, then prints a JSON summary and returns failure when validation fails.
#### Scenario: MCP launch runs
- **WHEN** the user runs the model3d MCP launch command
- **THEN** the system launches Blender UI with the vendored BlenderMCP add-on enabled and reports that the server listens on localhost port 9876.

### Requirement: Dragon GLB Validation
The system SHALL validate rigged dragon GLB files against the current game asset contract.
#### Scenario: Valid dragon GLB is checked
- **WHEN** a GLB has glTF 2.0 structure, at least one skin, all required clip names, clip durations above the minimum, and a bounding-box height between 20 and 100 model units
- **THEN** validation succeeds and returns a report with summary fields and no problems.
#### Scenario: Required contract is missing
- **WHEN** a GLB is malformed or lacks required clips, skinning, valid animation durations, or the expected height range
- **THEN** validation fails and reports the specific problems.

### Requirement: Dependency-Light Testable Boundaries
The system SHALL keep imports, policies, verifiers, providers, and frame math testable without live services by default.
#### Scenario: Package is imported
- **WHEN** a caller imports `apps.content_studio`
- **THEN** the import exposes request, result, verifier, pipeline, and provider registry symbols without requiring Pillow, requests, anthropic, or Blender immediately.
#### Scenario: Logic is tested offline
- **WHEN** tests inject fake askers, transcribers, providers, codecs, or verifiers
- **THEN** frame sampling, pass/fail policies, negative-prompt merging, provider dispatch, audio checks, and pipeline retries can run without API keys or network access.
