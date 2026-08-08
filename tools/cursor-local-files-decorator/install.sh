#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: bash tools/cursor-local-files-decorator/install.sh [--cursor|--vscode]

Installs the local Explorer decoration extension by symlinking this folder into
the local editor extensions directory.

Default: --cursor
USAGE
}

editor="cursor"
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
elif [[ "${1:-}" == "--vscode" ]]; then
  editor="vscode"
elif [[ "${1:-}" == "--cursor" || "${1:-}" == "" ]]; then
  editor="cursor"
else
  usage >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
extension_id="fof-local-files-decorator"

if [[ "$editor" == "cursor" ]]; then
  extensions_dir="$HOME/.cursor/extensions"
else
  extensions_dir="$HOME/.vscode/extensions"
fi

target="$extensions_dir/$extension_id"

mkdir -p "$extensions_dir"

if [[ -L "$target" ]]; then
  current_target="$(readlink "$target")"
  if [[ "$current_target" == "$script_dir" ]]; then
    echo "Already installed: $target -> $script_dir"
    exit 0
  fi
  echo "Replacing existing symlink: $target -> $current_target"
  rm "$target"
elif [[ -e "$target" ]]; then
  echo "Refusing to replace non-symlink path: $target" >&2
  echo "Move or remove it manually, then re-run this installer." >&2
  exit 1
fi

ln -s "$script_dir" "$target"
echo "Installed: $target -> $script_dir"
echo "Reload $editor: Command Palette -> Developer: Reload Window"
