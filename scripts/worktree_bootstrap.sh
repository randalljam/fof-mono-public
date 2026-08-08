#!/usr/bin/env bash
# Bootstrap a new git worktree checkout: symlink .env, local files, and (by default) .venv
# from main, merge .vscode/settings.json from main (preserving Worktree Manager title-bar
# colors when present), copy .vscode/tasks.json from main (folderOpen venv terminal),
# and publish the branch to origin (push -u or sync with existing remote).
#
# Usage:
#   ./scripts/worktree_bootstrap.sh                    # current checkout (recommended in worktree window)
#   ./scripts/worktree_bootstrap.sh /path/to/worktree
#   ./scripts/worktree_bootstrap.sh --local-venv       # current checkout, siloed venv
#   ./scripts/worktree_bootstrap.sh /path/to/worktree --local-venv
#   ./scripts/worktree_bootstrap.sh --no-publish       # skip push / upstream setup (local-only branch)
#   ./scripts/worktree_bootstrap.sh --install-hooks    # install pre-commit hooks without prompting
#
# Also checks git pre-commit hooks (scripts/git/hooks/) and installs when missing.
#
# Default: shared .venv (symlink to main repo) — one virtualenv for all worktrees.
# Optional --local-venv: create an isolated .venv in this worktree (siloed pip installs).
# Optional --no-publish: skip publishing; default is to push and set upstream so cloud agents can use the branch.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WT=""
MODE="shared"
PUBLISH=true
INSTALL_HOOKS=""
for arg in "$@"; do
  case "$arg" in
    --local-venv) MODE="--local-venv" ;;
    --no-publish) PUBLISH=false ;;
    --install-hooks) INSTALL_HOOKS="yes" ;;
    *)
      if [[ -n "$WT" ]]; then
        echo "error: unexpected argument '$arg' (usage: $0 [/path/to/worktree] [--local-venv] [--no-publish] [--install-hooks])" >&2
        exit 1
      fi
      WT="$arg"
      ;;
  esac
done
if [[ -z "$WT" ]]; then
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "error: not inside a git checkout — pass a worktree path or cd into the worktree first" >&2
    exit 1
  fi
  WT="$(git rev-parse --show-toplevel)"
fi
if [[ ! -d "$WT" ]]; then
  echo "error: worktree path does not exist: $WT" >&2
  exit 1
fi
if ! git -C "$WT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "error: not a git worktree: $WT" >&2
  exit 1
fi
MAIN="$(dirname "$(git -C "$WT" rev-parse --path-format=absolute --git-common-dir)")"
REQ="${REQ:-$MAIN/dependencies/requirements_2026-07-11.txt}"
cd "$WT"
echo "=== worktree bootstrap ==="
echo "worktree: $WT"
echo "main:     $MAIN"
echo "branch:   $(git branch --show-current)"
echo "mode:     $MODE"
echo "publish:  $PUBLISH"
if [[ -e .env && ! -L .env ]]; then
  echo "error: .env exists and is not a symlink — remove or rename it first" >&2
  exit 1
fi
ln -sf "$MAIN/.env" .env
echo "linked .env -> $MAIN/.env"
"$SCRIPT_DIR/local_files_mount.sh" "$WT"
if [[ "$MODE" == "--local-venv" ]]; then
  if [[ -e .venv ]]; then
    echo "error: .venv already exists — remove it first to create a local venv" >&2
    exit 1
  fi
  if [[ ! -f "$REQ" ]]; then
    echo "error: requirements file not found: $REQ" >&2
    exit 1
  fi
  python3 -m venv .venv
  .venv/bin/pip install -r "$REQ"
  echo "created local .venv and installed from $REQ"
elif [[ "$MODE" == "shared" || -z "$MODE" ]]; then
  if [[ -e .venv && ! -L .venv ]]; then
    echo "error: .venv exists and is not a symlink — remove it first or use --local-venv" >&2
    exit 1
  fi
  if [[ ! -d "$MAIN/.venv" ]]; then
    echo "error: main repo has no .venv at $MAIN/.venv — create it there first" >&2
    exit 1
  fi
  ln -sf "$MAIN/.venv" .venv
  echo "linked .venv -> $MAIN/.venv"
else
  echo "error: unknown mode '$MODE' (use --local-venv or omit for shared venv)" >&2
  exit 1
fi
SETTINGS_SRC="$MAIN/.vscode/settings.json"
SETTINGS_DEST=".vscode/settings.json"
if [[ -f "$SETTINGS_SRC" ]]; then
  mkdir -p .vscode
  SETTINGS_MODE="$("$SCRIPT_DIR/worktree_copy_settings.py" "$SETTINGS_SRC" "$SETTINGS_DEST")"
  if [[ "$SETTINGS_MODE" == "merged" ]]; then
    echo "merged .vscode/settings.json from $MAIN (kept worktree title-bar colors)"
  else
    echo "copied .vscode/settings.json from $MAIN"
  fi
else
  echo "warning: no settings at $SETTINGS_SRC — skipped" >&2
fi
# Copy tasks from main so folderOpen "Open terminal with .venv" works even on
# branches that predate that task (settings merge alone does not bring tasks.json).
TASKS_SRC="$MAIN/.vscode/tasks.json"
TASKS_DEST=".vscode/tasks.json"
if [[ -f "$TASKS_SRC" ]]; then
  mkdir -p .vscode
  cp "$TASKS_SRC" "$TASKS_DEST"
  echo "copied .vscode/tasks.json from $MAIN"
else
  echo "warning: no tasks at $TASKS_SRC — skipped" >&2
fi
if [[ "$PUBLISH" == "true" ]]; then
  BRANCH="$(git branch --show-current)"
  if [[ -z "$BRANCH" ]]; then
    echo "warning: detached HEAD — skipped publish" >&2
  elif [[ "$BRANCH" == "main" || "$BRANCH" == "master" ]]; then
    echo "skipped publish (on $BRANCH)"
  else
    echo "--- publish"
    git fetch origin
    if git show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
      UPSTREAM="$(git rev-parse --abbrev-ref '@{upstream}' 2>/dev/null || true)"
      if [[ "$UPSTREAM" != "origin/$BRANCH" ]]; then
        git branch --set-upstream-to="origin/$BRANCH"
        echo "upstream: origin/$BRANCH"
      else
        echo "upstream: $UPSTREAM"
      fi
      git pull --ff-only
      git push
      echo "in sync with origin/$BRANCH"
    else
      git push -u origin HEAD
      echo "published origin/$BRANCH (upstream set)"
    fi
  fi
fi
EXPECTED_HOOKS="scripts/git/hooks"
CURRENT_HOOKS="$(git config core.hooksPath 2>/dev/null || true)"
if [[ "$CURRENT_HOOKS" == "$EXPECTED_HOOKS" ]]; then
  echo "git hooks: installed ($EXPECTED_HOOKS)"
else
  echo "git hooks: NOT installed (core.hooksPath=${CURRENT_HOOKS:-unset}, expected $EXPECTED_HOOKS)"
  DO_INSTALL=false
  if [[ "$INSTALL_HOOKS" == "yes" || "${FOF_BOOTSTRAP_INSTALL_HOOKS:-}" == "1" ]]; then
    DO_INSTALL=true
  elif [[ -t 0 ]]; then
    read -r -p "Install git pre-commit hooks now? [Y/n] " ans
    if [[ -z "$ans" || "$ans" =~ ^[Yy]$ ]]; then
      DO_INSTALL=true
    fi
  else
    echo "non-interactive session — installing hooks (agents: proceed without prompting)"
    DO_INSTALL=true
  fi
  if [[ "$DO_INSTALL" == true ]]; then
    "$SCRIPT_DIR/git/install-hooks.sh"
  else
    echo "warning: skipped git hooks — run ./scripts/git/install-hooks.sh before committing" >&2
  fi
fi
echo "--- worktree import guard"
if [[ ! -x .venv/bin/python3 ]]; then
  echo "error: .venv/bin/python3 missing after bootstrap" >&2
  exit 1
fi
"$SCRIPT_DIR/python/install_worktree_import_guard.py" --venv-python "$WT/.venv/bin/python3"
if ! "$WT/.venv/bin/python3" "$SCRIPT_DIR/python/diagnose_worktree_imports.py"; then
  echo "error: worktree import guard verification failed for $WT" >&2
  exit 1
fi
echo "python:   $(.venv/bin/python --version)"
echo "done."
