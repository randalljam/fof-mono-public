# Baseline Current Behavior
## Why
Focus on Foundations is already deployed on staging and production, but it has no OpenSpec baseline. This change creates the first single-capability spec so future site, QRAG demo, transcript, redirect, and deploy changes can be compared against the behavior that exists today.

## What Changes
- Capture the current public Astro site behavior under one capability named `app`.
- Document current QRAG demo UI behavior, transcript corpus pages, legacy redirects, legal pages, and AWS static hosting/deploy mechanics.
- Establish the baseline through an archived OpenSpec change before future behavior proposals are added.

## Non-Goals
- No code or behavior changes.
- No roadmap commitments in the spec.
- No split into multiple capabilities at this S2-deployed/single-spec stage.
- No changes to QRAG Lambda backend algorithms, vector indexes, corpus data, DNS, or AWS resources.
