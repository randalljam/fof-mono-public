file: skills/media/youtube-transcript/README.md
title: YouTube transcript — fetch and transform YouTube video transcripts
source-github-url: https://github.com/NousResearch/hermes-agent/blob/main/skills/media/youtube-transcript/SKILL.md
source-guide-url: https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/media/media-youtube-content
history:
  - 2026-08-05 · Randy · Cursor [yt refs synthetic swap](e2f50aa7-c5f7-4c05-b6ab-6cd70aebe155) — replace reference transcripts with synthetic format-only examples (no real video bodies)
  - 2026-06-07 · Randy · Cursor [skill youtube-content](89db60ea-666b-4529-ae35-5bb34d2e3556) — yt transcript output format, spacing rules, provenance/versioning
  - 2026-06-07 · Claude Code · [session](https://claude.ai/code/session_01VFysgSVcZZavWUvfBGnh2f) — adapted from Hermes bundled skill; initial import to skills/

**Fetch a YouTube video transcript and transform it into useful formats.**

Extract transcripts from YouTube videos and convert them into summaries, chapter lists,
thread posts, blog posts, or timestamped quotes.


## When to use
When a user shares a YouTube URL or video link, asks to summarize a video, requests a
transcript, or wants to extract and reformat content from any YouTube video.


## Dependencies
```bash
pip install youtube-transcript-api
```

The skill's `fetch_transcript.py` script is fully self-contained (stdlib + `youtube-transcript-api`).
However, the full workflow described below also uses **YouTube metadata** (title, description,
video length) which comes from `core.transcribe.get_youtube_all()` or YouTube oEmbed. When
running outside this repo (e.g. on the Hermes agent), export or vendor the needed function
from `core/` or fall back to oEmbed / manual metadata entry.


## Flow
1. **Fetch** the transcript using the helper script:
   ```bash
   python3 skills/media/youtube-transcript/scripts/fetch_transcript.py "URL" --text-only --timestamps
   ```
   The script accepts any standard YouTube URL format, short links (youtu.be), shorts,
   embeds, live links, or a raw 11-character video ID.

2. **Validate**: confirm the output is non-empty and in the expected language. If empty,
   retry without `--language` to get any available transcript. If still empty, tell the
   user the video likely has transcripts disabled.

3. **Chunk if needed**: if the transcript exceeds ~50K characters, split into overlapping
   chunks (~40K with 2K overlap) and summarize each chunk before merging.

4. **Transform** into the requested output format. If the user did not specify a format,
   default to a summary.

5. **Adjust chapter transitions** (default): move dangling end-of-chapter fragments to
   the start of the next chapter so sentences are complete. Skip if the user requests
   not to adjust transitions.
6. **Confirm** the output looks coherent — correct timestamps, no truncation, clean
   chapter boundaries — before presenting.


## Script usage
```bash
# JSON output with metadata
python3 skills/media/youtube-transcript/scripts/fetch_transcript.py "https://youtube.com/watch?v=VIDEO_ID"

# Plain text (good for piping into further processing)
python3 skills/media/youtube-transcript/scripts/fetch_transcript.py "URL" --text-only

# With timestamps
python3 skills/media/youtube-transcript/scripts/fetch_transcript.py "URL" --timestamps

# Specific language with fallback chain
python3 skills/media/youtube-transcript/scripts/fetch_transcript.py "URL" --language tr,en
```


## Output formats
After fetching the transcript, format it based on what the user asks for:

- **Summary**: concise 5–10 sentence overview of the entire video
- **Chapters**: group by topic shifts, output timestamped chapter list
- **Chapter summaries**: chapters with a short paragraph summary for each
- **Thread**: Twitter/X thread format — numbered posts, each under 280 chars
- **Blog post**: full article with title, sections, and key takeaways
- **Quotes**: notable quotes with timestamps
- **Raw transcript**: the full text, optionally with timestamps


## YouTube transcript markdown format
When the user asks for a full transcript document saved to `data/`, follow these
conventions. Read the reference examples on demand:

- `skills/media/youtube-transcript/references/example-yt-transcript-01-multiple-speakers.md`
  — synthetic podcast interview, multiple speakers, per-paragraph timestamp links, not diarized.
- `skills/media/youtube-transcript/references/example-yt-transcript-02-single-speaker-transitions-adjusted.md`
  — synthetic solo tutorial, one timestamp per chapter, chapter transitions adjusted.

Both reference files are **format exemplars only** (invented names, URLs, and dialogue). Do not treat them as real transcripts.

Skill layout for this format:

```
skills/media/youtube-transcript/
  README.md
  scripts/fetch_transcript.py
  scripts/adjust_chapter_transitions.py
  references/example-yt-transcript-01-multiple-speakers.md
  references/example-yt-transcript-02-single-speaker-transitions-adjusted.md
```


### File location and naming
- **Default output path:** repo-root `data/` (gitignored) — write the markdown file directly
  in that folder, not in a subdirectory, unless the user specifies a different path.
- Filename pattern: `YYYY-MM-DD_<Channel Name>_<Video Title>_yt.md`
  - Underscores separate the four fields only: date, channel, title, `yt` suffix.
  - **Use spaces** (not underscores or dashes) within the channel name and video title.
  - The `title:` metadata field uses the YouTube video title with natural spaces.
  - Examples:
    - `2026-03-12_Riverbend Conversations_Mira Kelso - Are Smart Notebooks Just Stationery_yt.md`
    - `2026-04-18_Dana Orth | Desk Systems_How DeskPilot's Inventor Starts EVERY Project_yt.md`


### Document structure (H2 sections only — never use H1)
Sections in order:

1. **Metadata** — key-value fields with colons (`file:`, `title:`, `url:`, `source:`,
   `channel:`, `length:`, `speakers:`, `diarized:`). Pull title, channel, and length from
   YouTube metadata. See **Speakers and diarization** below.
2. **Summary** — agent-written overview of the whole video (not copied from description).
3. **Description** — verbatim YouTube description body (everything *before* the
   `Timestamps:` block). Do not include the timestamp list here.
4. **Chapters** — parsed from the description's `Timestamps:` block only. Do not infer or
   paraphrase chapters from the transcript.
5. **Transcript** — full text, formatted for readability (see below).


### Spacing rules
These rules apply to **YouTube transcript output documents** saved in `data/`. Skill
READMEs and other markdown in `skills/` follow `AGENTS.md` → Markdown formatting (two
blank lines before every heading; body directly after the heading).

For `data/*_yt.md` output:

- **Two blank lines** before every `##` (H2) section heading.
- **No blank line** between any heading and the content that immediately follows it. The
  first line of body text, list, timestamp link, or transcript paragraph goes directly on
  the next line.
- **`###` and deeper (H3+) within the Transcript and Description sections:**
  - **One blank line** before an H3+ heading when body content precedes it (i.e. it does
    not follow an H2 heading directly). Never use two blank lines before an H3+ heading.
  - **No blank line** before the first H3+ heading when it comes **directly after** its
    parent `##` section heading.
  - **Never two blank lines in a row** anywhere within an H3+ section — not before a
    nested H3+, not between paragraphs, not between a heading and its body. Use a single
    blank line at most.
- **One blank line** between transcript paragraphs (speech segments) within a chapter.

Example — `## Transcript` followed by chapter headings:

```
## Transcript
### 0:00 Cold open & intro
[0:00](…)
First chapter text…

### 1:35 Next chapter
[1:35](…)
Second chapter text…
```

Example — `## Description` with embedded subheadings:

```
## Description
Opening paragraph from the YouTube description.

### We discuss
- bullet list…

### Socials
- follow links…
```


### Description section
- Copy the YouTube description faithfully (links, bold, lists, typos included).
- **Demote embedded headings** one level below `## Description`: YouTube `# Heading`
  becomes `### Heading` (H1 → H3). Apply the H3+ spacing rules above.


### Chapters section
- Source: the `Timestamps:` list in the YouTube description only.
- Use the **exact timestamp strings** and **exact title text** from the description — do
  not rewrite, summarize, or add em dashes.
- Format each line as a bullet with a clickable link (not bold):

  ```
  - [0:00](https://www.youtube.com/watch?v=VIDEO_ID&t=0) Cold open & intro
  ```

  Space between the link and the title text; `&t=` value is timestamp in seconds.


### Transcript section
- Insert `### {timestamp} {title}` H3 headings at each chapter boundary — same timestamp
  and title text as the description's `Timestamps:` list.
- **One timestamp link per chapter** (not bold), on the line immediately after the `###`
  heading. All transcript text for that chapter follows on the next line(s) — no inline
  timestamp links within chapter text.
- Merge caption segments into continuous chapter text. Use blank lines between
  paragraphs only where a natural speech pause warrants a break.
- Strip auto-caption artifacts like `[music]` and `>>` speaker markers where practical.
- **Do not diarize.** Do not label who said what, assign speaker names, or split the
  transcript by speaker. That is a separate workflow (`core/transcribe.py`, Deepgram,
  `core/speakerid.py`, etc.) — out of scope for this skill.

Example chapter block (solo-speaker / transitions-adjusted style — see
`skills/media/youtube-transcript/references/example-yt-transcript-02-single-speaker-transitions-adjusted.md`):

```

### 2:55 PROJECT.md: the file that learns
[2:55](https://www.youtube.com/watch?v=VIDEO_ID&t=175)
Now, this next piece, it's the one that most people miss…
```

Note the **one blank line** before the second and later chapter `###` headings (never two).


### Chapter transition adjustment (default)
Description chapter timestamps often split **mid-sentence**. By default, fix these
boundaries before saving:

1. If a chapter's text does not end on sentence-ending punctuation (`.`, `!`, `?`), the
   trailing fragment is **incomplete**.
2. **Move** that fragment from the end of the chapter to the **beginning** of the next
   chapter, so the next chapter opens with a complete sentence.
3. Repeat for every chapter boundary.

Example — before:

```
…you want access. Now,

### 0:53 Eight parallel sessions
[0:53](…)
Riley has about four DeskPilot sessions…
```

After:

```
…you want access.

### 0:53 Eight parallel sessions
[0:53](…)
Now, Riley has about four DeskPilot sessions…
```

Helper script (optional):

```bash
python3 skills/media/youtube-transcript/scripts/adjust_chapter_transitions.py data/…_yt.md
```

**Opt-out:** if the user says **don't adjust the transitions** (or similar), skip this
step and leave chapter text aligned strictly to the description timestamps, even when
sentences span boundaries.


### Speakers and diarization
This skill fetches YouTube auto-captions or subtitles only. It does **not** perform
speaker diarization. Always record speaker metadata so downstream consumers know what they
are getting.

**Required metadata fields:**

| Field | Values | Meaning |
|-------|--------|---------|
| `speakers:` | `single` | One person speaking throughout (lecture, solo vlog, monologue) |
| | `multiple` | Conversation, interview, podcast, panel, or debate with 2+ voices |
| | `unknown` | Cannot tell from title, description, or a quick transcript scan |
| `diarized:` | `no` | Always `no` for outputs from this skill |

Example (podcast interview):

```
speakers: multiple
diarized: no
```

**How to set `speakers:`** — infer from video type, not from diarization:

- Podcast, interview, debate, panel, Q&A → `multiple`
- Solo lecture, tutorial, vlog, audiobook-style narration → `single`
- Ambiguous → `unknown`

Do not change `diarized:` to `yes` here. If the user needs speaker-labeled transcripts,
direct them to the diarization pipeline — do not attempt it in this skill.


### Data sources
| Field | Source |
|-------|--------|
| Transcript text | `skills/media/youtube-transcript/scripts/fetch_transcript.py` (`youtube-transcript-api`) |
| Title, description, length | YouTube Data API via `core.transcribe.get_youtube_all()` or oEmbed |
| Chapters | Description `Timestamps:` block (not auto-generated) |
| Summary | Agent-written from transcript |
| `speakers:` | Inferred from video format (see Speakers and diarization) |
| `diarized:` | Always `no` for this skill |


### Example — chapters output
```
- [0:00](https://www.youtube.com/watch?v=VIDEO_ID&t=0) Cold open & intro
- [1:35](https://www.youtube.com/watch?v=VIDEO_ID&t=95) Mira's background in design school
```


## Error handling
- **Transcript disabled**: tell the user; suggest they check if subtitles are available.
- **Private/unavailable video**: relay the error and ask the user to verify the URL.
- **No matching language**: retry without `--language` to fetch any available transcript,
  then note the actual language to the user.
- **Dependency missing**: run `pip install youtube-transcript-api` and retry.
