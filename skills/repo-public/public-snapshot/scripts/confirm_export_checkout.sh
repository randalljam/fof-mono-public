#!/usr/bin/env bash
# Confirm exclusions and redactions on the export-branch checkout before publish.
#
# Run from a checkout of export/to-fof-mono-public:
#   ./skills/repo-public/public-snapshot/scripts/confirm_export_checkout.sh
#
# Exclusion paths come from skills/repo-public/public-snapshot/snapshot-exclude.md
# on origin/main (same private list pare_down_pass.sh reads) — not hardcoded here.
# Redaction spot-check terms come from confirm-redaction-terms.md on origin/main.
# Prints each check, the paths/terms under test, and PASS/FAIL. Exit 0 only if
# every check passes (docs/personal may still exist on disk — that alone is OK).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
SKILL_REL="${SCRIPT_DIR#"$REPO_ROOT"/}"
SKILL_REL="$(dirname "$SKILL_REL")"
cd "$REPO_ROOT"
BRANCH="$(git branch --show-current)"
TERMS_REL="$SKILL_REL/confirm-redaction-terms.md"
failures=0
echo "=== confirm export checkout ==="
echo "cwd:    $REPO_ROOT"
echo "branch: $BRANCH"
if [[ "$BRANCH" != "export/to-fof-mono-public" ]]; then
  echo "warning: expected branch export/to-fof-mono-public" >&2
fi
echo ""

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

### Load exclude paths from snapshot-exclude.md (origin/main) — single source of truth
EXCLUDE_LIST="$(mktemp "${TMPDIR:-/tmp}/snapshot-exclude.XXXXXX")"
TERMS_LIST="$(mktemp "${TMPDIR:-/tmp}/confirm-redaction-terms.XXXXXX")"
trap 'rm -f "$EXCLUDE_LIST" "$TERMS_LIST"' EXIT
fetch_list_from_main "$EXCLUDE_LIST" "snapshot-exclude.md"
EXCLUDE_PATHS=()
while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line%%#*}"
  line="$(printf '%s' "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [[ -z "$line" ]] && continue
  EXCLUDE_PATHS+=("${line%/}")
done < "$EXCLUDE_LIST"
if [[ "${#EXCLUDE_PATHS[@]}" -eq 0 ]]; then
  echo "error: no exclude paths loaded from origin/main snapshot-exclude.md" >&2
  exit 1
fi

### 1. Exclusions — not tracked in git
echo "--- 1. Confirm exclusions (git index) ---"
echo "Source: origin/main:$SKILL_REL/snapshot-exclude.md (${#EXCLUDE_PATHS[@]} path(s))"
echo "Checking that these paths have no tracked files:"
for p in "${EXCLUDE_PATHS[@]}"; do
  echo "  - $p"
done
tracked_hits=0
for p in "${EXCLUDE_PATHS[@]}"; do
  if git ls-files "$p" | grep -q .; then
    echo "FAIL: STILL TRACKED: $p"
    git ls-files "$p" | sed 's/^/       /' | head -5
    tracked_hits=$((tracked_hits + 1))
  fi
done
if [[ "$tracked_hits" -eq 0 ]]; then
  echo "PASS: none of the exclude paths are tracked"
else
  echo "FAIL: $tracked_hits exclude path(s) still tracked"
  failures=$((failures + 1))
fi
echo ""

### 2. Exclusions — working-tree leftovers (docs/personal mount OK)
echo "--- 2. Confirm exclusions (working tree) ---"
echo "Checking filesystem presence (docs/personal may remain as local mount):"
for p in "${EXCLUDE_PATHS[@]}"; do
  echo "  - $p"
done
fs_bad=0
for p in "${EXCLUDE_PATHS[@]}"; do
  if [[ -e "$p" || -L "$p" ]]; then
    if [[ "$p" == "docs/personal" ]]; then
      echo "OK:   STILL PRESENT (local mount, untracked — will not ship): $p"
    else
      echo "FAIL: STILL PRESENT: $p"
      fs_bad=$((fs_bad + 1))
    fi
  fi
done
if [[ "$fs_bad" -eq 0 ]]; then
  echo "PASS: no unexpected exclude-path leftovers on disk"
else
  echo "FAIL: $fs_bad unexpected path(s) still present on disk"
  failures=$((failures + 1))
fi
echo ""

### 3. Redactions — search tracked files for sensitive terms
# Terms loaded from confirm-redaction-terms.md on origin/main (excluded from ship).
fetch_list_from_main "$TERMS_LIST" "confirm-redaction-terms.md"
ID_TERMS=()
NAME_TERMS=()
section=""
while IFS= read -r raw || [[ -n "$raw" ]]; do
  if [[ "$raw" =~ ^##[[:space:]]+(.*) ]]; then
    title="$(printf '%s' "${BASH_REMATCH[1]}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    case "$title" in
      "Identifier / host / address terms") section=id ;;
      "Personal-name terms") section=name ;;
      *) section="" ;;
    esac
    continue
  fi
  line="${raw%%#*}"
  line="$(printf '%s' "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [[ -z "$line" ]] && continue
  case "$section" in
    id) ID_TERMS+=("$line") ;;
    name) NAME_TERMS+=("$line") ;;
  esac
done < "$TERMS_LIST"
if [[ "${#ID_TERMS[@]}" -eq 0 || "${#NAME_TERMS[@]}" -eq 0 ]]; then
  echo "error: confirm-redaction-terms.md missing id and/or personal-name terms" >&2
  exit 1
fi
echo "--- 3. Confirm redactions (tracked files) ---"
echo "Source: origin/main:$TERMS_REL"
echo "Searching tracked files (git grep). Excludes terms file path if present: $TERMS_REL"
echo ""
echo "Identifier / host / address terms:"
for t in "${ID_TERMS[@]}"; do
  echo "  - $t"
done
id_pattern="$(IFS='|'; echo "${ID_TERMS[*]}")"
id_out="$(git grep -nI -E "$id_pattern" -- . ":!$TERMS_REL" 2>/dev/null || true)"
if [[ -z "$id_out" ]]; then
  echo "PASS: none of the identifier terms found in tracked files"
else
  echo "FAIL: identifier term(s) found:"
  echo "$id_out" | head -40
  count="$(printf '%s\n' "$id_out" | wc -l | tr -d ' ')"
  [[ "$count" -gt 40 ]] && echo "       … ($count total hits, showing first 40)"
  failures=$((failures + 1))
fi
echo ""
echo "Personal-name terms (word-boundary):"
for t in "${NAME_TERMS[@]}"; do
  echo "  - $t"
done
name_pattern="$(IFS='|'; echo "${NAME_TERMS[*]}")"
name_out="$(git grep -nIw -E "$name_pattern" -- . ":!$TERMS_REL" 2>/dev/null || true)"
if [[ -z "$name_out" ]]; then
  echo "PASS: none of the personal-name terms found in tracked files"
else
  echo "FAIL: personal-name term(s) found:"
  echo "$name_out" | head -40
  count="$(printf '%s\n' "$name_out" | wc -l | tr -d ' ')"
  [[ "$count" -gt 40 ]] && echo "       … ($count total hits, showing first 40)"
  failures=$((failures + 1))
fi
echo ""

### Summary
echo "=== summary ==="
if [[ "$failures" -eq 0 ]]; then
  echo "ALL CHECKS PASSED"
  exit 0
fi
echo "FAILED CHECKS: $failures"
exit 1
