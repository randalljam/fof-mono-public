#!/usr/bin/env bash
# MANUAL FALLBACK: pull family-schedule markdown from the Hermes Fly volume.
# Runtime Fly dashboard sync uses private networking (*.internal); this helper
# is for local review of live schedule files on a Mac with flyctl.
#
# Usage:
#   ./sync_schedule_from_hermes.sh
#   ./sync_schedule_from_hermes.sh ../data/schedule_live
#
# Writes:
#   <dest>/current-week.md   ← this week's Monday-dated Hermes week file
#   <dest>/next-week.md      ← next week's Monday-dated Hermes week file
#   <dest>/horizon.md        ← horizon_family-schedule.md
#
# fly ssh sftp get refuses to overwrite local files, so each pull lands in a
# temp path and is moved into place. Default dest is the lesson-logger data
# mount: ../data/schedule_live/.
set -euo pipefail
cd "$(dirname "$0")"

HERMES_APP="${HERMES_APP:-[FLY-APP-NAME]}"
SCHEDULE_REMOTE_DIR="${HERMES_SCHEDULE_REMOTE_DIR:-/opt/data/schedule}"
LOCAL_DEST="${1:-../data/schedule_live}"

log() { echo "$(date '+%H:%M:%S')  $*"; }

### Pull one remote file into LOCAL_DEST/<local_name>, replacing any prior copy.
pull_file() {
  local remote_path="$1"
  local local_name="$2"
  local required="${3:-0}"  # 1 = fail the script if missing; 0 = warn and keep old
  local dest="$LOCAL_DEST/$local_name"
  local tmp="$dest.downloading"

  rm -f "$tmp"
  if fly ssh sftp get "$remote_path" "$tmp" -a "$HERMES_APP"; then
    mv -f "$tmp" "$dest"
    local size
    size=$(stat -f%z "$dest" 2>/dev/null || stat -c%s "$dest")
    log "Downloaded $local_name ($size bytes)"
    return 0
  fi
  rm -f "$tmp"
  if [ "$required" -eq 1 ]; then
    log "ERROR: failed to download required file: $remote_path"
    return 1
  fi
  if [ -f "$dest" ]; then
    log "WARN: could not refresh $local_name from Hermes — keeping existing local copy"
  else
    log "WARN: $local_name not on Hermes yet (and no local cache)"
  fi
  return 0
}

DATE_PY="${SCHEDULE_DATE_PYTHON:-.venv/bin/python3}"
if [ ! -x "$DATE_PY" ]; then
  log "ERROR: dashboard Python not found at $DATE_PY; run ./run_local.sh once or set SCHEDULE_DATE_PYTHON"
  exit 1
fi
read -r MONDAY NEXT_MONDAY < <(
  "$DATE_PY" -c 'from datetime import datetime, timedelta; from zoneinfo import ZoneInfo; t = datetime.now(ZoneInfo("America/Los_Angeles")).date(); m = t - timedelta(days=t.weekday()); print(m.isoformat(), (m + timedelta(weeks=1)).isoformat())'
)
REMOTE_WEEK="${SCHEDULE_REMOTE_DIR}/${MONDAY}_week_family-schedule.md"
REMOTE_NEXT_WEEK="${SCHEDULE_REMOTE_DIR}/${NEXT_MONDAY}_week_family-schedule.md"
REMOTE_HORIZON="${SCHEDULE_REMOTE_DIR}/horizon_family-schedule.md"

mkdir -p "$LOCAL_DEST"
log "Pulling family schedule from Hermes ($HERMES_APP) into $LOCAL_DEST"
log "Week file (Monday ${MONDAY}): $REMOTE_WEEK"
pull_file "$REMOTE_WEEK" "current-week.md" 0
log "Next week file (Monday ${NEXT_MONDAY}): $REMOTE_NEXT_WEEK"
pull_file "$REMOTE_NEXT_WEEK" "next-week.md" 0
log "Horizon: $REMOTE_HORIZON"
pull_file "$REMOTE_HORIZON" "horizon.md" 1
log "Done. Point the dashboard at this dir with SCHEDULE_DIR=$LOCAL_DEST (or use run_local.sh --live-schedule)."
