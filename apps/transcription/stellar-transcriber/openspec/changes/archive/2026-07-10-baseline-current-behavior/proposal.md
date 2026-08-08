# Baseline Current Behavior

## Why
This is the first OpenSpec baseline for Stellar Transcriber. The app already has working scripts, config, reference reports, and root-level tests, but no living spec that states what the current app does.

## What Changes
- Capture the current observable behavior of the app in one `app` capability.
- Cover the existing corpus inventory, S3 fetch, eval scoring, draft generation, alignment ladder, aggregation, M3B scoring, and review-bundle workflows.
- Archive this baseline into the living spec so future changes can be proposed against it.

## Non-Goals
- No behavior changes.
- No roadmap items or desired future behavior.
- No new tests or implementation work.
