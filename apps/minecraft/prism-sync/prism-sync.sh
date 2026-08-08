#!/usr/bin/env bash
#
# AGENT INSTRUCTIONS — read before running this script for the user:
#   When the user asks you to run this sync for a particular Prism instance name
#   (or several), pass those names on the command line with one --include switch
#   per name, e.g.:
#       apps/minecraft/prism-sync/prism-sync.sh --include "MathQuest Cataclysm" --include "Skyhanni"
#   Do NOT edit the hardcoded INSTANCE_NAME_INCLUDES array in this script to do
#   this — leave it empty. Only change the script file itself if the user
#   explicitly asks you to. The INSTANCE_NAME_EXCLUDES array stays as-is unless
#   the user asks otherwise.
#
# Common ways to run this from the repo root:
#   apps/minecraft/prism-sync/prism-sync.sh
#     Preview all enabled computers, then prompt before real sync.
#
#   apps/minecraft/prism-sync/prism-sync.sh --computer 1
#     Preview only computer slot 1, then prompt before real sync.
#
#   apps/minecraft/prism-sync/prism-sync.sh --computer all
#     Preview all enabled computers, then prompt before real sync.
#
#   apps/minecraft/prism-sync/prism-sync.sh --include "MathQuest Cataclysm"
#     Sync only instances whose names contain the given substring(s).
#     Repeat --include to add more names.
#
#   apps/minecraft/prism-sync/prism-sync.sh --skip-prompt
#     Preview all enabled computers, then real sync without prompting.
#
#   apps/minecraft/prism-sync/prism-sync.sh --computer 1 --skip-prompt
#     Preview computer slot 1, then real sync without prompting.
#
#   apps/minecraft/prism-sync/prism-sync.sh --computer all --skip-prompt
#     Preview all enabled computers, then real sync without prompting.
#
#   apps/minecraft/prism-sync/prism-sync.sh --update-existing
#     Also update target instance folders that already exist.
#
#   apps/minecraft/prism-sync/prism-sync.sh --log
#     Append a markdown record of this run to the sync log (off by default).


set -euo pipefail

# Sync Prism Launcher instances from Randy's master laptop, host4, to selected family Macs.
# Every run previews the exact rsync work first. Use --skip-prompt only for automation.

SKIP_PROMPT=0
UPDATE_EXISTING=0
WRITE_LOG=0
REQUESTED_COMPUTERS=()

SOURCE_INSTANCES_DIR="${HOME}/Library/Application Support/PrismLauncher/instances"
SOURCE_ICONS_DIR="${HOME}/Library/Application Support/PrismLauncher/icons"
REMOTE_INSTANCES_DIR='Library/Application Support/PrismLauncher/instances'
REMOTE_ICONS_DIR='Library/Application Support/PrismLauncher/icons'
PRISM_SYNC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${PRISM_SYNC_DIR}/_data/prism-sync_log.md"
DRY_RUN_DETAILS_FILE="$(mktemp -t prism-sync-dry-run.XXXXXX)"
REAL_SYNC_DETAILS_FILE="$(mktemp -t prism-sync-real-run.XXXXXX)"

cleanup() {
  rm -f "${DRY_RUN_DETAILS_FILE}" "${REAL_SYNC_DETAILS_FILE}"
}

trap cleanup EXIT

# Computer slots. Enable a computer by setting its matching TARGET_ENABLED entry to 1.
TARGET_IDS=("1" "2" "3" "4")
TARGET_NAMES=("host1-Kid1" "host3-carer" "host5-randytrue" "host2-tl-user")
TARGET_HOSTS=("host1.local" "host3.local" "host5.local" "host2.local")
TARGET_USERS=("Kid1" "carer" "randytrue" "tl-user")
TARGET_ENABLED=("1" "1" "1" "1")

# Any local Prism instance whose name contains one of these substrings will be skipped.
# Matching is case-sensitive and whitespace-sensitive.
INSTANCE_NAME_EXCLUDES=(
  "_Base"
)

# If empty, every non-excluded instance is eligible. If set, only instances whose
# names contain at least one of these substrings are synced. Matching is case-sensitive
# and whitespace-sensitive.
#
# Leave this array empty and pass instance names at runtime with --include instead
# (see the AGENT INSTRUCTIONS at the top of this file). Any --include values are
# appended to this list.
INSTANCE_NAME_INCLUDES=()

RSYNC_EXCLUDES=(
  "--exclude=minecraft/saves/"
  "--exclude=minecraft/screenshots/"
  "--exclude=minecraft/logs/"
  "--exclude=minecraft/crash-reports/"
  "--exclude=minecraft/config/options.txt"
  "--exclude=minecraft/options.txt"
)

SYNC_INSTANCES=()
SKIPPED_BY_EXCLUDE=()
SKIPPED_BY_INCLUDE=()
SELECTED_TARGET_INDEXES=()
TARGET_SYNC_INSTANCES=()
TARGET_SKIPPED_EXISTING_INSTANCES=()

usage() {
  cat <<'USAGE'
Usage:
  apps/minecraft/prism-sync/prism-sync.sh
  apps/minecraft/prism-sync/prism-sync.sh --computer 1
  apps/minecraft/prism-sync/prism-sync.sh --computer all
  apps/minecraft/prism-sync/prism-sync.sh --include "instance name substring"
  apps/minecraft/prism-sync/prism-sync.sh --update-existing
  apps/minecraft/prism-sync/prism-sync.sh --skip-prompt
  apps/minecraft/prism-sync/prism-sync.sh --log

Examples:
  apps/minecraft/prism-sync/prism-sync.sh
  apps/minecraft/prism-sync/prism-sync.sh --computer 1
  apps/minecraft/prism-sync/prism-sync.sh --include "MathQuest Cataclysm"
  apps/minecraft/prism-sync/prism-sync.sh --include "MathQuest Cataclysm" --include "Skyhanni"
  apps/minecraft/prism-sync/prism-sync.sh --computer 1 --update-existing
  apps/minecraft/prism-sync/prism-sync.sh --computer all --skip-prompt

Default behavior:
  - Select every enabled computer.
  - Show selected computers.
  - Show synced and skipped Prism instances.
  - Skip target instance folders that already exist.
  - Run rsync in dry-run preview mode.
  - Prompt before running the real sync.
  - Do NOT write to the sync log (use --log to opt in).

Choosing which instances to sync:
  --include "substring" syncs only instances whose names contain that substring.
  Repeat --include to allow more names. If no --include is given (and the
  hardcoded INSTANCE_NAME_INCLUDES is empty), every non-excluded instance syncs.

Update existing instances:
  --update-existing updates target instance folders that already exist.
  Without this switch, existing target instance folders are left untouched.

Automation:
  --skip-prompt still runs the dry-run preview first, then continues without asking.

Logging:
  --log appends a markdown record of the run to the sync log. Off by default.

Configuration:
  - Edit TARGET_* arrays to add family Macs.
  - Set TARGET_ENABLED to 1 or 0 for each computer slot.
  - Edit INSTANCE_NAME_EXCLUDES to skip local Prism instances by name.
  - Prefer --include over editing INSTANCE_NAME_INCLUDES for per-run instance
    selection. Leave INSTANCE_NAME_INCLUDES empty to sync every non-excluded
    instance when no --include is given.
USAGE
}

instance_name_contains_any() {
  local instance="$1"
  shift
  local patterns=("$@")
  local pattern

  for pattern in "${patterns[@]}"; do
    if [[ "${instance}" == *"${pattern}"* ]]; then
      return 0
    fi
  done

  return 1
}

matches_instance_name_exclude() {
  [[ "${#INSTANCE_NAME_EXCLUDES[@]}" -eq 0 ]] && return 1
  instance_name_contains_any "$1" "${INSTANCE_NAME_EXCLUDES[@]}"
}

matches_instance_name_include() {
  [[ "${#INSTANCE_NAME_INCLUDES[@]}" -eq 0 ]] && return 0
  instance_name_contains_any "$1" "${INSTANCE_NAME_INCLUDES[@]}"
}

target_index_for_id() {
  local requested_id="$1"
  local i

  for i in "${!TARGET_IDS[@]}"; do
    if [[ "${TARGET_IDS[$i]}" == "${requested_id}" ]]; then
      printf '%s\n' "${i}"
      return 0
    fi
  done

  return 1
}

add_selected_target() {
  local requested_id="$1"
  local target_index
  local existing

  target_index="$(target_index_for_id "${requested_id}")" || {
    echo "Error: unknown computer slot '${requested_id}'." >&2
    exit 2
  }

  if [[ "${TARGET_ENABLED[$target_index]}" != "1" ]]; then
    echo "Error: computer ${requested_id} (${TARGET_NAMES[$target_index]}) is disabled in the script." >&2
    echo "Enable it by setting its TARGET_ENABLED value to 1 after filling in host and user." >&2
    exit 2
  fi

  if [[ -z "${TARGET_HOSTS[$target_index]}" || -z "${TARGET_USERS[$target_index]}" ]]; then
    echo "Error: computer ${requested_id} (${TARGET_NAMES[$target_index]}) is missing host or user config." >&2
    exit 2
  fi

  if [[ "${#SELECTED_TARGET_INDEXES[@]}" -gt 0 ]]; then
    for existing in "${SELECTED_TARGET_INDEXES[@]}"; do
      if [[ "${existing}" == "${target_index}" ]]; then
        return 0
      fi
    done
  fi

  SELECTED_TARGET_INDEXES+=("${target_index}")
}

select_all_enabled_targets() {
  local i

  for i in "${!TARGET_IDS[@]}"; do
    if [[ "${TARGET_ENABLED[$i]}" == "1" ]]; then
      add_selected_target "${TARGET_IDS[$i]}"
    fi
  done
}

discover_instances() {
  local source_path
  local instance

  shopt -s nullglob
  for source_path in "${SOURCE_INSTANCES_DIR}"/*; do
    if [[ ! -d "${source_path}" || ! -f "${source_path}/instance.cfg" ]]; then
      continue
    fi

    instance="${source_path##*/}"
    if matches_instance_name_exclude "${instance}"; then
      SKIPPED_BY_EXCLUDE+=("${instance}")
    elif ! matches_instance_name_include "${instance}"; then
      SKIPPED_BY_INCLUDE+=("${instance}")
    else
      SYNC_INSTANCES+=("${instance}")
    fi
  done
  shopt -u nullglob
}

print_core_info() {
  local target_index
  local instance
  local excluded
  local included
  local rsync_exclude
  local yellow=""
  local reset=""

  if [[ -t 1 ]]; then
    yellow=$'\033[1;33m'
    reset=$'\033[0m'
  fi

  echo "${yellow}Selected computers:${reset}"
  for target_index in "${SELECTED_TARGET_INDEXES[@]}"; do
    echo "  [${TARGET_IDS[$target_index]}] ${TARGET_NAMES[$target_index]}: ${TARGET_USERS[$target_index]}@${TARGET_HOSTS[$target_index]}"
  done

  echo
  echo "Existing target instances:"
  if [[ "${UPDATE_EXISTING}" -eq 1 ]]; then
    echo "  Update existing target instance folders: yes (--update-existing)"
  else
    echo "  Update existing target instance folders: no (default)"
  fi

  echo
  echo "Prism icon library:"
  if [[ -d "${SOURCE_ICONS_DIR}" ]]; then
    echo "  Sync enabled: ${SOURCE_ICONS_DIR}"
  else
    echo "  Sync skipped: local Prism icon library not found"
  fi

  echo
  echo "Instance-name exclusions:"
  if [[ "${#INSTANCE_NAME_EXCLUDES[@]}" -eq 0 ]]; then
    echo "  none"
  else
    for excluded in "${INSTANCE_NAME_EXCLUDES[@]}"; do
      echo "  ${excluded}"
    done
  fi

  echo
  echo "Instance-name includes:"
  if [[ "${#INSTANCE_NAME_INCLUDES[@]}" -eq 0 ]]; then
    echo "  all non-excluded instances"
  else
    for included in "${INSTANCE_NAME_INCLUDES[@]}"; do
      echo "  ${included}"
    done
  fi

  echo
  echo "Rsync excludes:"
  for rsync_exclude in "${RSYNC_EXCLUDES[@]}"; do
    echo "  ${rsync_exclude}"
  done

  echo
  echo "${yellow}Instances that will sync:${reset}"
  if [[ "${#TARGET_SYNC_INSTANCES[@]}" -eq 0 ]]; then
    echo "  none"
  else
    for instance in "${TARGET_SYNC_INSTANCES[@]}"; do
      echo "  ${instance}"
    done
  fi

  echo
  echo "Instances skipped because they already exist on target:"
  if [[ "${#TARGET_SKIPPED_EXISTING_INSTANCES[@]}" -eq 0 ]]; then
    echo "  none"
  else
    for instance in "${TARGET_SKIPPED_EXISTING_INSTANCES[@]}"; do
      echo "  ${instance}"
    done
    if [[ "${UPDATE_EXISTING}" -ne 1 && "${#TARGET_SYNC_INSTANCES[@]}" -eq 0 ]]; then
      echo
      echo "${yellow}Note:${reset} No instance files will copy this run because matching folders already exist on the target."
      echo "  Use --update-existing to refresh them, or delete the target instance folder and sync again."
    fi
  fi

  echo
  echo "Source instances skipped by exclude list:"
  if [[ "${#SKIPPED_BY_EXCLUDE[@]}" -eq 0 ]]; then
    echo "  none"
  else
    for instance in "${SKIPPED_BY_EXCLUDE[@]}"; do
      echo "  ${instance}"
    done
  fi

  echo
  echo "Source instances skipped because they did not match include list:"
  if [[ "${#SKIPPED_BY_INCLUDE[@]}" -eq 0 ]]; then
    echo "  none"
  else
    for instance in "${SKIPPED_BY_INCLUDE[@]}"; do
      echo "  ${instance}"
    done
  fi
}

write_markdown_log() {
  local timestamp="$1"

  {
    echo
    echo "# Prism Sync - ${timestamp}"
    echo
    print_core_info
    echo
    echo "## Details"
    echo
    echo "### Dry-Run Preview"
    echo
    echo '```text'
    cat "${DRY_RUN_DETAILS_FILE}"
    echo '```'
    echo
    echo "### Real Sync"
    echo
    echo '```text'
    cat "${REAL_SYNC_DETAILS_FILE}"
    echo '```'
  } >> "${LOG_FILE}"
}

run_rsync_for_target() {
  local target_index="$1"
  local mode="$2"
  local remote_user="${TARGET_USERS[$target_index]}"
  local target="${TARGET_HOSTS[$target_index]}"
  local instance
  local source_path
  local remote_path
  local remote_instance_dir
  local escaped_remote_path
  local rsync_flags=(-az --delete --human-readable --itemize-changes)
  local target_name="${TARGET_NAMES[$target_index]}"

  if [[ "${mode}" == "dry-run" ]]; then
    rsync_flags+=(--dry-run)
    echo
    echo "Dry-run preview for ${TARGET_NAMES[$target_index]} (${remote_user}@${target})"
  else
    echo
    echo "Real sync for ${TARGET_NAMES[$target_index]} (${remote_user}@${target})"
    ssh -n "${remote_user}@${target}" "mkdir -p \"\$HOME/${REMOTE_INSTANCES_DIR}\""
  fi

  for instance in "${SYNC_INSTANCES[@]}"; do
    source_path="${SOURCE_INSTANCES_DIR}/${instance}"
    remote_instance_dir="${REMOTE_INSTANCES_DIR}/${instance}"
    remote_path="${REMOTE_INSTANCES_DIR}/${instance}/"
    escaped_remote_path="$(printf '%q' "${remote_path}")"

    if [[ "${UPDATE_EXISTING}" -ne 1 ]] && ssh -n "${remote_user}@${target}" "test -d \"\$HOME/${remote_instance_dir}\""; then
      echo "Skipping existing target instance: ${instance}"
      if [[ "${mode}" == "dry-run" ]]; then
        TARGET_SKIPPED_EXISTING_INSTANCES+=("${target_name}: ${instance}")
      fi
      continue
    fi

    echo
    echo "Syncing instance: ${instance}"
    if [[ "${mode}" == "dry-run" ]]; then
      TARGET_SYNC_INSTANCES+=("${target_name}: ${instance}")
    fi
    rsync "${rsync_flags[@]}" "${RSYNC_EXCLUDES[@]}" \
      "${source_path}/" \
      "${remote_user}@${target}:${escaped_remote_path}"
  done
}

run_icon_sync_for_target() {
  local target_index="$1"
  local mode="$2"
  local remote_user="${TARGET_USERS[$target_index]}"
  local target="${TARGET_HOSTS[$target_index]}"
  local escaped_remote_icons_dir
  local rsync_flags=(-az --delete --human-readable --itemize-changes)

  if [[ ! -d "${SOURCE_ICONS_DIR}" ]]; then
    echo
    echo "Skipping Prism icon library sync; local folder not found: ${SOURCE_ICONS_DIR}"
    return 0
  fi

  if [[ "${mode}" == "dry-run" ]]; then
    rsync_flags+=(--dry-run)
    echo
    echo "Dry-run preview for Prism icon library on ${TARGET_NAMES[$target_index]} (${remote_user}@${target})"
  else
    echo
    echo "Real sync for Prism icon library on ${TARGET_NAMES[$target_index]} (${remote_user}@${target})"
    ssh -n "${remote_user}@${target}" "mkdir -p \"\$HOME/${REMOTE_ICONS_DIR}\""
  fi

  escaped_remote_icons_dir="$(printf '%q' "${REMOTE_ICONS_DIR}/")"
  rsync "${rsync_flags[@]}" \
    "${SOURCE_ICONS_DIR}/" \
    "${remote_user}@${target}:${escaped_remote_icons_dir}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --computer)
      REQUESTED_COMPUTERS+=("${2:-}")
      shift 2
      ;;
    --all)
      REQUESTED_COMPUTERS+=("all")
      shift
      ;;
    --skip-prompt|--yes)
      SKIP_PROMPT=1
      shift
      ;;
    --update-existing)
      UPDATE_EXISTING=1
      shift
      ;;
    --include)
      if [[ -z "${2:-}" ]]; then
        echo "Error: --include requires an instance-name substring." >&2
        exit 2
      fi
      INSTANCE_NAME_INCLUDES+=("$2")
      shift 2
      ;;
    --log)
      WRITE_LOG=1
      shift
      ;;
    --apply)
      echo "Error: --apply has been replaced by --skip-prompt." >&2
      usage
      exit 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ ! -d "${SOURCE_INSTANCES_DIR}" ]]; then
  echo "Error: source Prism instances folder not found:" >&2
  echo "  ${SOURCE_INSTANCES_DIR}" >&2
  exit 1
fi

if [[ "${#REQUESTED_COMPUTERS[@]}" -eq 0 ]]; then
  select_all_enabled_targets
else
  for requested in "${REQUESTED_COMPUTERS[@]}"; do
    if [[ "${requested}" == "all" ]]; then
      select_all_enabled_targets
    else
      add_selected_target "${requested}"
    fi
  done
fi

if [[ "${#SELECTED_TARGET_INDEXES[@]}" -eq 0 ]]; then
  echo "Error: no enabled computers selected." >&2
  exit 1
fi

discover_instances

if [[ "${#SYNC_INSTANCES[@]}" -eq 0 ]]; then
  echo "Error: no Prism instances found to sync after exclusions." >&2
  exit 1
fi

for target_index in "${SELECTED_TARGET_INDEXES[@]}"; do
  run_icon_sync_for_target "${target_index}" "dry-run" > >(tee -a "${DRY_RUN_DETAILS_FILE}") 2>&1
  run_rsync_for_target "${target_index}" "dry-run" > >(tee -a "${DRY_RUN_DETAILS_FILE}") 2>&1
done

echo
print_core_info
echo
if [[ "${SKIP_PROMPT}" -eq 1 ]]; then
  echo "Skipping confirmation prompt because --skip-prompt was provided."
else
  if ! read -r -p "Continue with the real sync to the selected computers? Type yes to continue: " answer; then
    echo "Cancelled. No real sync was performed."
    exit 0
  fi
  if [[ "${answer}" != "yes" ]]; then
    echo "Cancelled. No real sync was performed."
    exit 0
  fi
fi

for target_index in "${SELECTED_TARGET_INDEXES[@]}"; do
  run_icon_sync_for_target "${target_index}" "real" > >(tee -a "${REAL_SYNC_DETAILS_FILE}") 2>&1
  run_rsync_for_target "${target_index}" "real" > >(tee -a "${REAL_SYNC_DETAILS_FILE}") 2>&1
done

echo
print_core_info
if [[ "${WRITE_LOG}" -eq 1 ]]; then
  sync_timestamp="$(date '+%Y-%m-%d %H:%M:%S %Z')"
  write_markdown_log "${sync_timestamp}"
fi
echo
echo "Sync complete. Restart Prism on the selected computers; the synced instances should appear locally."
if [[ "${WRITE_LOG}" -eq 1 ]]; then
  echo "Log written to: ${LOG_FILE}"
fi
