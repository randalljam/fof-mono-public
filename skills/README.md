file: skills/README.md
title: skills/ — Shared, platform-agnostic skill definitions

**Shared skills — procedures and scripts usable by any agent or platform.**

This folder holds the platform-agnostic source of truth for reusable skills: the
procedures (instructions), scripts, references, and eval harnesses. Each platform
consumes these through its own wrapper format:

| Platform | Wrapper location | Discovery |
|----------|-----------------|-----------|
| **Hermes** | `agents/hermes/skills/<cat>/<name>/SKILL.md` | Auto-matched by description |
| **Claude Code** | `.claude/commands/<name>.md` (future) | Explicit: `/<command>` |
| **Cursor** | `.cursor/rules/` or via `AGENTS.md` | Auto-attached or manual |
| **Codex** | Via `AGENTS.md` | Agent reads at session start |

This mirrors the pattern already used for agent instructions: one `AGENTS.md` source of
truth, with `CLAUDE.md`, `.cursor/rules/`, etc. as platform entry points.


## A skill is a folder with a README
```
skills/<category>/<skill-name>/
  README.md            # required: what it does, when to use it, step-by-step procedure
  scripts/             # optional: the skill's logic (testable, stdlib-first)
  references/          # optional: schema docs, examples the agent reads on demand
  eval/                # optional: test cases and eval harnesses
```


## File headers
Every skill markdown file (`README.md`, `references/*.md`, `eval/*.md`) starts with a
header block so agents can locate it from any working directory:

```
file: skills/<category>/<skill-name>/README.md
title: Human-readable title
source-github-url: <upstream GitHub URL>   # see Provenance below
source-guide-url: <upstream guide/docs URL>
history:                        # lightweight versioning — newest entry first
  - YYYY-MM-DD · <author> · <platform> [<thread title>](<thread-id-or-url>) — <what changed>
  - YYYY-MM-DD · <author> · <platform> [<thread title>](<thread-id-or-url>) — <what changed>

```

Use the **repo-relative path** in `file:` (from the monorepo root), not a basename or
path relative to the skill folder. When a skill README points at references, scripts, or
eval files, use the same repo-relative paths — e.g.
`skills/media/youtube-transcript/references/example-yt-transcript-01-multiple-speakers.md`.


## Provenance and lightweight versioning
**Required on every skill `README.md`.** Git commit history is not enough — the header
records *where a skill came from* and *who changed it in which AI thread*.

- **`source-github-url:`** — URL of the upstream skill source on GitHub (e.g. a bundled
  Hermes `SKILL.md` file).
- **`source-guide-url:`** — URL of the human-readable upstream guide or docs page (e.g.
  Hermes Agent docs for a bundled skill).
- **When only one URL exists**, duplicate it in both fields — e.g. GitHub-only upstream:
  set both `source-github-url` and `source-guide-url` to the same GitHub URL; guide-only:
  set both to the guide URL. When both exist (common for Hermes bundled skills), use each
  URL in its own field.
- **Skills authored entirely in this repo** — omit both fields, or set both to `original`.
- **`history:`** — append-only list, **newest first**. Each line:
  `YYYY-MM-DD · <human author> · <platform> [<short thread title>](<link>) — <brief note>`.
  - **Platform** — `Cursor`, `Claude Code`, `ChatGPT`, etc.
  - **Thread link** — for Cursor, use the transcript UUID (no `.jsonl`), e.g.
    `[Skill YouTube](89db60ea-666b-4529-ae35-5bb34d2e3556)`. For other platforms, use
    whatever share/session URL exists.
  - **On each material edit** to the skill, add a new `history` line at the top. Do not
    rewrite or delete older entries.
- **Formal versioning** (semver, `CHANGELOG.md`) is optional and reserved for skills that
  need a published API contract. Default is this lightweight `history` block only.

Example — `skills/media/youtube-transcript/README.md` (adapted from the Nous Research Hermes
Agent bundled `media/youtube-content` skill —
[GitHub SKILL.md](https://github.com/NousResearch/hermes-agent/blob/main/skills/media/youtube-content/SKILL.md),
[docs guide](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/media/media-youtube-content)).


## Conventions
- **Provenance and versioning** — **required** on every skill `README.md`. See
  [Provenance and lightweight versioning](#provenance-and-lightweight-versioning) above.
- **Markdown formatting** — **required** for every skill README and reference doc. Follow
  `AGENTS.md` → Markdown formatting: **two blank lines** before every heading (`##` and
  deeper); **no blank line** between a heading and the body text, list, or code block that
  follows. A format-specific skill (e.g. YouTube transcript output) may document exceptions
  for its generated artifacts only — not for the skill's own README.
- **Categories** group skills (`education/`, `repo-ops/`, later `devops/`, `research/`, ...).
- **Self-contained first.** Scripts should use the stdlib or narrow CLIs. Skills needing
  heavy dependencies (boto3, core/, etc.) should document the requirement and provide a
  deps strategy (venv, uvx, or calling a service).
- **Testable.** Skill scripts are plain code; add tests so the pipeline is real.
- **kebab-case** for skill/directory names; **snake_case** for `.py` files (repo convention).
- **No secrets** in skills. Use the agent's configured credentials/tools.
- **Confirm before saving.** Skills that persist data should confirm with the user before
  writing — state the extracted/computed values in plain language so errors are caught.


## Add a skill
1. Create `<category>/<name>/README.md` (+ `scripts/`, `references/` as needed).
2. Add tests for any script logic.
3. Create platform wrappers as needed:
   - **Hermes:** `agents/hermes/skills/<cat>/<name>/SKILL.md` with frontmatter, referencing
     scripts here by repo-relative path.
   - **Claude Code:** `.claude/commands/<name>.md` referencing this skill (future).
4. Push. For Hermes: tell it "sync your skills" from Telegram.


## Relationship to agents/hermes/skills/
`agents/hermes/skills/` holds **Hermes-specific** skills (like `sync-skills`, which calls
`hermes skills reload`) and **thin SKILL.md wrappers** that point at shared scripts here.
Skills whose logic is reusable across platforms live here; Hermes-only mechanics live there.
