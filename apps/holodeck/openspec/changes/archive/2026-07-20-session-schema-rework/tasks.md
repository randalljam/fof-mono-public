# Tasks: session-schema-rework

- [x] tool->platform, entrypoint cli/app/subagent, host local/cloud across parsers/DB/labels
- [x] Remote Control detection (JSONL bridge-session + app bridgeSessionIds) -> remote_control + bridge_session_id
- [x] In-place DB migration (rename + columns + legacy normalization, schema v5)
- [x] Delegation/subagent/cloud logic updated to new fields; frontend filters + cloud/RC tags
- [x] 143 tests green; RC fixtures verified (7224a4fe, fdbf0bdb); zero old field values
