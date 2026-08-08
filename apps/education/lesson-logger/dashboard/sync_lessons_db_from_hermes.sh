#!/usr/bin/env bash
# MANUAL FALLBACK: pull lessons.db from the Hermes Fly volume to a local file.
# Runtime dashboard sync uses Fly private networking; this helper is for manual
# inspection or local seeding only.
#
# Usage:
#   ./sync_lessons_db_from_hermes.sh
#   ./sync_lessons_db_from_hermes.sh ../data/lessons_from_hermes.db
#   ./sync_lessons_db_from_hermes.sh /tmp/lessons.db
#
# Default dest is the lesson-logger data mount: ../data/lessons_from_hermes.db
set -euo pipefail
cd "$(dirname "$0")"

HERMES_APP="[FLY-APP-NAME]"
DB_REMOTE_PATH="/opt/data/lesson-logs/lessons.db"
LOCAL_DEST="${1:-../data/lessons_from_hermes.db}"

log() { echo "$(date '+%H:%M:%S')  $*"; }

mkdir -p "$(dirname "$LOCAL_DEST")"
# fly ssh sftp get refuses to overwrite existing local files.
TMP="${LOCAL_DEST}.downloading"
rm -f "$TMP"
log "Downloading lessons.db from Hermes ($HERMES_APP)..."
fly ssh sftp get "$DB_REMOTE_PATH" "$TMP" -a "$HERMES_APP"
mv -f "$TMP" "$LOCAL_DEST"

SIZE=$(stat -f%z "$LOCAL_DEST" 2>/dev/null || stat -c%s "$LOCAL_DEST" 2>/dev/null)
log "Downloaded $SIZE bytes -> $LOCAL_DEST"
