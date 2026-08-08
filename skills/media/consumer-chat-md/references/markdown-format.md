file: skills/media/consumer-chat-md/references/markdown-format.md
title: Consumer chat markdown house format

## Single-thread file

```markdown
# YYYY-MM-DD — Thread title
Source: chatgpt|claude
Source URL / id: ...
Exported: 2026-07-25T16:30:00+00:00

## 1. User
First prompt text.

## 1. Assistant
First response text.

## 2. User
Follow-up prompt.

## 2. Assistant
Follow-up response.
```

Rules:
- One H1: `DATE — TITLE` (date first, em dash, title).
- Provenance lines immediately after H1: `Source`, optional `Source URL / id`, optional `Exported`.
- Exchanges use paired `## N. User` then `## N. Assistant` headings with incrementing `N`.
- Body text starts on the line after each heading; no extra wrapper blocks.

## Combined file

```markdown
# <topic> — combined consumer chats

## ChatGPT — Thread title
Source URL / id: ...

## 1. User
...

## 1. Assistant
...

## Claude — Thread title
Source URL / id: ...

## 1. User
...
```

Rules:
- One document H1 for the combined topic.
- Each source thread gets an H2: `ChatGPT — <title>` or `Claude — <title>`.
- Optional provenance line under each H2.
- Message sections reuse the same numbered User/Assistant pattern inside each thread block.

## Filename conventions

- Single thread: `YYYY-MM-DD_<source>_<slug>.md`
- Combined: `YYYY-MM-DD_<topic-slug>_combined.md`
- Default output directory: `$FOF_MONO_LOCAL_FILES_ROOT/consumer-chats/`
