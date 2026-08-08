# Baseline Current Behavior
## Why
Math Quiz has deployed behavior across the anchor fluency app, legacy quiz pages, analysis dashboards, local SQLite tooling, and the dragon motivation layer, but it did not have an OpenSpec baseline. This change creates the first spec baseline so future work can distinguish shipped behavior from planned changes.
## What Changes
- Capture the current observable app behavior in one `app` capability.
- Cover the active kid/coach anchor flow, SQLite save/load lifecycle, fluency computation, targeted practice, problem-list workflows, analysis and fluency dashboards, legacy quiz behavior, local dev-server APIs, and dragon game behavior.
- Archive the baseline into the living spec after strict validation.
## Non-goals
- No behavior changes.
- No roadmap or aspirational requirements in the living spec.
- No capability split beyond the single `app` capability.
