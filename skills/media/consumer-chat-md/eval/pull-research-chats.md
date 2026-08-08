file: skills/media/consumer-chat-md/eval/pull-research-chats.md
title: Pull speech-recognition / metrics research chats

Run these after you have the two target consumer chats available.

## ChatGPT (share link)
1. Open the speech-recognition / metrics thread in ChatGPT.
2. Share → copy link.
3. Export:

```bash
.venv/bin/python3 skills/media/consumer-chat-md/scripts/consumer_chat_md.py \
  --chatgpt-share 'https://chatgpt.com/share/<your-id>' \
  --out-dir "$FOF_MONO_LOCAL_FILES_ROOT/consumer-chats"
```

## Claude.ai (browser export)
1. Follow [`../references/claude-console-export.md`](../references/claude-console-export.md).
2. When prompted, enter a title substring such as `speech recognition` or `metrics`.
3. Export:

```bash
.venv/bin/python3 skills/media/consumer-chat-md/scripts/consumer_chat_md.py \
  --claude-json ~/Downloads/holodeck-claude-chat-*.json \
  --select 'speech recognition,metrics' \
  --out-dir "$FOF_MONO_LOCAL_FILES_ROOT/consumer-chats"
```

## Combined markdown (both chats)
```bash
.venv/bin/python3 skills/media/consumer-chat-md/scripts/consumer_chat_md.py \
  --chatgpt-share 'https://chatgpt.com/share/<your-id>' \
  --claude-json ~/Downloads/holodeck-claude-chat-*.json \
  --select 'speech recognition,metrics' \
  --combine \
  --topic 'speech-recognition-benchmarks' \
  --out-dir "$FOF_MONO_LOCAL_FILES_ROOT/consumer-chats"
```

Expected outputs under `$FOF_MONO_LOCAL_FILES_ROOT/consumer-chats/`:
- `YYYY-MM-DD_chatgpt_<slug>.md`
- `YYYY-MM-DD_claude_<slug>.md`
- `YYYY-MM-DD_speech-recognition-benchmarks_combined.md`

Then `@` the combined file (or either single file) in Cursor for context.
