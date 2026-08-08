# Initial Build — Worldview Mirror + Atlas

## Why
Use cases #1 (Worldview Mirror) and #2 (Worldview Atlas) from `apps/deutsch/deutsch-graph/docs/use-cases.md` are the first downstream consumers of the deutsch-graph. They are built together because the Atlas taxonomy is what the Mirror classifies user beliefs against, and Deutsch's graph-cited profile is what makes the atlas format concrete.

## What Changes
- Create the app: engine package (`wvmirror/`), CLI (`run_mirror.py`), local FastAPI server, and hand-authored web UI.
- Author the research-grounded Worldview Atlas taxonomy: 14 axes (`taxonomy/axes.jsonl`) and 9 named profiles, with `deep-optimism.json` fully cited to deutsch-graph node ids (the L5 seed).
- Implement the mirrored-conversation pipeline (route+extract -> graph grounding -> tone-controlled cited reply), the transparent editable user profile, local thread storage, and user-vs-lens comparison.
- Establish the v1 "basic" security baseline (localhost + session token + local files + safety framing) with the confidentiality ladder documented as placeholders.
- Capture the built behavior in the baseline `app` capability spec.

## Non-Goals
- No accounts, server-side thread storage, client-side encryption, or no-retention inference (explicit placeholders).
- No divergence-detection service, clip cutting, TTS, or deployment.
- No L5 overlay export back into deutsch-graph until that layer's format lands.
