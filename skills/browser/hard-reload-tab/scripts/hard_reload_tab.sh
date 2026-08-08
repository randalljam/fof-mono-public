#!/usr/bin/env bash
# Hard-reload (Cmd+Shift+R) or soft-reload a unique Chrome tab by URL needle.
# Usage:
#   skills/browser/hard-reload-tab/scripts/hard_reload_tab.sh [--soft] [urlNeedle] [windowNamePrefix]
# Defaults: urlNeedle=127.0.0.1:8790  windowNamePrefix=holodeck
set -euo pipefail

MODE="hard"
URL_NEEDLE="127.0.0.1:8790"
WINDOW_PREFIX="holodeck"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --soft)
      MODE="soft"
      shift
      ;;
    --hard)
      MODE="hard"
      shift
      ;;
    -*)
      echo "ABORT	unknown flag	$1" >&2
      exit 2
      ;;
    *)
      break
      ;;
  esac
done

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
BRING_FRONT="$REPO_ROOT/skills/browser/bring-tab-to-front/scripts/bring_tab_to_front.sh"
SOFT_RELOAD="$SCRIPT_DIR/soft_reload_tab.applescript"

if [[ "$MODE" == "soft" ]]; then
  if [[ ! -f "$SOFT_RELOAD" ]]; then
    echo "ABORT	missing soft reload script	$SOFT_RELOAD" >&2
    exit 2
  fi
  result="$(osascript "$SOFT_RELOAD" "$URL_NEEDLE")"
  echo "$result"
  [[ "$result" == OK$'\t'* ]] || exit 1
  exit 0
fi

if [[ ! -x "$BRING_FRONT" && ! -f "$BRING_FRONT" ]]; then
  echo "ABORT	missing bring-tab-to-front script	$BRING_FRONT" >&2
  exit 2
fi

focus_result="$("$BRING_FRONT" "$URL_NEEDLE" "$WINDOW_PREFIX")"
echo "focus	$focus_result"
# bring_tab_to_front.sh may print only the final OK line; accept a trailing OK line too.
if [[ "$focus_result" != OK$'\t'* && "$focus_result" != *$'\n'OK$'\t'* ]]; then
  exit 1
fi
# Prefer the last OK line when the wrapper echoes diagnostics.
focus_result="$(printf '%s\n' "$focus_result" | awk '/^OK\t/{line=$0} END{print line}')"
if [[ -z "$focus_result" ]]; then
  echo "ABORT	bring-tab-to-front produced no OK line" >&2
  exit 1
fi

IFS=$'\t' read -r status matched_url matched_title front_url front_title <<<"$focus_result"
if [[ "$status" != "OK" ]]; then
  echo "ABORT	focus failed	$focus_result" >&2
  exit 1
fi
if [[ "$front_url" != *"$URL_NEEDLE"* ]]; then
  echo "ABORT	front URL missing needle before keystroke	$front_url	$front_title" >&2
  exit 1
fi

# Only after verified front URL: Cmd+Shift+R
osascript <<'APPLESCRIPT'
tell application "System Events"
  keystroke "r" using {command down, shift down}
end tell
APPLESCRIPT

echo "OK	$matched_url	$matched_title	$front_url	$front_title"
