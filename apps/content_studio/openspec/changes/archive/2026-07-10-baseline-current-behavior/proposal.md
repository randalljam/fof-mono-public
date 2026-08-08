# Baseline Current Behavior
## Why
Content Studio has working media-generation, verification, provider, profile, and model3d behavior, but no OpenSpec baseline. This change captures the current observable behavior in a single `app` capability so future changes have a stable contract to update.
## What Changes
- Add the first OpenSpec baseline for `apps/content_studio`.
- Capture current animation, video, audio, verification, provider, CLI, profile, and model3d behavior.
- Keep the baseline focused on behavior that exists in code, docs, tests, and branch history today.
## Non-Goals
- No application behavior changes.
- No roadmap or aspirational requirements in the living spec.
- No split into narrower capabilities during S1 development.
