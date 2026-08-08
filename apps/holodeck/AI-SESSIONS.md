## AI session retrieval
Holodeck's **sessions** layer reads recent AI coding conversations from three local stores — Cursor, Claude Code, and OpenAI Codex — and normalizes them into one list in `apps/holodeck/data/snapshot.json`. Implementation lives in `apps/holodeck/collectors/sessions.py`.

Collection runs as part of `collect.py` (or `POST /api/refresh` with `{"layers": ["sessions"]}`). Each tool collector:

- scans only files modified in the last **30 days**
- keeps sessions whose project path matches a known git worktree path or the configured fallback repo (`/Users/randytrue/Documents/Code/fof-mono`)
- sorts by `last_activity` descending
- returns at most **40** sessions per tool

The dashboard shows summary rows (title, branch, message count, first/last user preview). Full message text is loaded lazily via `GET /api/sessions/{tool}/{session_id}` once the session is already present in the current snapshot. Preview strings in the snapshot are truncated to 240 characters; drawer detail is not truncated.

Session content never enters git. The Cursor database is opened **read-only** (`?mode=ro`).


## Normalized Holodeck session object
Every collected session becomes the same shape regardless of source tool:

| Field | Meaning |
|-------|---------|
| `tool` | `cursor`, `claude-code`, or `codex` |
| `id` | Stable session identifier (composer UUID, Claude filename stem, or Codex session id) |
| `title` | Human-readable thread title when available |
| `entrypoint` | Client that created the session (see **Entrypoint** below); `null` when unknown |
| `project` | Absolute path to the working directory when the session ran |
| `worktree` | Matched git worktree path, if any |
| `branch` | Git branch recorded in the session or inferred from the matched worktree |
| `started` | ISO timestamp of first activity |
| `last_activity` | ISO timestamp of most recent activity |
| `messages` | Count of user + assistant turns Holodeck recognized |
| `first_user` | Preview of the first real user message (injected/system stubs skipped) |
| `last_user` | Preview of the last real user message |
| `source_path` | Where to reload detail: JSONL file path for Claude/Codex; composer id for Cursor |

Detail responses use a separate message list:
```json
{"messages": [{"role": "user|assistant", "text": "...", "ts": "ISO-or-null"}]}
```
Up to 200 messages are returned per request.


## Entrypoint
Holodeck adds an `entrypoint` field to every session row, using Claude Code's terminology where possible. Values are extracted from the last 30 days of local session files; older sessions may have `entrypoint: null`.

| Tool | Source field | Holodeck `entrypoint` values |
|------|--------------|------------------------------|
| Claude Code | `entrypoint` on the first `user` JSONL line | Passed through as-is — observed: `cli`, `claude-desktop` |
| Codex | `session_meta.payload.source` + `originator` + `thread_source` | Normalized: `codex-cli`, `codex-desktop`, `codex-subagent`, `codex-vscode` |
| Cursor | N/A (always the Cursor IDE) | `cursor` |

Codex normalization rules in `collectors/sessions.py` (stored as `cli` / `app` / `subagent`; labels say Codex CLI / Codex App / Codex Subagent):

- `source: exec` or `originator: codex_exec` → `cli`, origin **delegated** (fable5-w-codex machinery; hidden unless Machinery filter is on)
- `source: cli` or `originator: codex-tui` → `cli`, origin **operator** (interactive Codex CLI TUI; visible in AI Sessions as `Codex CLI`)
- `originator: Codex Desktop` or `codex_work_desktop` (user thread) → `app`, origin operator
- `thread_source: subagent` or dict `source` → `subagent`, origin delegated
- `source: vscode` + `originator: Claude Code` → `cli`, origin delegated (rare cross-label case)

### Web, iPhone, and desktop sync
Holodeck only reads **local on-disk** session logs on the Mac where `collect.py` runs. It does not call cloud APIs.

**Claude Code** (`~/.claude/projects/*.jsonl`): A full survey of local files on this machine shows only two entrypoints — `cli` (terminal) and `claude-desktop` (macOS Claude Code app). No `claude-ios`, `claude-web`, or similar values appear in the JSONL. Consumer Claude chat (claude.ai web and iPhone app) syncs across devices in Anthropic's cloud, but those conversations are a **different product surface** from Claude Code coding sessions; they do not write into `~/.claude/projects` on this Mac. If Anthropic later adds mobile or web entrypoints to the local JSONL format, Holodeck will pass them through unchanged.

**Codex** (`~/.codex/sessions/**/rollout-*.jsonl`): Local rollouts distinguish CLI (`codex-cli`) from desktop/VS Code integration (`codex-desktop`). ChatGPT web and iPhone Codex threads sync in OpenAI's cloud but do not populate `~/.codex/sessions` locally — Holodeck cannot see them.

The dashboard's per-worktree **Primary AI interface** pulldown remains a separate manual field in `state.json`; `entrypoint` on session rows is inferred from session files, not from that pulldown.


## Consumer ChatGPT and Claude.ai chats (not in Holodeck sessions)
Holodeck's **sessions** and **turns** layers do **not** ingest consumer ChatGPT web/iPhone chats or Claude.ai web/iPhone chats. Those threads sync in vendor cloud and never land in `~/.codex/sessions` or `~/.claude/projects`.

**WIP skill (not live end-to-end):** [`skills/media/consumer-chat-md/README.md`](../../skills/media/consumer-chat-md/README.md) — scaffold + fixture tests only; never proven on real chats; not wired into Holodeck. Goal is automatic fetch of named chats; today you still supply share URL / Claude console JSON / pasted markdown to the CLI.

Holodeck's Claude Playwright login and Codex CLI token cover **coding** cloud sessions (`/v1/code/sessions`, `wham/tasks`), not consumer chat history. Claude consumer chats use `chat_conversations` — same browser cookie could work, but that path is not built yet.


## Cursor
### Where messages live
Cursor stores agent/chat state in a **SQLite** database:

`~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`

Holodeck opens it read-only and queries the `cursorDiskKV` table — a simple key/value store (not a normalized messages table).

### Storage format
Two key patterns hold conversation data:

| Key pattern | Contents |
|-------------|----------|
| `composerData:{composerId}` | JSON blob: session metadata, workspace association, ordered message headers |
| `bubbleId:{composerId}:{bubbleId}` | JSON blob: full text and rich metadata for one message bubble |

The `composerData` JSON includes fields such as `composerId`, `name` (title), `createdAt`, `lastUpdatedAt`, `workspaceIdentifier`, and `fullConversationHeadersOnly` (an ordered list of `{type, bubbleId}` entries). Holodeck reads message bodies by following those bubble ids into `bubbleId:…` rows and extracting `text` / `content` / `message` from the bubble JSON.

Header `type` values map to roles:

- `1` → user
- `2` → assistant

### Tracked by window?
**No.** Sessions are tracked by **composer thread** (`composerId`), not by Cursor window. A composer row may carry a `workspaceIdentifier.uri.path` (or `fsPath`) tying the thread to a folder, and Holodeck uses that path to match a git worktree — but that is project association, not live window identity.

Whether a worktree currently has an open Cursor window is a **separate** concern handled by the **worktrees** layer, which reads `windowsState.openedWindows` from Cursor's `storage.json`. That `cursor_open` flag drives the "open in Cursor" focus button; it does not select or filter session rows.

### Timestamps
- Session-level: `createdAt` and `lastUpdatedAt` on the composer row (epoch milliseconds → local ISO).
- Per-message: bubble JSON may include `createdAt`, but Holodeck's detail reader does **not** surface per-message timestamps today (`ts` is `null` in drawer messages).

### Fields Holodeck stores per Cursor session
From the normalized object above: `tool`, `id`, `title`, `project`, `worktree`, `branch`, `started`, `last_activity`, `messages`, `first_user`, `last_user`, `source_path` (the composer id).

`first_user` / `last_user` previews are fetched only for the **15** most recent matching sessions (extra SQLite lookups per user bubble).

### Raw Cursor fields Holodeck does not use
Composer and bubble JSON carry many additional fields (`relevantFiles`, `capabilities`, `richText`, `modelConfig`, `usageData`, tool results, etc.). Holodeck ignores them for inventory and detail.

### Scrubbing a deleted Cursor chat from Holodeck
Deleting a chat in Cursor History removes it from `state.vscdb`, so the next sessions collect will not re-list it. It does **not** remove rows already copied into Holodeck (`turns.db`, `snapshot.json`). Use the standalone scrubber (not wired into collect/build/refresh):

```bash
# Dry-run (default): confirm gone from Cursor + show Holodeck traces
.venv/bin/python3 apps/holodeck/turns_cli.py purge-cursor <composer-uuid>

# Permanently delete Holodeck copies and verify
.venv/bin/python3 apps/holodeck/turns_cli.py purge-cursor <composer-uuid> --execute

# Optional: also remove matching ~/.cursor/projects/*/agent-transcripts files
.venv/bin/python3 apps/holodeck/turns_cli.py purge-cursor <composer-uuid> --execute --agent-transcripts

# Scan every cursor session in turns.db and purge those absent from Cursor
.venv/bin/python3 apps/holodeck/turns_cli.py purge-cursor --all-missing --execute
```

Implementation: `apps/holodeck/turns/purge_cursor.py` (`purge_deleted_cursor_session`). Refuses if `composerData:{id}` still exists unless `--force`. Cascades exchanges/digests/links via FK; clears `parent_session_id` on child sessions; leaves git `commits` rows intact.


## Claude Code
### Where messages live
Claude Code writes **JSONL** session logs under:

`~/.claude/projects/<encoded-project-path>/*.jsonl`

Project folders are named from the absolute cwd with slashes replaced (for example `-Users-randytrue-Documents-Code-feature-holodeck-start`). Each file is one session; the filename stem (UUID) is the session `id`.

### Storage format
**JSONL** — one JSON object per line. Record `type` drives parsing:

| `type` | Holodeck use |
|--------|----------------|
| `user` | User turn; content from `message.content` |
| `assistant` | Assistant turn; content from `message.content` |
| `ai-title` | Thread title (`title` field) |
| Other (`mode`, `permission-mode`, `file-history-snapshot`, …) | Ignored for session inventory |

### Typical fields on `user` / `assistant` lines
| Field | Meaning |
|-------|---------|
| `type` | `user` or `assistant` |
| `timestamp` | ISO-8601 time for this message |
| `cwd` | Working directory (used to match repo worktrees) |
| `gitBranch` | Git branch at send time |
| `message` | `{content: string or block array}` |
| `sessionId`, `uuid`, `parentUuid` | Claude internal threading |
| `entrypoint` | Client that sent the message (see below) |
| `userType`, `version`, `promptId`, … | Additional Claude metadata |

Holodeck uses `type`, `timestamp`, `cwd`, `gitBranch`, `message`, and `ai-title`. It skips injected/system-looking user text (lines starting with `<`, `[SYSTEM NOTIFICATION`, etc.) when building `first_user` / `last_user` previews.

### Tracked by window?
**No.** Sessions are files on disk keyed by project folder + session UUID. There is no Cursor-style window linkage.

### CLI vs desktop app vs web vs iPhone
Holodeck reads **local** `~/.claude/projects` JSONL only.

On disk, Claude Code **CLI** and **Claude Desktop** both write to this tree. Raw `user` records distinguish clients via `entrypoint` (`cli`, `claude-desktop`). Holodeck copies the first user line's `entrypoint` into the session row.

Claude.ai **web** and **iPhone** consumer chat syncs in the cloud but does not write to this local JSONL store on the surveyed Mac — see **Entrypoint** above.

The dashboard's per-worktree **Primary AI interface** pulldown (`claude-cli` vs `claude-app`) is a **manual** Holodeck state field (`apps/holodeck/data/state.json`), not inferred from session files.

### Detail messages
Each message: `role` (`user` / `assistant`), full `text`, and `ts` from the JSONL `timestamp` field.


## OpenAI Codex
### Where messages live
Codex rollout logs are **JSONL** files under:
`~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`
Thread titles come from a separate index:
`~/.codex/session_index.jsonl`
Each index line: `{"id", "thread_name", "updated_at"}`.

### Storage format
**JSONL** with typed records:

| `type` | Holodeck use |
|--------|----------------|
| `session_meta` | One per file: session id, start time, `cwd`, `git.branch` |
| `response_item` | Individual turns; `payload.role` of `user` or `assistant` |
| `event_msg` and others | Ignored for inventory/detail |

### `session_meta.payload` fields (raw)
Holodeck reads: `id` / `session_id`, `timestamp`, `cwd`, `git.branch`.

The payload also carries client metadata Holodeck **does not** surface:

| Field | Example values | Meaning |
|-------|----------------|---------|
| `source` | `vscode`, `exec`, subagent objects | Which Codex client started the session |
| `originator` | `Codex Desktop`, `codex_exec` | Product name |
| `thread_source` | `user`, `subagent` | How the thread was created |
| `cli_version` | e.g. `0.144.2` | Codex CLI version |

### `response_item.payload` fields (messages)
| Field | Meaning |
|-------|---------|
| `role` | `user`, `assistant`, or other roles (Holodeck keeps only user/assistant) |
| `content` | String or block array (text extracted like Claude) |
| `timestamp` | Per-message time when present |

Holodeck uses `payload.timestamp` for detail `ts`. Session `last_activity` falls back to the rollout file's modification time.

### CLI vs desktop vs VS Code/Cursor vs web vs iPhone
Holodeck reads **local** `~/.codex/sessions` JSONL only — the same files whether you used Codex CLI, Codex Desktop, or a VS Code/Cursor-integrated Codex client. `session_meta` distinguishes clients; Holodeck normalizes them to `entrypoint` values (`codex-cli`, `codex-desktop`, `codex-subagent`).
ChatGPT **web** and **iPhone** Codex threads sync in the cloud but are not written to `~/.codex/sessions` locally — see **Entrypoint** above.
As with Claude, the dashboard's `codex-cli` / `codex-app` primary-interface pills are **manual** worktree state, not parsed from session files.

### Large files
Rollout JSONL files can exceed 20 MB. Holodeck samples them: first 200 lines + last 400 lines when reading for inventory and detail.


## API recap
| Endpoint | Purpose |
|----------|---------|
| `collect.py --layer sessions` | Rebuild only the sessions layer in `snapshot.json` |
| `GET /api/snapshot` | Includes `layers.sessions` array |
| `GET /api/sessions/{tool}/{session_id}` | Lazy full messages for a snapshot session |
| `POST /api/refresh` with `{"layers": ["sessions"]}` | Refresh sessions from the running server |

Allowed `tool` values: `cursor`, `claude-code`, `codex`. The detail route rejects sessions not in the current snapshot and validates source paths stay under the expected home-directory roots.


## Quick comparison
| | Cursor | Claude Code | Codex |
|---|--------|-------------|-------|
| **Format** | SQLite key/value (`state.vscdb`) | JSONL per session file | JSONL rollout files + title index |
| **Session key** | `composerId` UUID | Filename UUID | `session_meta.payload.id` |
| **Repo match** | `workspaceIdentifier` path | `cwd` on message lines | `session_meta.payload.cwd` |
| **Per-message timestamps in drawer** | No (`ts: null`) | Yes | Yes (when present in payload) |
| **Client/interface in Holodeck** | `cursor` | Raw `entrypoint` (`cli`, `claude-desktop`, …) | Normalized `entrypoint` (`codex-cli`, `codex-desktop`, …) |
| **Window tracking** | Separate (`cursor_open` in worktrees layer) | N/A | N/A |


## Randy Notes 2026-07-16_1427
### Voice prompts from superwhisper
Okay, so I want you to do an important set of things here and I think it's gonna make sense to do this on a sub branch that comes off of the of this parent branch holodeck start and I think it makes sense to call this feature holodeck-commits because the general purpose here the main thing that you're going to do is to create a database that's going to store the commits and the AI messages together it's essentially going to correlate those two things and I'm going to explain a bit more about this I'm also going to describe some various miscellaneous kind of UI, UX things to change in different parts of this and the general goal here is to make this more usable for me in tracking what I sometimes call the turns that I'm doing on these different applications so you know what these turns typically involve is a long voice dictated prompt sometimes it's multi-part but it's almost always voice dictated and it's usually while I'm using the app and testing the last thing that was done and often it includes both fixes to and changes as well as like new you know one or more new features some that might be major so you can think of it as like inner interaction by me this is Randy I'm the primary coder repo owner sort of kind of main main person here working on these I mean almost solo so you can you can sort of treat it that way there are a couple of branches that are worked on by other people but not much so okay let me get to the before I get to the kind of turns in the and this database and the commits me AI messages I'm looking at the current version here and in the status I had asked him to put the time over on the left I actually want it to be put over on the right to the right of the the badges that indicate what platform was used and I'm gonna and the reason is because I think I'm very much thinking about these with respect to which which platform I used and how long ago that was and what what is waiting on me and then when am I waiting on the AI to finish the coding so this is actually really you know really important and you know part of the complexity here is that I'm using multiple different providers you know anthropic and Claude open AI and through codex and your GPT models and and then through multiple interfaces or entry points or applications such as the CLI primarily I'm using the or at least I used to be but now I'm using the CLI more I used to be using the Mac OS apps I still am for codex and yeah so I want to see the time after that badge now one thing one thing that's confusing to me here is in the status section under overview I see like the only ones I see right now are Claude CLI and I'm not sure what that like attribute is called because down below in the work tree cards it says cursor codex or Claude code so really what I want to see there is I want to I want it I want a combination of the you know platform model and entry point there and I guess let me maybe I need to think of they may need to write through what these are going to be. Let me take a second and do that.
Okay, I created these entries as a notes section at the end of the aids - sessions.md file And this is where I'm putting these voice prompts as well to keep disorganized So what I did was I went through and I just manually typed the Basically the places where I'm Entering my prompts which again are almost always voice dictated and I'm almost always doing these through super whisper except on my phone where I use the microphone button in the iOS app actually sometimes for longer when they use super whisper on my phone too and paste it in so These are Basically what I want to see Because they're how I think about this so the key thing for you to do is to store the information properly in a database and then show me the It's basically a combination of like, you know, the platform the entry pointer interface plus the model Plus sometimes some additional information like the environment or the if it's dot plan dot MD So this is quite custom to kind of like my workflow like what I'm doing So but it's it's actually really important and getting this getting this Collation and storage and linking Is gonna be a really really helpful thing so the key insight is that I'm basically not doing any any hand coding. I mean I haven't done at all any in Weeks and probably months. Yeah, and and that includes even Yeah, even cutting and pasting almost always even if it's a small change I mean usually it's a copy change for me And I just asked the cursor composer 2.5 fast in agent mode to do it So The key insight here is that basically every commit is Associated with a AI session or or just prompt So So I want to link those up I want to Store these and make make that connection. It seems like that's partly implemented but not fully and This when I was thinking about this, you know one, you know one prompt or one It really it's an incident. I think of it as an exchange where it's a user prompt in a response Sometimes there can be short sort of follow-ups that you know aren't nearly as important as the primary message And so that's another thing I I have like basically primary messages which are usually longer They're important. They contain sort of features or key requests and then the AI Does a you know fairly significant coding? Turn as a part of that And then other there are other quick fast Changes and sometimes just informational prompts where I ask about things to kind of learn or understand things better so really distinguishing the between these is is important and the reason it's so important is because I mean usually after every You know primary prompt and Can be anywhere from a couple minute to a 30 or 45 minute Response time from the AI system that I usually want to go in and do at least a quick a quick test a quick look So and then sometimes if I don't like what I see here if I see problems or changes then I just voice-tit-tape follow-ups while I'm I'm doing that testing and Then it can be confusing though because sometimes you know locally those changes just they sit in in the working directory I'm typically trying to commit really after every AI response because because I'm not looking at the code I think it makes sense to to basically basically commit after every response of the AI after every You know agent turn on changing the code, so that's typically what I'm doing Sometimes I do skip that and and if I'm tuning something I might do a few prompts and returns before Do before manually committing? So It can be the case that Several commits are associated with a single You know user AI exchange That's often the case for the more complex ones. There's multiple the agent ends up You know grouping the work into multiple kind of logical commits Or a Single commit can be the result of multiple Exchanges, but it's usually still just a single session It's I think it's quite rare that a commit Is the result of more than one session although sometimes it's it's Well the the cloud coding agents always commit and push. That's the only way I I get them locally Right this only way I can see those changes is pulling them down So by default the cloud coding and just always commit and you can review my agents dot MD to see some of this so I think The thing I want you to do is develop I think further expand You know the I think it would be the collectors. I'm not sure Looks like this might be the sessions.py, but I think Yeah, basically Figure out how to I think it makes sense to store this as a database Even if it's a small one. I mean could be a SQLite file. I'm not sure I don't know what format the Cursor, I think it's like a VS code DB file or something like that So then let me explain here kind of like what I want to see.
Okay, so I'm confused why the status shows Claude CLI and then down for the AI sessions it just says cursor Codex, Claude code. So from the like the sort of session identifiers, I'm not quite sure what to call these are the lines that I gave for each of the entries for cursor Claude code Codex. These are what I want to see and I know they're a little bit kind of idiosyncratic and this is what's going to help me and I want to see the same thing up in the status as down in the work tree cards. Yeah, but the time after that kind of session identifier string. Yeah. Okay, and then the main thing I want to see is if I click on like that AI session, what I want to see is basically a summary of what I asked for and then and then any additional information that the AI gave besides like build that any like important you know build details or you know important things to note or something like that. And like each of those should be kind of like a handful of bullets. It's important to be able to like for me to be able to digest those quickly. And then if I want to see the more fulsome description such as the entire AI agents response, I can click into that. The Claude CLI does a good job of showing that something at the end called the recap. That's a really good nice like you know just one or two sentence summary of what of what it built and what it did that turn. So you may need a custom prompt to do this to basically post process the session to get to get this information in the format that I wanted here and that's fine if you make an additional API call to get that. I think it's worth it. So develop that prompt and do it. Where there is the recap, where there is the nice summary, more and more models are doing a doing you know a TLDR either at the beginning of its response or at the end. Sometimes it's and sometimes it does a slightly different version in both places and then the detail is in the middle of the response. Okay I think this is enough and you're gonna have to sort of fill in some details here and make some judgments. If you have questions ask me those questions but I would prefer for you to use your best judgment and do what you recommend and then in your in your response. You know offer alternatives and if if I want to you know make a change to what you've implemented. Okay do this.

### Cursor
Cursor - Composer 2.5 Fast
  - Cursor is running on Randy's MacBookPro laptop unless otherwise specified (host4)
  - Cursor has a new iphone app which I installed but have not used
  - am not using the new Cursor agent window interface
Cursor - Grok 4.5 High Fast
Cursor - Opus 4.8 1M High (.plan.md)
  - I want to specifically call out when I use plan mode to create a Cursor .plan.md file (I am always adding these to the workspace and committing them, sometimes they live in the root .cursor folder and sometimes I move them to the <app-name>/docs folder)

### Claude Code
Claude Code App (Cloud env=Cataclysm) - <model>
  - a few weeks ago, this was my go-to for complex work
  - would tag-team from MacOS to iOS apps
Claude Code App (Local)
  - have not tried this
  - using Remote Control (rc) instead
Claude Code CLI (Cursor)
  - only using from the terminal in Cursor
  - have a skill `fable5-w-codex` where Claude Fable 5 delegates subagents to Codex

### Codex
Codex App - 5.6 Sol Extra High (Local)
  - currently using as go-to for complex tasks to reserve Claude subscription tokens for Fable and to utilize Codex subscription tokens
  - selecting existing worktree as Codex `project` (or create new one if that project does not exist yet)
  - for `fof-mono` project, cannot select existing branch that is open as worktree (on 1 checkout error), but can create new sub-branch that is not checked out and instruct Codex session to work there (did this for `feature/minecraft-tp-credits`)
Codex CLI - <model>
  - installed but I have not yet used on it's own
  - the skill `fable5-w-codex` may be calling the Codex CLI