#!/usr/bin/env bash
# nuke_history.sh
#
# Purpose:
#   Nuke/squash ALL history on main into a single clean snapshot commit
#   using an orphan branch + force push. Use after a secret or identifier
#   leaked into an earlier public snapshot commit (tip redaction alone leaves
#   the old blob reachable in history).
#
# SAFETY GUARDS (hard-coded):
#   - Must be run from within this exact local repo path:
#       $HOME/Documents/Code/fof-mono-public
#   - The 'origin' remote URL must be exactly one of:
#       git@github.com:randalljam/fof-mono-public.git
#       https://github.com/randalljam/fof-mono-public.git
#   - Requires interactive confirmation: you must type "yes" (case-insensitive)
#
# Intended home: the public fof-mono-public repo (scripts/git/). Hard path/remote
# guards refuse to run elsewhere, so private-repo agents cannot invoke it by accident.
#
# Typical use (after the public tip tree is already clean):
#   1. Remirror the clean export tip into fof-mono-public.
#   2. Then:
#        cd ~/Documents/Code/fof-mono-public
#        bash scripts/git/nuke_history.sh "snapshot: clean slate"
#
# Notes / warnings:
#   - This script will FORCE PUSH to origin/main. Make sure that's what you want.
#   - It assumes your default branch is "main" and your remote is "origin".
#   - Anyone who cloned/forked before can still have the old history; rotate
#     any exposed secret separately.
#   - Adapted from corpus-tools floodlamp public-repo-mirror/nuke_history.sh
#     and retargeted at fof-mono-public (2026-08-07). Never embed leaked
#     identifier strings in this file.
#
set -euo pipefail

BRANCH="main"
REMOTE="origin"

EXPECTED_TOPLEVEL="${HOME}/Documents/Code/fof-mono-public"
EXPECTED_REMOTE_URLS=(
  "git@github.com:randalljam/fof-mono-public.git"
  "https://github.com/randalljam/fof-mono-public.git"
)

if [[ $# -lt 1 ]]; then
  echo "ERROR: Missing commit message."
  echo "Usage: bash $0 \"Clean snapshot commit message\""
  exit 2
fi

SNAPSHOT_MSG="$1"

if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git not found on PATH."
  exit 2
fi

# Ensure we're inside a git repo
if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "ERROR: Not inside a git repository."
  exit 2
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
echo "Repo root detected: $REPO_ROOT"

# Guard: exact local path match
if [[ "$REPO_ROOT" != "$EXPECTED_TOPLEVEL" ]]; then
  echo "ERROR: Safety guard triggered."
  echo "  This script is hard-coded to run only in:"
  echo "    $EXPECTED_TOPLEVEL"
  echo "  But detected repo root is:"
  echo "    $REPO_ROOT"
  exit 2
fi

cd "$REPO_ROOT"

# Confirm remote exists
if ! git remote get-url "$REMOTE" >/dev/null 2>&1; then
  echo "ERROR: Remote '$REMOTE' not found. Available remotes:"
  git remote -v || true
  exit 2
fi

REMOTE_URL="$(git remote get-url "$REMOTE")"
echo "Remote ($REMOTE) detected: $REMOTE_URL"

# Guard: remote URL must match an expected form
REMOTE_OK=false
for expected in "${EXPECTED_REMOTE_URLS[@]}"; do
  if [[ "$REMOTE_URL" == "$expected" ]]; then
    REMOTE_OK=true
    break
  fi
done
if [[ "$REMOTE_OK" != "true" ]]; then
  echo "ERROR: Safety guard triggered."
  echo "  This script is hard-coded to run only when origin is one of:"
  for expected in "${EXPECTED_REMOTE_URLS[@]}"; do
    echo "    $expected"
  done
  echo "  But detected origin is:"
  echo "    $REMOTE_URL"
  exit 2
fi

# Ensure clean working tree
if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: Working tree is not clean. Commit/stash changes before running."
  git status --porcelain
  exit 2
fi

# Ensure on main
CURRENT_BRANCH="$(git branch --show-current || true)"
if [[ "$CURRENT_BRANCH" != "$BRANCH" ]]; then
  echo "Checking out $BRANCH..."
  git checkout "$BRANCH" 2>/dev/null || git checkout -B "$BRANCH"
fi

# Pull latest (best-effort; ok if diverged)
echo "Pulling latest from $REMOTE/$BRANCH (best effort)..."
git pull "$REMOTE" "$BRANCH" --ff-only || true

# Ensure still clean
if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: Working tree became dirty after pull (unexpected). Resolve and retry."
  git status --porcelain
  exit 2
fi

echo
echo "DANGER ZONE"
echo "This will REWRITE HISTORY and FORCE PUSH to:"
echo "  $REMOTE_URL ($REMOTE/$BRANCH)"
echo
echo "It will replace ALL commit history on $BRANCH with ONE commit:"
echo "  \"$SNAPSHOT_MSG\""
echo
read -r -p "Are you sure? If so, type yes and press Enter: " CONFIRM
CONFIRM_LOWER="$(printf "%s" "$CONFIRM" | tr '[:upper:]' '[:lower:]')"

if [[ "$CONFIRM_LOWER" != "yes" ]]; then
  echo "Aborted (you did not type 'yes'). No changes made."
  exit 0
fi

echo
echo "Proceeding..."

# Nuke history via orphan branch snapshot
git checkout --orphan clean-slate
git add -A

if git diff --cached --quiet; then
  echo "ERROR: Nothing to commit. Is your working tree empty?"
  exit 2
fi

git commit -m "$SNAPSHOT_MSG"

# Replace main and force-push
git branch -M "$BRANCH"
echo "Force-pushing rewritten history to $REMOTE/$BRANCH..."
# Large repos (>1 GB) can fail over HTTPS with "the remote end hung up unexpectedly".
# Increase the HTTP post buffer to 2 GB to handle the full pack in one transfer.
git config http.postBuffer 2147483648
git push --force "$REMOTE" "$BRANCH"

# Cleanup: prune + local gc (optional but nice)
echo
echo "Pruning and running local GC..."
git fetch --prune "$REMOTE" || true
git gc --prune=now --aggressive || true

# Verify only 1 commit reachable from HEAD
FINAL_COUNT="$(git rev-list --count HEAD)"
echo
echo "FINAL commit count on $BRANCH (reachable from HEAD): $FINAL_COUNT"
if [[ "$FINAL_COUNT" -ne 1 ]]; then
  echo "WARNING: Expected 1, got $FINAL_COUNT. Something kept additional commits reachable."
  echo "Check for extra branches/tags pointing to old history:"
  echo "  git branch -a"
  echo "  git tag -n"
  exit 1
fi

echo
echo "SUCCESS: History nuked. '$BRANCH' now has a single commit."
echo "Next: open GitHub -> repo -> Commits (on main). You should see only:"
echo "  $SNAPSHOT_MSG"
echo "Spot-check tip yourself for any leaked strings (do not embed those strings in this script)."
