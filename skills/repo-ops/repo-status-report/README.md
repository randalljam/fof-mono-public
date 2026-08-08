file: skills/repo-ops/repo-status-report/README.md
title: Repo status report
source-github-url: original
source-guide-url: original
history:
  - 2026-06-30 · Randy · Cursor [Repo Size And Hooks](90c8a941-72ad-4b56-b21c-4b7a84b4b89f) — default report now includes repo root plus folders under apps
  - 2026-06-30 · Randy · Cursor [Repo Size And Hooks](90c8a941-72ad-4b56-b21c-4b7a84b4b89f) — moved repo_status.py into a reusable repo-ops skill and switched default output to a stable current report file


**Use this skill to generate the current repo status report: a deterministic folder-size snapshot that compares git-tracked bytes against working-tree bytes for the repo root or selected folders.**


## When to use
- The user asks for a repo status report, folder size report, tracked-vs-worktree size snapshot, or "what is taking space in this checkout?"
- The user wants a tracked, stable report file rather than a dated one-off report.
- The question is about current checkout contents, not clone size or history bloat. For clone/history size, use `skills/repo-ops/repo-size-audit/README.md`.


## Output
Default output is stable and intended to be tracked:
```bash
skills/repo-ops/repo-status-report/current-repo-status-report.md
```

The report includes a generated timestamp near the top of the file. Do not put dates or timestamps in the report filename. The default report has two sections: `## Repo Root` and `## Folders Under Apps`.


## Run
From repo root:
```bash
.venv/bin/python3 skills/repo-ops/repo-status-report/scripts/repo_status.py .
```

Print only, without writing the report:
```bash
.venv/bin/python3 skills/repo-ops/repo-status-report/scripts/repo_status.py . --print-only
```

Scan selected repo-relative folders:
```bash
.venv/bin/python3 skills/repo-ops/repo-status-report/scripts/repo_status.py . apps/math-quiz skills
```

Write to a custom path only when the user explicitly asks:
```bash
.venv/bin/python3 skills/repo-ops/repo-status-report/scripts/repo_status.py . --output <path>
```


## What it measures
- **Tracked file count and tracked MB** from `git ls-files`, grouped by immediate child directory.
- **Working-tree file count and working-tree MB** by walking the filesystem, excluding `.git` and symlinks.
- **Folders under apps** with the same columns, so app-level size changes are visible without running a second command.
- The difference between tracked and working-tree size highlights local-only or ignored material such as `.venv`, local data, caches, or build outputs.


## Reporting back
After running, tell the user:
- Where the report was written.
- The top-level total tracked MB and worktree MB.
- The largest one or two folders if they stand out.
- Any caveat if local ignored data or virtualenvs dominate the working-tree size.

Do not commit the report unless the user explicitly asks for a commit.
