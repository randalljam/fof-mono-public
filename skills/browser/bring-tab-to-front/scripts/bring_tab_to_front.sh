#!/usr/bin/env bash
# Bring a unique Chrome tab's window to the front without surfacing sibling
# Chrome windows and without minimizing them.
# Usage:
#   skills/browser/bring-tab-to-front/scripts/bring_tab_to_front.sh [urlNeedle] [windowNamePrefix]
# Defaults: urlNeedle=127.0.0.1:8790  windowNamePrefix=holodeck
set -euo pipefail

URL_NEEDLE="127.0.0.1:8790"
WINDOW_PREFIX="holodeck"

if [[ $# -ge 1 && -n "${1:-}" ]]; then
  URL_NEEDLE="$1"
  shift
fi
if [[ $# -ge 1 && -n "${1:-}" ]]; then
  WINDOW_PREFIX="$1"
  shift
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
ASCRIPT="$SCRIPT_DIR/bring_tab_to_front.applescript"
HELPER="$SCRIPT_DIR/activate_front_window_only.py"
PYTHON="$REPO_ROOT/.venv/bin/python3"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3)"
fi

if [[ ! -f "$ASCRIPT" ]]; then
  echo "ABORT	missing applescript	$ASCRIPT" >&2
  exit 2
fi
if [[ ! -f "$HELPER" ]]; then
  echo "ABORT	missing helper	$HELPER" >&2
  exit 2
fi

result="$(osascript "$ASCRIPT" "$URL_NEEDLE" "$WINDOW_PREFIX" "$PYTHON" "$HELPER")"
echo "$result"
[[ "$result" == OK$'\t'* ]] || exit 1
