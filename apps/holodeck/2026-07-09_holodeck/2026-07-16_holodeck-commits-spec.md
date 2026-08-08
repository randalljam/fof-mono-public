file: 2026-07-16_holodeck-commits-spec.md
title: Holodeck turns database — commits ↔ AI exchanges, session labels, digests
last-updated: 2026-07-16_1540
ai: Claude Code - Fable 5 (fable5-w-codex orchestration)
session: `holodeck control center build`

# Holodeck turns database — build spec (branch feature/holodeck-commits)

User request 2026-07-16 (see `apps/holodeck/AI-SESSIONS.md` → "Randy Notes 2026-07-16_1427" for the verbatim voice prompt and the session-identifier taxonomy — READ IT). Two parallel, file-disjoint tasks.

## The domain (load-bearing facts from Randy)
- Randy is effectively the sole coder and writes no code by hand — **every commit results from an AI turn**.
- A **turn/exchange** = one (voice-dictated, often long, multi-part) user prompt + the AI's coding response. Short follow-ups exist but the primary prompts matter most. Response time 2–45 min.
- Exchange kinds matter: **primary** (long, feature-bearing), **quick** (short fix/tweak), **info** (question, no code intent).
- Commit patterns: Randy usually commits after each AI response; complex turns → agent groups work into several commits; several quick exchanges → one commit. A commit from >1 session is rare. Cloud Claude Code agents always commit+push themselves.
- Sessions come from multiple platform × interface × model combos; Randy thinks in his own labels (see taxonomy below).

## Shared contract A — turns database
SQLite at `apps/holodeck/data/turns.db` (gitignored). Owned by a new module set `apps/holodeck/turns/` (package: `db.py` schema+access, `ingest.py`, `correlate.py`, `digest.py`, `labels.py`) plus CLI `apps/holodeck/turns_cli.py`. Tables:
- `sessions(id TEXT PK, tool, source_path, project, worktree, branch, label, model, interface, title, started, last_activity, ingested_at)` — id = `<tool>:<native id>`.
- `exchanges(id TEXT PK, session_id FK, idx INT, kind TEXT CHECK(kind IN ('primary','quick','info')), user_ts, user_text, response_text, response_end_ts, follow_up_of TEXT NULL)` — id = `<session_id>#<idx>`.
- `commits(sha TEXT PK, branch, worktree, author, author_email, author_date, committer_date, subject, body, is_agent_commit INT)`.
- `links(exchange_id, sha, method TEXT, confidence REAL, PRIMARY KEY(exchange_id, sha))`.
- `digests(exchange_id PK, asked_json, notes_json, recap, model_used, created_at)`.
- `meta(key PK, value)` — schema_version, last_build times.
Rebuilds are idempotent upserts keyed on stable ids; never drop user data (digests persist across rebuilds).

## Shared contract B — session labels (`labels.py`, also applied to snapshot sessions layer)
Derive Randy's identifier strings. Verified raw fields:
- **Cursor** composerData: `modelConfig.modelName` (e.g. `composer-2.5`), `modelConfig.maxMode` bool, `selectedModels[].parameters` (e.g. `{id:"fast",value:"true"}`), `unifiedMode` (`agent`/`plan`/...), `planModeSuggestionUsed`.
  → `Cursor - <PrettyModel>[ High][ Fast][ K2]` + ` (.plan.md)` when unifiedMode=="plan" (planModeSuggestionUsed alone does NOT count). PrettyModel: `composer-2.5`→`Composer 2.5`, `grok-4.5-high-fast`→tokens split: model name words title-cased, `high`/`fast`/`max`/`1m` become suffix qualifiers (`High`, `Fast`, `K2`, `1M`).
- **Claude Code** JSONL: assistant lines carry `message.model` (e.g. `claude-fable-5`); local `~/.claude/projects` sessions are CLI-in-Cursor by definition (cloud app sessions don't sync to this store).
  → `Claude Code CLI (Cursor) - <PrettyModel>` (`claude-fable-5`→`Fable 5`, `claude-opus-4-8`→`Opus 4.8`, `claude-sonnet-5`→`Sonnet 5`; rule: strip `claude-`, title-case, dashes between digits→dots).
- **Codex** rollout JSONL: `session_meta.payload.originator` (`Codex Desktop` | `Claude Code` | terminal originators), latest `turn_context.payload.{model, effort}` (e.g. `gpt-5.6-sol`, `xhigh`).
  → originator `Codex Desktop` → `Codex App - <PrettyModel> <Effort>`; originator `Claude Code` → `Codex CLI (fable5-w-codex) - <PrettyModel> <Effort>`; otherwise → `Codex CLI (Cursor) - <PrettyModel> <Effort>`. PrettyModel: `gpt-5.6-sol`→`GPT 5.6 Sol`; Effort xhigh→`xhigh` as-is.
- Fallback when fields are missing: plain tool name (`Cursor`, `Claude Code`, `Codex`).
- The **snapshot sessions layer** gains `label` (and `model`, `interface` fields) computed with the same functions; keep existing fields untouched.

## Shared contract C — exchange segmentation, classification, correlation
Segmentation (per session, from ordered messages): a non-injected user message starts an exchange; subsequent assistant messages belong to it; its `response_end_ts` = last assistant ts before the next user message. A user message within 3 minutes of the previous exchange's last activity AND under 200 chars → follow-up: append to the same exchange (record `follow_up_of`), not a new one.
Classification heuristic (documented in code, easy to tune): `info` if the response contains no tool-use/code markers AND user text < 300 chars; `primary` if user text ≥ 400 chars OR response spans ≥ 10 messages; else `quick`.
Commit ingestion: for every worktree (reuse `git worktree list` collectors), `git log <branch> --since=60.days` with full bodies + author/committer emails/dates; `is_agent_commit` = 1 when the message contains a `Co-Authored-By: Claude` trailer or committer email is a bot/noreply address.
Correlation (per commit, on the same branch or worktree as the session — require branch match when both known, else worktree match):
1. **agent-window**: commit committer_date within [exchange.user_ts, next exchange's user_ts (or session last_activity + 10 min)] of an exchange in a session on that worktree → method `agent-window`, confidence 0.9.
2. **randy-after-response**: commit within 45 min after `response_end_ts` and before the next exchange's response window → method `after-response`, confidence 0.6.
3. Multiple candidate exchanges → link the latest one ≤ commit time; a commit may link to exchanges from ONE session only (pick the session with the closest response_end).
Unmatched commits stay unlinked (that's signal, not failure).

## Shared contract D — digests (LLM post-processing)
`digest.py`: for an exchange lacking a digest row, one LLM call producing STRICT JSON: `{"asked": ["<bullet>", ...3-6], "notes": ["<bullet>", ...0-5], "recap": "<1-2 sentences>"}`.
- Prompt (develop it carefully): system role "You summarize one AI-coding exchange for the repo owner's dashboard"; instructions: bullets are terse, concrete, digestible at a glance; `asked` = what Randy asked for (features, fixes, changes); `notes` = important non-obvious info from the response (build details, caveats, decisions, test results); `recap` = prefer the response's own recap/TL;DR text when one exists (models often put it at the start or end) — extract/tighten it rather than re-summarize. Input: user_text (cap 6k chars) + response_text (cap 24k chars: keep the FIRST 6k and LAST 18k when longer — recaps live at the ends).
- Keys via dotenv from repo `.env`: prefer `ANTHROPIC_API_KEY_LOCAL` → anthropic SDK, model `claude-haiku-4-5-20251001`; else `OPENAI_API_KEY_LOCAL` → openai SDK, model `gpt-5-mini`. No key → skip gracefully with a clear message. Record `model_used`. Retry once on JSON parse failure with a "return ONLY the JSON" nudge.
- NEVER auto-digest in bulk during collect: digests run only from the CLI `--digest` flag or the on-demand API endpoint. CLI `--digest --limit N` (default 20, newest primary exchanges first).

## Shared contract E — API
- `GET /api/turns?branch=<b>&limit=<n=20>` → exchanges (newest first, primary first within same time bucket) for sessions matched to that branch/worktree: `{exchanges: [{id, session_id, session_label, kind, user_ts, user_preview (300 chars), has_digest, digest: {asked, notes, recap}|null, commits: [{sha, subject, author_date, is_agent_commit}]}]}`.
- `GET /api/turns/exchange/{id}` → full user_text + response_text + digest + commits.
- `POST /api/turns/refresh` → runs ingest+correlate (subprocess or thread, REFRESH_LOCK-style guard) — no digests.
- `POST /api/turns/digest/{exchange_id}` → generate digest for one exchange on demand (this is what the UI calls when a digest is missing); 409 if already running, clear error if no API key.
- Session-id sanitization as with existing endpoints; exchange ids validated against the DB.

## Task 1 — backend (owns apps/holodeck/turns/, turns_cli.py, collectors/sessions.py label additions, server.py, tests/, README.md)
- Implement contracts A–E. `sessions.py`: extract raw label inputs (cursor modelConfig/unifiedMode; claude message.model; codex originator/turn_context) into the parsed session dicts + compute `label` via labels.py (import from apps.holodeck.turns.labels with the same try/except pattern used elsewhere).
- The turns pipeline REUSES sessions.py reader functions (full messages) — do not duplicate store-parsing logic; refactor shared helpers if needed.
- Tests (fixtures, no network, no real HOME): label derivation for all three tools incl. plan-mode and fable5-w-codex cases; segmentation (follow-up folding); classification; correlation (agent-window, after-response, unmatched); digest JSON parsing + long-response truncation windowing (mock the SDK call); DB idempotent re-ingest (no dupes, digests preserved). Keep all existing tests green.
- README: turns DB section (what it is, CLI usage, digest key requirements, endpoints).
- Style rules as always (no type hints, no blank lines between functions, `###` headers). New deps allowed: none beyond anthropic/openai/dotenv already in venv.

## Task 2 — frontend (owns apps/holodeck/web/ only)
1. **Status panel rows**: replace the interface pill + left time with: the latest session's **label** (e.g. `Cursor - Composer 2.5 Fast`, `Claude Code CLI (Cursor) - Fable 5`) as the badge (keep tool color coding by tool), and the **relative time to the RIGHT of the label badge**. Keep worktree chip + first open next step.
2. **Worktree card session rows**: show the session `label` (falls back to tool name) instead of bare tool name; time stays on the right (already right-aligned there — keep). Tooltip + click-through unchanged.
3. **AI Sessions section rows**: add the label as the primary identifier (tool dot keeps color).
4. **Exchange digest drawer**: clicking a session (from Status, card, or AI Sessions) now opens the session drawer with a new **Turns view on top**: fetch `GET /api/turns?branch=...` filtered client-side to that session (or add `&session=` param if backend provides — check the contract; filtering client-side is fine), render each exchange as: kind pill (primary gold / quick muted / info teal), user_ts relative, **Asked** bullets, **Notes** bullets, *recap* line (italic, prominent), linked commits (mono sha + subject, agent-commit tag when set). If `has_digest` false → a `Summarize` button calling `POST /api/turns/digest/{id}` with spinner, then re-render. A `Full response` expander per exchange fetches `/api/turns/exchange/{id}` and shows complete text (reuse message styling). Below the turns view, keep the existing raw message list (collapsed under a `<details>` "All messages").
5. Sample mode: add `sample-turns.json` consumed when `?src=sample` (2 exchanges with digests, one without, linked commits) — no fetches.
6. Null-safe, escape everything, keep stable ids, keep tests green.

## Acceptance
- `turns_cli.py build` ingests real sessions+commits and correlates: the holodeck-start worktree must show recent exchanges linked to recent holodeck commits.
- `turns_cli.py build --digest --limit 3` produces 3 digests with real API keys (run it once for real; report cost-relevant sizes).
- Labels: a recent Cursor session shows `Cursor - Composer 2.5 Fast...`; a codex delegation from this session shows `Codex CLI (fable5-w-codex) - ...`; this Claude session shows `Claude Code CLI (Cursor) - Fable 5`.
- UI: Status shows label + time-on-right; digest drawer renders bullets/recap/commits and the Summarize button works live.
- All tests green; both tasks report files changed, verification, deviations.
