file: skills/repo-ops/repo-size-audit/README.md
title: Repo size audit
source-github-url: original
source-guide-url: original
history:
  - 2026-06-30 · Randy · Cursor [Repo Size And Hooks](90c8a941-72ad-4b56-b21c-4b7a84b4b89f) — moved repo_size_audit.py into a reusable repo-ops skill and switched default output to a stable current report file


**Use this skill to audit clone size and history bloat: tracked tree size by branch, shallow clone size, fresh full clone size, and how much of the clone is `.git` history.**


## When to use
- The user asks how large the repo is to clone into a VM or cloud instance.
- The user asks whether bloat is in history or active files.
- The user wants to compare clone sizes for `main` and one or more active branches.
- The user wants a tracked, stable repo size audit report rather than a dated one-off report.

For folder-by-folder tracked-vs-worktree size in the current checkout, use `skills/repo-ops/repo-status-report/README.md`.


## Output
Default output is stable and intended to be tracked:
```bash
skills/repo-ops/repo-size-audit/current-repo-size-audit.md
```

The report includes a generated timestamp near the top of the file. Do not put dates or timestamps in the report filename.


## Run
From repo root, audit `main`:
```bash
.venv/bin/python3 skills/repo-ops/repo-size-audit/scripts/repo_size_audit.py
```

Audit multiple branches:
```bash
.venv/bin/python3 skills/repo-ops/repo-size-audit/scripts/repo_size_audit.py --branches main feature/minecraft-mod-forge
```

Print only, without writing the report:
```bash
.venv/bin/python3 skills/repo-ops/repo-size-audit/scripts/repo_size_audit.py --branches main feature/minecraft-mod-forge --print-only
```

Fast mode skips temp clones and reports tracked bytes plus local `.git` size only:
```bash
.venv/bin/python3 skills/repo-ops/repo-size-audit/scripts/repo_size_audit.py --branches main feature/minecraft-mod-forge --fast
```


## What it measures
- **Tracked files (active tree):** logical byte sum of git-tracked files at each branch tip.
- **Shallow clone:** measured `git clone --depth 1 --single-branch` size using a temporary local file clone.
- **Full clone:** measured full `git clone` size using a temporary local file clone.
- **History bloat:** approximate full-clone `.git` size minus shallow-clone `.git` size.
- **Local `.git`:** current checkout `.git` size, which may be larger than a fresh clone because of reflog, extra refs, or unpushed objects.

Temporary clones are created under `data/_repo_size_audit_tmp/` and removed automatically.


## Reporting back
After running, tell the user:
- Where the report was written.
- Full clone size in MB and GB.
- Shallow clone size by audited branch.
- Whether bloat appears to be mostly active files or history.
- Any caveat if local `.git` is larger than fresh-clone `.git`.

Do not commit the report unless the user explicitly asks for a commit.
