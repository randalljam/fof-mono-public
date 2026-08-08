file: skills/repo-ops/cli-auth-check/README.md
title: CLI authentication check
source-github-url: original
source-guide-url: original
history:
  - 2026-07-23 · Randy · Cursor [CLI auth check skill](98a1b05c-4019-415c-8b6e-5bd89db9b596) — table columns: CLI, Command, Version, Status, Account, Path, Notes; AWS account = user + account number
  - 2026-07-23 · Randy · Cursor [CLI auth check skill](98a1b05c-4019-415c-8b6e-5bd89db9b596) — markdown table with ✅/❌; Chalice follows AWS auth; Cursor AUTH OK from app Settings email (no CLI auth command; never read tokens)
  - 2026-07-23 · Randy · Cursor [CLI auth check skill](98a1b05c-4019-415c-8b6e-5bd89db9b596) — compact report: CLI version in heading, account in AUTH OK (...), binary alias only when it differs (e.g. Fly.io (fly))
  - 2026-07-23 · Randy · Cursor [CLI auth check skill](98a1b05c-4019-415c-8b6e-5bd89db9b596) — initial skill: read-only install + auth status for gh, aws, chalice, flyctl, codex, claude, cursor


**Use this skill before starting agent coding that needs cloud CLIs** (deploy, GitHub, Fly, Codex, Claude Code). It reports whether each CLI is installed and authenticated so expired logins (e.g. Codex) are caught up front.

**READ-ONLY.** Never logs in, logs out, writes credentials, or prints tokens/secrets. It only runs status/whoami-style commands (plus a Cursor app email lookup that never reads tokens) and prints a stdout report (no file write by default).

**Report shape:** one markdown table with columns `CLI | Command | Version | Status | Account | Path | Notes`. Command is the lowercase binary (`gh`, `aws`, `chalice`, `fly`, `codex`, `claude`, `cursor`). Status is `✅ AUTH OK` or `❌ AUTH FAIL` / `❌ NOT INSTALLED`. Account is a separate column (for AWS: `user (account-number)`).


## When to use
- Start of a local session before agents do real codework that may call `gh`, `aws`/`chalice`, `flyctl`, `codex`, or `claude`.
- User says "check CLI auth", "are we logged in", "Codex auth broken", or similar.
- After a laptop reboot, credential rotation, or a CLI reports authentication errors.

Do **not** fold this into `create-worktree` — keep worktree creation and auth checks separate.


## What it checks

| CLI | Binary | Where it lives | Auth probe |
|-----|--------|----------------|------------|
| GitHub | `gh` | machine PATH (not repo) | `gh auth status` |
| AWS | `aws` | usually Homebrew on PATH; older `awscli` may also exist in `.venv` | `aws sts get-caller-identity` |
| Chalice | `chalice` | typically repo `.venv/bin` | **no separate login** — AUTH OK iff AWS is AUTH OK |
| Fly.io | `fly` / `flyctl` | `~/.fly/bin` (not repo) | `fly auth whoami` |
| Codex | `codex` | npm global / PATH (not repo) | `codex login status` |
| Claude | `claude` | machine PATH (not repo) | `claude auth status` |
| Cursor | `cursor` | app CLI symlink | **no CLI auth command** — reads app Settings email from Cursor global state (email only; never tokens) |

**Mental model:** ops agent CLIs are machine-level. The repo `.venv` holds Python packages for this project (`chalice`, sometimes `awscli` 1.x). Auth tokens live under the home directory, never in git. Chalice is not a cloud login — it is a deploy tool that uses your AWS credentials. Cursor CLI opens windows; your Cursor account is the app Settings login.


## Run
From any checkout of the repo (prefer project venv for the checker script only):
```bash
.venv/bin/python3 skills/repo-ops/cli-auth-check/scripts/cli_auth_check.py
```

Options:
```bash
... --timeout 20                 # per-command timeout seconds (default 20)
... --skip chalice,cursor        # skip named checks: gh,aws,chalice,fly,codex,claude,cursor
```

Prints to stdout. Do not write a report file unless the user asks for one.


## Interpreting the report
- **✅ AUTH OK** — logged in / identity resolved (Chalice OK only when AWS is OK; Cursor OK when app Settings email is present). Account is in its own column.
- **❌ AUTH FAIL** — installed but not authenticated (or Chalice when AWS is not OK). Fix before work that needs that CLI.
- **❌ NOT INSTALLED** — binary/package missing; install only if the session needs it.
- **UNKNOWN** — timeout or ambiguous output; re-run outside a restricted sandbox if needed.

**VERDICT** summarizes failures. If any row is **AUTH FAIL**, tell the user the fix command from that row before starting agents that depend on it.


## Common fix commands
```bash
gh auth login -h github.com
aws configure
# or: aws sso login --profile <name>
flyctl auth login
codex login
claude auth login
```

Chalice has no separate login — fix the AWS row.


## Related
- `skills/repo-ops/clone-bootstrap/README.md` — one-time clone setup (hooks, local-files), not CLI cloud auth.
- `skills/repo-ops/create-worktree/README.md` — worktrees; does not run this check.
- `skills/repo-ops/session-start-check/README.md` — git branch discipline at session start.
