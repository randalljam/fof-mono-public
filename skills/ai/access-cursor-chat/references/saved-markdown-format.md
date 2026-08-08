file: skills/ai/access-cursor-chat/references/saved-markdown-format.md
title: Access Cursor Chat — saved markdown format
source-github-url: original
source-guide-url: original
history:
  - 2026-07-10 · Randy · Cursor [Access Cursor Chat](access-cursor-chat) — documented the saved transcript example format


This reference shows the saved markdown shape used by `skills/ai/access-cursor-chat/scripts/format_cursor_chat.py`. The full worked example lives at `skills/ai/access-cursor-chat/references/cursor-export-example/2026-07-10_0706_cursor_auto_learner_spec_access.md`. The raw Cursor UI export for the same chat is at `skills/ai/access-cursor-chat/references/cursor-export-example/cursor_auto_learner_spec_access.md`.


## Shape
```markdown
file: 2026-07-10_0706_cursor_auto_learner_spec_access.md
title: Auto learner spec access - prep for fable5 update
last-updated: 2026-07-10_0706
session: `Auto learner spec access`
_Exported on 7/10/2026 at 07:18:17 PDT from Cursor (3.10.20)_

# User
User prompt text.

# Cursor
ai: gpt-5.5
Cursor response text.
```


## Notes
- `last-updated` is the chat's last-response timestamp when available, otherwise the transcript file mtime.
- `ai:` comes from Cursor `state.vscdb` when available, otherwise `unknown`.
- User prompts should usually be the visible prompt only, not Cursor's attached context wrapper.
