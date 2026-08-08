file: skills/media/consumer-chat-md/README.md
title: Consumer chat → markdown (ChatGPT + Claude.ai)
source-github-url: original
source-guide-url: original
history:
  - 2026-07-27 · Randy · Cursor — mark WIP; document Claude Playwright reuse vs ChatGPT/Codex gap
  - 2026-07-25 · Randy · Cursor [Consumer chat markdown](consumer_chat_markdown_8d9347d0) — initial skill for selected consumer chat export

**Status: WORK IN PROGRESS.** Scaffold + fixture tests only. **Never run live end-to-end** on real ChatGPT/Claude.ai chats. Not connected to Holodeck `turns.db` or the dashboard. Intended direction: ask an agent for named chats and have them fetched automatically (reusing Holodeck's Claude Playwright login where possible); that automatic path is **not built yet**. Today's path is still manual: you supply a share URL, saved HTML, Claude console JSON, or pasted markdown, then run the CLI.

**Export selected consumer ChatGPT and Claude.ai chats to markdown for agent context.**

Holodeck's sessions/turns layers cover AI **coding** tools only. This skill is meant to pull individual **consumer** chats and write house-format markdown locally — not into `turns.db`.


## Why not Holodeck's existing cloud login?
**Short version:** Claude coding cloud auth ≈ reusable for consumer chats, unfinished. Codex cloud auth ≠ ChatGPT consumer chats. Automatic "get me those chats" is the intended end state; not built, never run live.

Your intuition is mostly right — for Claude.

Holodeck *does* log into Claude via Playwright and pull cloud **coding** sessions. That login is real. What it calls today is `/v1/code/sessions` — Claude Code cloud VMs — not consumer Claude.ai chats.

Consumer chats are a different API on the same site: `chat_conversations`. Same browser cookie would almost certainly work (the console snippet already uses your logged-in tab). v1 just never wired Playwright to that endpoint; it stopped at "you export, CLI converts."

**ChatGPT is different.** Holodeck's Codex cloud path uses the Codex CLI token against coding **tasks** (`wham/tasks`). That is not general ChatGPT web/iPhone chat history. So "reuse the same login for ChatGPT consumer chats" is not already set up the way Claude coding-session login is.

| Surface | Holodeck auth today | API Holodeck calls | Consumer chats? |
|---------|---------------------|--------------------|-----------------|
| Claude Code cloud | Playwright `~/.holodeck/playwright-claude` | `/v1/code/sessions` | No — different product API: `chat_conversations` |
| Codex cloud | `~/.codex/auth.json` | ChatGPT `wham/tasks` | No — coding tasks, not ChatGPT web/iPhone chats |


## When to use
- You need one or a few ChatGPT or Claude.ai research chats as markdown for Cursor/agent context
- You do **not** want a full conversation database or Holodeck dashboard ingest
- You already have a ChatGPT **share link**, saved share HTML, Claude browser export JSON, or Hermes-style pasted markdown
- Expect to babysit the export steps — automatic "get me that chat" is the goal, not current behavior


## Dependencies
Uses repo `.venv` and existing `core/conversion.py` for ChatGPT share pages. No extra pip packages beyond what the monorepo already installs (`beautifulsoup4`, `requests`, etc.).


## Quick start

### ChatGPT (share link)
```bash
.venv/bin/python3 skills/media/consumer-chat-md/scripts/consumer_chat_md.py \
  --chatgpt-share 'https://chatgpt.com/share/...' \
  --out-dir "$FOF_MONO_LOCAL_FILES_ROOT/consumer-chats"
```

### ChatGPT (saved HTML)
```bash
.venv/bin/python3 skills/media/consumer-chat-md/scripts/consumer_chat_md.py \
  --chatgpt-html ~/Downloads/chatgpt-share.html
```

### Claude.ai (browser export)
1. Run the console snippet in [`references/claude-console-export.md`](references/claude-console-export.md)
2. Convert the downloaded JSON:

```bash
.venv/bin/python3 skills/media/consumer-chat-md/scripts/consumer_chat_md.py \
  --claude-json ~/Downloads/holodeck-claude-chat-*.json \
  --select 'speech recognition'
```

### Combine two chats (e.g. ChatGPT + Claude on the same topic)
```bash
.venv/bin/python3 skills/media/consumer-chat-md/scripts/consumer_chat_md.py \
  --chatgpt-share 'https://chatgpt.com/share/...' \
  --claude-json ~/Downloads/holodeck-claude-chat-*.json \
  --select 'metrics' \
  --combine \
  --topic 'speech-recognition-benchmarks'
```

## CLI options

| Flag | Purpose |
|------|---------|
| `--chatgpt-share URL` | Fetch public ChatGPT share page (repeatable) |
| `--chatgpt-html PATH` | Saved share HTML file or glob |
| `--chatgpt-md PATH` | Existing numbered User/Assistant markdown |
| `--claude-json PATH` | Browser export JSON or glob |
| `--pasted-md PATH` | Pasted markdown in house format |
| `--select TEXT` | Comma-separated title/id filter for Claude JSON |
| `--claude-id ID` | Exact Claude conversation id (repeatable) |
| `--combine` | Also write one combined markdown file |
| `--topic TEXT` | Combined file title/slug |
| `--out-dir PATH` | Output dir (default: `$FOF_MONO_LOCAL_FILES_ROOT/consumer-chats`) |

## Output
- Default directory: `~/Documents/Code/_LOCAL_FILES/fof-mono/consumer-chats/` (override with `FOF_MONO_LOCAL_FILES_ROOT`)
- Format spec: [`references/markdown-format.md`](references/markdown-format.md)
- Files are local-only (gitignored via `_LOCAL_FILES`); not archived to S3 in v1

## Tests
```bash
.venv/bin/python3 -m pytest skills/media/consumer-chat-md/tests -q
```

## Related Holodeck docs
- Coding-session limits: [`apps/holodeck/AI-SESSIONS.md`](../../../apps/holodeck/AI-SESSIONS.md) — consumer chats section points here
- ChatGPT share converter source: [`core/conversion.py`](../../../core/conversion.py)
