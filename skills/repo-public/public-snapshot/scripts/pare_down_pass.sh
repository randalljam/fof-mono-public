#!/usr/bin/env bash
# Re-apply the pare-down lists on the export branch.
#
# Run INSIDE a checkout of export/to-fof-mono-public:
#   ./skills/repo-public/public-snapshot/scripts/pare_down_pass.sh
#
# Reads snapshot-exclude.md and snapshot-replace.md from origin/main (both
# lists are private — never tracked on the export tip / public snapshot).
# Applies excludes (git rm + wipe non-mount leftovers), applies replacements,
# re-injects the public README if missing, then prints the resulting changes.
# The operator/agent reviews and groups the deltas into per-section commits,
# runs pii_sweep.py (must be 0 findings), and only then mirrors.
#
# Local-files mounts (docs/personal, data/, exchanges/, …) are never deleted —
# only untracked from the git index (--cached). That keeps pii-terms.md, the
# review checklist, and other local-only process docs available in the checkout.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
SKILL_REL="${SCRIPT_DIR#"$REPO_ROOT"/}"
SKILL_REL="$(dirname "$SKILL_REL")"
cd "$REPO_ROOT"
BRANCH="$(git branch --show-current)"
if [[ "$BRANCH" != "export/to-fof-mono-public" ]]; then
  echo "warning: running on branch '$BRANCH', expected export/to-fof-mono-public" >&2
fi
PYTHON="$REPO_ROOT/.venv/bin/python3"
[[ -x "$PYTHON" ]] || PYTHON="python3"
### Fetch a private list file from origin/main (skill path + legacy fallbacks)
fetch_list_from_main() {
  local out="$1" name="$2" rel
  rel="$SKILL_REL/$name"
  if git show "origin/main:$rel" > "$out" 2>/dev/null; then
    return 0
  fi
  if git show "origin/main:skills/repo-public/public-snapshot/$name" > "$out" 2>/dev/null \
      || git show "origin/main:skills/repo-ops/public-snapshot/$name" > "$out" 2>/dev/null; then
    return 0
  fi
  echo "error: could not read $name from origin/main" >&2
  return 1
}
### Mount points from local_files_mounts.txt — never rm -rf these
is_mount() {
  local p="$1" m
  p="${p%/}"
  [[ -f scripts/local_files_mounts.txt ]] || return 1
  while IFS= read -r m || [[ -n "$m" ]]; do
    m="${m%%#*}"
    m="$(printf '%s' "$m" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//;s|/*$||')"
    [[ -z "$m" ]] && continue
    [[ "$m" == "$p" ]] && return 0
  done < scripts/local_files_mounts.txt
  return 1
}
### Private lists live on origin/main
EXCLUDE_LIST="$(mktemp "${TMPDIR:-/tmp}/snapshot-exclude.XXXXXX")"
PAIRS="$(mktemp "${TMPDIR:-/tmp}/snapshot-replace.XXXXXX")"
trap 'rm -f "$EXCLUDE_LIST" "$PAIRS"' EXIT
fetch_list_from_main "$EXCLUDE_LIST" "snapshot-exclude.md"
fetch_list_from_main "$PAIRS" "snapshot-replace.md"
### Excludes — untrack from git, then wipe non-mount working-tree leftovers
removed=0
wiped=0
while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line%%#*}"
  line="$(printf '%s' "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [[ -z "$line" ]] && continue
  path="${line%/}"
  if git ls-files --error-unmatch "$path" >/dev/null 2>&1 \
      || [[ -n "$(git ls-files "$path" 2>/dev/null)" ]]; then
    git rm -r -q --ignore-unmatch "$path"
    removed=$((removed + 1))
  fi
  # Working-tree leftovers (untracked debris, empty dirs after git rm).
  # Skip mounts so docs/personal (pii-terms, checklist, sweep notes) stays.
  if is_mount "$path"; then
    continue
  fi
  if [[ -e "$path" || -L "$path" ]]; then
    rm -rf "$path"
    wiped=$((wiped + 1))
  fi
done < "$EXCLUDE_LIST"
echo "excludes: $removed path spec(s) untracked from git"
echo "wiped:    $wiped non-mount working-tree leftover path(s)"
### Local-files mounts: untrack (--cached). On the export branch, also drop every
### mount symlink except docs/personal (needed for pii-terms + review notes).
### `rm` on a symlink removes only the link — never the shared _LOCAL_FILES target.
KEEP_MOUNT="docs/personal"
unmounted=0
if [[ -f scripts/local_files_mounts.txt ]]; then
  while IFS= read -r m || [[ -n "$m" ]]; do
    m="${m%%#*}"
    m="$(printf '%s' "$m" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//;s|/*$||')"
    [[ -z "$m" ]] && continue
    git rm -r -q --cached --ignore-unmatch "$m" 2>/dev/null || true
    [[ "$m" == "$KEEP_MOUNT" ]] && continue
    if [[ -L "$m" ]]; then
      rm "$m"
      unmounted=$((unmounted + 1))
    elif [[ -e "$m" ]]; then
      echo "warning: mount path '$m' exists but is not a symlink; leaving it" >&2
    fi
  done < scripts/local_files_mounts.txt
fi
echo "unmounted: $unmounted local-files symlink(s) (kept $KEEP_MOUNT)"
### Replacements (rules from origin/main)
"$PYTHON" "$SCRIPT_DIR/apply_replacements.py" --root . --pairs "$PAIRS"
### Public README
if [[ ! -f README.md && -f "$SKILL_REL/public-readme-template.md" ]]; then
  cp "$SKILL_REL/public-readme-template.md" README.md
  echo "readme: re-injected from template"
fi
### Report
echo "--- resulting changes (group into per-section commits) ---"
git add -A
git status --short | head -40
echo "next: commit by section, run pii_sweep.py (must be clean), then mirror."
