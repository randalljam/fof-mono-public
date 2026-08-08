# Tasks: turns-database

- [x] turns.db schema + idempotent ingest (sessions, exchanges, commits)
- [x] Exchange segmentation, follow-up folding, primary/quick/info classification
- [x] Correlation: agent-window and after-response links with confidence
- [x] Session labels from Cursor/Claude/Codex store metadata; snapshot label field
- [x] Digest worker (asked/notes/recap, recap-preferring prompt, key fallback) + CLI
- [x] API: /api/turns, exchange detail, refresh, per-exchange digest
- [x] UI: label badges with right-side time; Turns digest drawer with Summarize
- [x] Review fixes: codex line timestamps, auto-review exclusion, has_digest join
- [x] Live verification: 322 exchanges, 119 links, 3 real digests, correct linkage
