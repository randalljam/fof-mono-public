#!/usr/bin/env bash
# Build a filtered public snapshot of fof-mono; with --execute, commit and push
# it into the fof-mono-public repo as a single snapshot commit.
#
# Usage:
#   ./skills/repo-ops/public-snapshot/scripts/build_public_snapshot.sh              # dry run
#   ./skills/repo-ops/public-snapshot/scripts/build_public_snapshot.sh --execute    # publish
#   ./skills/repo-ops/public-snapshot/scripts/build_public_snapshot.sh --skip-sweep # plumbing test only
#
# Exports tracked files from HEAD (git archive — gitignored/local files can never
# leak), deletes exclude-list paths, injects the public README, runs the PII
# sweep, then (only with --execute) rsyncs into the public clone and pushes.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
PUBLIC_REMOTE="${FOF_PUBLIC_REMOTE:-git@github.com:randalljam/fof-mono-public.git}"
PUBLIC_CLONE="${FOF_PUBLIC_CLONE:-$HOME/Documents/Code/fof-mono-public}"
EXCLUDE_FILE="$SKILL_DIR/snapshot-exclude.md"
ALLOWLIST_FILE="$SKILL_DIR/pii-allowlist.md"
README_TEMPLATE="$SKILL_DIR/public-readme-template.md"
TERMS_FILE="$REPO_ROOT/docs/personal/pii-terms.md"
PYTHON="$REPO_ROOT/.venv/bin/python3"
[[ -x "$PYTHON" ]] || PYTHON="python3"
EXECUTE=false
SKIP_SWEEP=false
for arg in "$@"; do
  case "$arg" in
    --execute) EXECUTE=true ;;
    --skip-sweep) SKIP_SWEEP=true ;;
    *) echo "error: unknown argument '$arg'" >&2; exit 2 ;;
  esac
done
cd "$REPO_ROOT"
SHA="$(git rev-parse --short HEAD)"
BRANCH="$(git branch --show-current)"
if [[ "$BRANCH" != "main" ]]; then
  echo "warning: snapshotting from branch '$BRANCH', not main" >&2
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "warning: working tree is dirty; snapshot uses committed HEAD ($SHA) only" >&2
fi
STAGE="$(mktemp -d "${TMPDIR:-/tmp}/fof-public-snapshot.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT
echo "=== public snapshot build ==="
echo "source:  $REPO_ROOT @ $SHA ($BRANCH)"
echo "stage:   $STAGE"
echo "remote:  $PUBLIC_REMOTE"
git archive HEAD | tar -x -C "$STAGE"
### Apply exclude list
removed=0
while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line%%#*}"
  line="$(printf '%s' "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [[ -z "$line" ]] && continue
  if [[ -e "$STAGE/$line" ]]; then
    rm -rf "${STAGE:?}/$line"
    removed=$((removed + 1))
  fi
done < "$EXCLUDE_FILE"
echo "excluded: $removed path(s) removed per $(basename "$EXCLUDE_FILE")"
### Public README
if [[ ! -f "$STAGE/README.md" && -f "$README_TEMPLATE" ]]; then
  cp "$README_TEMPLATE" "$STAGE/README.md"
  echo "readme:  injected README.md from template"
fi
### Publish-time replacements (stage copy only; private tree untouched)
REPLACE_FILE="$SKILL_DIR/snapshot-replace.md"
if [[ -f "$REPLACE_FILE" ]]; then
  "$PYTHON" "$SCRIPT_DIR/apply_replacements.py" --root "$STAGE" --pairs "$REPLACE_FILE"
fi
### PII sweep gate
if [[ "$SKIP_SWEEP" == "true" ]]; then
  echo "sweep:   SKIPPED (--skip-sweep) — do not publish without a clean sweep"
else
  sweep_args=(--root "$STAGE" --allowlist "$ALLOWLIST_FILE")
  [[ -f "$TERMS_FILE" ]] && sweep_args+=(--terms "$TERMS_FILE")
  if ! "$PYTHON" "$SCRIPT_DIR/pii_sweep.py" "${sweep_args[@]}"; then
    echo "" >&2
    echo "BLOCKED: PII sweep found unsuppressed matches — fix sources, extend" >&2
    echo "snapshot-exclude.md, or allowlist benign patterns, then re-run." >&2
    exit 1
  fi
fi
echo "size:    $(du -sh "$STAGE" | cut -f1), $(find "$STAGE" -type f | wc -l | tr -d ' ') files"
### Publish
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
git add -A
if git diff --cached --quiet; then
  echo "publish: no changes since last snapshot; nothing to commit"
  exit 0
fi
git commit -m "snapshot: $(date +%F) from private $SHA"
git push origin HEAD
git log --oneline -1
echo "done."
