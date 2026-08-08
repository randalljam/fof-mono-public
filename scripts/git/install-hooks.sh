#!/usr/bin/env bash
# Point this repo's git hooks at the tracked scripts in scripts/git/hooks/.
# Run once per clone/worktree checkout (repository config is shared across worktrees).
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
HOOKS_DIR="scripts/git/hooks"
if [[ ! -f "$HOOKS_DIR/pre-commit" ]]; then
  echo "error: missing $HOOKS_DIR/pre-commit" >&2
  exit 1
fi
chmod +x "$HOOKS_DIR/pre-commit"
git config core.hooksPath "$HOOKS_DIR"
echo "Installed git hooks -> $ROOT/$HOOKS_DIR"
echo "core.hooksPath=$(git config core.hooksPath)"
