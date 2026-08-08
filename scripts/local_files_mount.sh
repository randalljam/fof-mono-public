#!/usr/bin/env bash
# Mount shared local-only folders into a git worktree as symlinks.
#
# Usage:
#   ./scripts/local_files_mount.sh /path/to/worktree
#   ./scripts/local_files_mount.sh /path/to/worktree --dry-run
#
# Canonical local files live outside every checkout. This script links only the
# approved mount points below; it does not discover arbitrary folders from the
# canonical root because some folders there are backups or internal bookkeeping.
set -euo pipefail
WT="${1:?Usage: $0 /path/to/worktree [--dry-run]}"
MODE="${2:-apply}"
LOCAL_ROOT="${FOF_MONO_LOCAL_FILES_ROOT:-/Users/randytrue/Documents/Code/_LOCAL_FILES/fof-mono}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MOUNTS_FILE="${FOF_MONO_LOCAL_FILES_MOUNTS:-$SCRIPT_DIR/local_files_mounts.txt}"
MOUNT_POINTS=()
EXCLUDE_MARKER_BEGIN="# BEGIN fof-mono local-files mounts"
EXCLUDE_MARKER_END="# END fof-mono local-files mounts"
if [[ ! -f "$MOUNTS_FILE" ]]; then
  echo "error: mount config not found: $MOUNTS_FILE" >&2
  exit 1
fi
while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line%%#*}"
  line="$(printf '%s' "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [[ -z "$line" ]] && continue
  MOUNT_POINTS+=("$line")
done < "$MOUNTS_FILE"
if [[ "$MODE" != "apply" && "$MODE" != "--dry-run" ]]; then
  echo "error: unknown mode '$MODE' (use --dry-run or omit)" >&2
  exit 1
fi
if [[ ! -d "$WT" ]]; then
  echo "error: worktree path does not exist: $WT" >&2
  exit 1
fi
if ! git -C "$WT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "error: not a git worktree: $WT" >&2
  exit 1
fi
echo "=== local files mount ==="
echo "worktree:   $WT"
echo "local root: $LOCAL_ROOT"
echo "mode:       $MODE"
ensure_local_excludes() {
  local git_dir
  local exclude_file
  git_dir="$(git -C "$WT" rev-parse --absolute-git-dir)"
  exclude_file="$git_dir/info/exclude"
  if [[ "$MODE" == "--dry-run" ]]; then
    echo "would ensure local git excludes in $exclude_file"
    return 0
  fi
  mkdir -p "$(dirname "$exclude_file")"
  touch "$exclude_file"
  if grep -Fq "$EXCLUDE_MARKER_BEGIN" "$exclude_file"; then
    local added=0
    for rel in "${MOUNT_POINTS[@]}"; do
      if ! grep -Fxq "/$rel" "$exclude_file"; then
        echo "/$rel" >> "$exclude_file"
        added=1
      fi
    done
    if [[ "$added" == "1" ]]; then
      echo "updated local git excludes with new mount points: $exclude_file"
    else
      echo "ok: local git excludes already contain local-files block"
    fi
    return 0
  fi
  {
    echo ""
    echo "$EXCLUDE_MARKER_BEGIN"
    for rel in "${MOUNT_POINTS[@]}"; do
      echo "/$rel"
    done
    echo "$EXCLUDE_MARKER_END"
  } >> "$exclude_file"
  echo "updated local git excludes: $exclude_file"
}
is_effectively_empty_dir() {
  local path="$1"
  [[ -d "$path" ]] || return 1
  [[ -z "$(find "$path" -type f ! -name .DS_Store -print -quit)" ]]
}
link_mount() {
  local rel="$1"
  local link_path="$WT/$rel"
  local target_path="$LOCAL_ROOT/$rel"
  local parent
  parent="$(dirname "$link_path")"
  echo "--- $rel"
  if [[ "$MODE" == "--dry-run" ]]; then
    echo "would ensure target: $target_path"
  else
    mkdir -p "$target_path" "$parent"
  fi
  if [[ -L "$link_path" ]]; then
    local current
    current="$(readlink "$link_path")"
    if [[ "$current" == "$target_path" ]]; then
      echo "ok: already linked -> $target_path"
      return 0
    fi
    if [[ "$MODE" == "--dry-run" ]]; then
      echo "would relink $link_path from $current to $target_path"
    else
      rm "$link_path"
      ln -s "$target_path" "$link_path"
      echo "relinked -> $target_path"
    fi
    return 0
  fi
  if [[ -e "$link_path" ]]; then
    if is_effectively_empty_dir "$link_path"; then
      if [[ "$MODE" == "--dry-run" ]]; then
        echo "would replace empty real directory tree with symlink"
      else
        rsync -a --exclude '.DS_Store' "$link_path/" "$target_path/"
        rm -rf "$link_path"
        ln -s "$target_path" "$link_path"
        echo "linked empty real directory tree -> $target_path"
      fi
      return 0
    fi
    echo "error: $link_path exists and is not an empty directory or symlink" >&2
    echo "       move or inspect it before mounting shared local files here" >&2
    return 1
  fi
  if [[ "$MODE" == "--dry-run" ]]; then
    echo "would link $link_path -> $target_path"
  else
    ln -s "$target_path" "$link_path"
    echo "linked -> $target_path"
  fi
}
ensure_local_excludes
for rel in "${MOUNT_POINTS[@]}"; do
  link_mount "$rel"
done
echo "done."
