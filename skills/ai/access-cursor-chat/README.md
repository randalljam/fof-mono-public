file: skills/ai/access-cursor-chat/README.md
title: Access Cursor Chat
source-github-url: original
source-guide-url: original
history:
  - 2026-07-10 · Randy · Cursor [Access Cursor Chat](access-cursor-chat) — enrich saved markdown with model names from Cursor state.vscdb
  - 2026-07-10 · Randy · Cursor [Access Cursor Chat](access-cursor-chat) — initial skill for locating Cursor transcripts and formatting saved chat markdown


Use this skill when the user asks to access, read, summarize, cite, or save a prior Cursor chat by chat name, transcript UUID, worktree, or "latest in this worktree." The goal is to pull the whole chat, including user prompts and agent responses, so another agent session can use it as context.


## What This Skill Does
- Finds Cursor chat transcripts for a worktree from Cursor's local `agent-transcripts` store when available.
- Falls back to a user-supplied Cursor markdown export when the local transcript cannot be found.
- Reads raw transcript context directly when the user only needs another agent to use it.
- Saves a reformatted markdown transcript only when the user asks to save/export it.
- Uses the repo-preferred saved format shown in `skills/ai/access-cursor-chat/references/cursor-export-example/2026-07-10_0706_cursor_auto_learner_spec_access.md`.


## Inputs The User May Give
- **Latest in this worktree**: resolve the current worktree's Cursor transcript folder and pick the newest `.jsonl` transcript.
- **Chat name or phrase**: search transcript filenames and content for the phrase, then choose the newest match.
- **Transcript UUID**: search for a matching UUID-named `.jsonl` file under Cursor's project transcript folders.
- **Worktree path**: use that path to derive Cursor's project folder token.
- **Exported markdown file**: parse Cursor's built-in export format and re-render it.

If multiple matches are plausible, stop and ask which chat to use before reading or saving.


## Local Sources
Cursor local transcript paths are machine-local and not repo-tracked. In this workspace, the active pattern is:

```text
~/.cursor/projects/<worktree-token>/agent-transcripts/<uuid>/<uuid>.jsonl
```

Model metadata is not stored in those JSONL files. When saving markdown, the formatter also reads Cursor's global SQLite store:

```text
~/Library/Application Support/Cursor/User/globalStorage/state.vscdb
```

Relevant keys in table `cursorDiskKV`:

| Key | Field | Purpose |
|-----|-------|---------|
| `composerData:<uuid>` | `modelConfig.modelName` | Session-level model fallback |
| `bubbleId:<uuid>:<bubbleId>` | `modelInfo.modelName` | Per-response model when Cursor recorded it |

The `<worktree-token>` is the absolute worktree path with `/` replaced by `-`, without the leading slash. For example:

```text
/Users/randytrue/Documents/Code/example
→ Users-randytrue-Documents-Code-example
```

Cursor may also provide a manual markdown export from the UI. Use that export when the local JSONL is unavailable, incomplete, or from another machine.


## Read-Only Access Procedure
Use this path when the user only wants the chat used as context and did not ask for a saved markdown file.

1. Identify the intended transcript from the user's phrase, UUID, worktree, or "latest" request.
2. Read the `.jsonl` transcript directly with `ReadFile`, or use `rg` to locate a phrase first.
3. Extract the visible user prompts from `<user_query>...</user_query>` blocks when present.
4. Extract assistant text blocks from `message.content` entries with `type: "text"`.
5. Ignore tool-use objects unless the user specifically asks for tool traces.
6. If citing the chat to the user, cite parent chat transcripts as `[<title <=6 words>](<uuid>)`.

Do not save a file in this procedure.


## Save As Markdown Procedure
Use this path only when the user asks to export, save, write, or reformat a chat as markdown.

1. Confirm the transcript identity before writing if the request is ambiguous.
2. Run the formatter:

```bash
.venv/bin/python3 skills/ai/access-cursor-chat/scripts/format_cursor_chat.py --input <transcript-or-export> --output <output.md>
```

For the latest transcript in a worktree:

```bash
.venv/bin/python3 skills/ai/access-cursor-chat/scripts/format_cursor_chat.py --worktree <worktree-path> --latest --output <output-folder>
```

For a chat name or phrase:

```bash
.venv/bin/python3 skills/ai/access-cursor-chat/scripts/format_cursor_chat.py --worktree <worktree-path> --query "<chat name or phrase>" --output <output-folder>
```

3. Use the output path printed by the script as the saved transcript path.
4. Read the saved file briefly to verify that the metadata, `# User`, and `# Cursor` sections look right.


## Saved Markdown Format
Saved markdown starts with metadata:

```markdown
file: YYYY-MM-DD_HHMM_slug.md
title: Human-readable title
last-updated: YYYY-MM-DD_HHMM
session: `Cursor chat title`
_Exported on ... from Cursor (...)_
```

Then each turn is rendered with level-one headings:

```markdown
# User
User prompt text.

# Cursor
ai: <model name or unknown>
Agent response text.
```

`last-updated` should use the chat's last-response time if available. If Cursor does not expose that value, use the transcript file's modified time. The formatter does this automatically for JSONL inputs.

For `# Cursor` blocks, the formatter looks up model names from `state.vscdb`:

1. Per-response `modelInfo.modelName` from grouped assistant bubbles when present.
2. Otherwise `composerData.modelConfig.modelName` for the session.
3. Otherwise `ai: unknown`.

Do not guess a model name.


## Formatter Details
The script is stdlib-only and supports:

- Cursor `agent-transcripts` JSONL.
- Cursor `globalStorage/state.vscdb` model lookup via composer UUID or session title.
- Cursor UI markdown exports with `**User**` / `**Cursor**` sections.
- Explicit output files or output directories.
- `--title`, `--session`, `--last-updated`, `--exported-line`, and `--state-db` overrides.
- `--raw-user-context` when the caller wants Cursor's attached context wrappers preserved.

Default behavior extracts only the visible `<user_query>` text from user messages so saved transcripts resemble Cursor's UI export instead of including attached system context.


## Verification
Run the eval after changing the formatter:

```bash
.venv/bin/python3 skills/ai/access-cursor-chat/eval/test_format_cursor_chat.py
```

The eval uses temporary files and does not write transcripts into the repo.
