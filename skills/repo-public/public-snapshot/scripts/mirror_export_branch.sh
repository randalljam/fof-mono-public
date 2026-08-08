#!/usr/bin/env bash
# Mirror the export branch tip into the public repo as one snapshot commit.
#
#   ./skills/repo-public/public-snapshot/scripts/mirror_export_branch.sh            # dry run
#   ./skills/repo-public/public-snapshot/scripts/mirror_export_branch.sh --execute  # publish
#
# Copies the TREE of origin/export/to-fof-mono-public (no private history) into
# a clone of fof-mono-public, commits `snapshot: <date> from private <sha>`,
# and pushes. The branch tip is exactly what ships — review it before running.
#
# Public commit author email defaults to the GitHub noreply for randalljam
# (override with FOF_PUBLIC_EMAIL if needed). Does not touch private-repo git config.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
EXPORT_BRANCH="${FOF_EXPORT_BRANCH:-export/to-fof-mono-public}"
PUBLIC_REMOTE="${FOF_PUBLIC_REMOTE:-git@github.com:randalljam/fof-mono-public.git}"
PUBLIC_CLONE="${FOF_PUBLIC_CLONE:-$HOME/Documents/Code/fof-mono-public}"
# GitHub noreply for randalljam — public snapshot commits only (not private-repo identity)
PUBLIC_EMAIL_DEFAULT="18576005+randalljam@users.noreply.github.com"
EXECUTE=false
[[ "${1:-}" == "--execute" ]] && EXECUTE=true
cd "$REPO_ROOT"
git fetch origin --quiet
SHA="$(git rev-parse --short "origin/$EXPORT_BRANCH")"
STAGE="$(mktemp -d "${TMPDIR:-/tmp}/fof-mirror.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT
git archive "origin/$EXPORT_BRANCH" | tar -x -C "$STAGE"
echo "=== mirror export branch ==="
echo "source: origin/$EXPORT_BRANCH @ $SHA"
echo "size:   $(du -sh "$STAGE" | cut -f1), $(find "$STAGE" -type f | wc -l | tr -d ' ') files"
if [[ "$EXECUTE" != "true" ]]; then
  echo "dry run: no push (pass --execute to publish)"
  exit 0
fi
if [[ ! -d "$PUBLIC_CLONE/.git" ]]; then
  echo "cloning $PUBLIC_REMOTE -> $PUBLIC_CLONE"
  git clone "$PUBLIC_REMOTE" "$PUBLIC_CLONE"
else
  git -C "$PUBLIC_CLONE" pull --ff-only
fi
rsync -a --delete --exclude '.git' "$STAGE/" "$PUBLIC_CLONE/"
cd "$PUBLIC_CLONE"
### Public commit identity — never stamp a personal email into public metadata
PUBLIC_EMAIL="${FOF_PUBLIC_EMAIL:-$PUBLIC_EMAIL_DEFAULT}"
git config user.email "$PUBLIC_EMAIL"
COMMIT_EMAIL="$(git config user.email || true)"
if [[ "$COMMIT_EMAIL" != *"users.noreply.github.com"* && "$COMMIT_EMAIL" != *"@focusonfoundations.org"* ]]; then
  echo "BLOCKED: public clone would commit as '$COMMIT_EMAIL'." >&2
  echo "Expected a GitHub noreply or @focusonfoundations.org address." >&2
  echo "Override with FOF_PUBLIC_EMAIL=... if needed." >&2
  exit 1
fi
git add -A
if git diff --cached --quiet; then
  echo "publish: no changes since last snapshot; nothing to commit"
  exit 0
fi
git commit -m "snapshot: $(date +%F) from private $SHA"
git push origin HEAD
git log --oneline -1
echo "done."
