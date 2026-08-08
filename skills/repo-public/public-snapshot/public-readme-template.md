# FoF Mono (public snapshot)

Public snapshot of the Focus on Foundations monorepo: shared Python tooling for file processing, transcription, LLM integration, and RAG, plus the applications built on it (education, family learning games, media pipelines, and agent/repo tooling).

This repo is published as **periodic filtered snapshots** of a private monorepo — a build-in-public window, not a maintained release. Each commit here is one snapshot; private development history, data, and personal/operational files are filtered out at publish time. Expect rough edges, in-progress work, and no compatibility guarantees between snapshots.

- Owner: FocusOnFoundationsNonprofit
- Shared library: `core/` (fileops, transcribe, llm, rag, s3_archive, and friends)
- Apps: `apps/<name>/` — each self-contained where possible
- Agent conventions: `AGENTS.md`
- Data: bulk corpora, logs, and generated data live in private S3 and local-only mounts, not in this repo — paths like `data/`, `logs/`, and `*/_data` are intentionally absent, and code referencing them expects those local mounts (see the local-files sections of `docs/worktrees-guide.md`)
- License: MIT (see `LICENSE`)

Questions or interest in the work: open an issue.
