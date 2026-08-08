#!/usr/bin/env bash
# Local dev runner for the lesson-logger dashboard.
#
# Idempotent and self-contained: on first run it creates the dashboard's OWN
# virtualenv (.venv inside this folder, separate from any repo-root .venv) and
# installs dependencies; on every run it starts the dev server with auto-reload.
# Safe to run whether or not another venv is active — it always uses this
# folder's .venv explicitly, so you never hit ".venv/bin/uvicorn: No such file".
#
# Usage (from anywhere):
#   apps/education/lesson-logger/dashboard/run_local.sh
#   PORT=8001 apps/education/lesson-logger/dashboard/run_local.sh
#   apps/education/lesson-logger/dashboard/run_local.sh --live-schedule
#   apps/education/lesson-logger/dashboard/run_local.sh --live
#
# --live-schedule  pull live schedule markdown from Hermes (fly ssh sftp), then
#                  serve with SCHEDULE_DIR=../data/schedule_live
# --live           pull live lessons.db + schedule from Hermes, then serve both
#
# Local durable files use the lesson-logger data mount at ../data
# (apps/education/lesson-logger/data → _LOCAL_FILES).
set -euo pipefail
cd "$(dirname "$0")"

DATA_DIR="$(cd .. && pwd)/data"

LIVE_SCHEDULE=0
LIVE_ALL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --live-schedule)
      LIVE_SCHEDULE=1
      shift
      ;;
    --live)
      LIVE_ALL=1
      shift
      ;;
    -h|--help)
      awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "$0"
      exit 0
      ;;
    *)
      echo "Unknown option: $1 (try --live-schedule, --live, or --help)" >&2
      exit 1
      ;;
  esac
done

if [ ! -x .venv/bin/python ]; then
  echo "First run: creating dashboard venv (.venv)..."
  python3 -m venv .venv
fi

# An existing venv can predate a requirements change. Check the app's newest
# direct dependency as well as the server binary before deciding setup is done.
if [ ! -x .venv/bin/uvicorn ] || \
    ! .venv/bin/python -c 'import markdown' >/dev/null 2>&1; then
  echo "Installing dashboard dependencies..."
  .venv/bin/pip install --upgrade pip >/dev/null
  .venv/bin/pip install -r requirements.txt
  echo "Setup complete."
fi

mkdir -p "$DATA_DIR"

if [ "$LIVE_ALL" -eq 1 ] || [ "$LIVE_SCHEDULE" -eq 1 ]; then
  if ! command -v fly >/dev/null 2>&1; then
    echo "flyctl (fly) is required for --live / --live-schedule" >&2
    exit 1
  fi
fi

if [ "$LIVE_ALL" -eq 1 ]; then
  echo "Pulling live lessons DB + family schedule from Hermes..."
  ./sync_lessons_db_from_hermes.sh "$DATA_DIR/lessons_from_hermes.db"
  ./sync_schedule_from_hermes.sh "$DATA_DIR/schedule_live"
  export LESSONS_DB="$DATA_DIR/lessons_from_hermes.db"
  export SCHEDULE_DIR="$DATA_DIR/schedule_live"
elif [ "$LIVE_SCHEDULE" -eq 1 ]; then
  echo "Pulling live family schedule from Hermes..."
  ./sync_schedule_from_hermes.sh "$DATA_DIR/schedule_live"
  export SCHEDULE_DIR="$DATA_DIR/schedule_live"
fi

# Local runs use the selected local DB/schedule files after any explicit pull.
# Fly sets both URLs in fly.toml; leaving them unset locally must not trigger a
# private-network sync or an attempted write to the production-only /data path.
export HERMES_LESSON_DB_URL="${HERMES_LESSON_DB_URL:-}"
export HERMES_SCHEDULE_BASE_URL="${HERMES_SCHEDULE_BASE_URL:-}"

PORT="${PORT:-8000}"
echo "Starting dashboard at http://localhost:${PORT}  (Ctrl+C to stop)"
if [ -n "${SCHEDULE_DIR:-}" ]; then
  echo "SCHEDULE_DIR=${SCHEDULE_DIR}"
fi
if [ -n "${LESSONS_DB:-}" ]; then
  echo "LESSONS_DB=${LESSONS_DB}"
fi
echo "Log in with dev creds: randy/randy or tl/tl — then click Family Schedule."
echo "Schedule page: http://localhost:${PORT}/schedule"
exec .venv/bin/uvicorn app:app --reload --port "${PORT}"
