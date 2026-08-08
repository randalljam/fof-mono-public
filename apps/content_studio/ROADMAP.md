file: apps/content_studio/ROADMAP.md
title: Content Studio — roadmap and vision

## Vision
Content Studio is headed toward a reusable, provider-swappable asset factory for the repo's apps: describe the media, generate candidates, verify them with media-specific checks, retry bad outputs with concrete feedback, and keep only assets that are good enough to ship. The app starts with CLI and library workflows for animation, video, audio, and dragon-focused 3D assets, with generated files staying local under `_data/` and tracked profiles describing what consumer apps need.

## Now / Next / Later
- **Now** - Stabilize the S1-dev media loop across animation, video, and audio: request models, provider dispatch, fal/Replicate/Runway/mock backends, strict visual policy, speech transcript verification, CLI materialization, and offline tests.
- **Now** - Continue the Dragon Fluency Game asset path: profile-driven reference/staging/approved folders, pink Pipa dragon identity constraints, optional 2D clips, generated audio, and the model3d GLB pipeline for `apps/math-quiz/dragon/assets/models/dragon.glb`.
- **Now** - Harden model3d scaffolding: Rodin/Meshy mesh caching, Blender rig/animation/export scripts, preview rendering, MCP launch, and GLB validation for required dragon clips.
- **Next** - Add image generation as a fourth media kind for stills and sprites using the existing request/provider/verifier pattern.
- **Next** - Add content-level judgement for music and sfx with an audio-understanding verifier instead of structural-only checks.
- **Next** - Add per-model presets or typed wrappers for provider schema quirks once repeated fal/Replicate model favorites emerge.
- **Next** - Build a small labeled eval set of good and broken outputs to measure verifier precision/recall and tune policy thresholds.
- **Later** - Reduce visual-verifier cost with frame montage/contact-sheet verification.
- **Later** - Support looping or boomerang export for sticker-style animations.
- **Later** - Grow profiles into a broader asset-production workflow for multiple consumer apps while keeping generated media local and gitignored.

## Idea inbox
- 2026-07-10 - Image generation media kind for stills and sprites.
- 2026-07-10 - Audio-understanding verifier for music and sound-effect content quality.
- 2026-07-10 - Provider/model presets for common schema quirks and favorite models.
- 2026-07-10 - Contact-sheet visual verification to lower vision-token cost.
- 2026-07-10 - Looping and boomerang export for short animation assets.
- 2026-07-10 - Labeled eval harness of clean and janky outputs for verifier threshold tuning.
