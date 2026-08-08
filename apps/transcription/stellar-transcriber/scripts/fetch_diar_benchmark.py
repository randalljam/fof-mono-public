"""
fetch_diar_benchmark.py — download external benchmark audio into the diarbench
layout, driven by the dataset registry (config/diar-datasets.json).

Only fetches files listed in the registered split lists (default: test), using
the registry's audio_mirror URL pattern, resuming partial downloads. Annotations
(RTTM/UEM) come from the external clones via build_diar_dataset.py, not from here.

Usage:
  .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/fetch_diar_benchmark.py --dataset ami-mini --split test
"""

import argparse
import os
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from build_diar_dataset import load_registry

def fetch(name, split):
    registry = load_registry()
    spec = registry["datasets"].get(name)
    if spec is None or spec.get("kind") != "external":
        raise SystemExit(f"'{name}' is not a registered external benchmark")
    list_rel = spec["lists"].get(split)
    if list_rel is None:
        raise SystemExit(f"no '{split}' list for {name}; available: {', '.join(spec['lists'])}")
    clone_root = os.path.join(registry["external_clones_dir"], spec["clone_subdir"])
    with open(os.path.join(clone_root, list_rel)) as f:
        uris = [line.strip() for line in f if line.strip()]
    audio_root = os.path.join(REPO_ROOT, spec["audio_root"])
    for uri in uris:
        dest = os.path.join(audio_root, spec["audio_pattern"].format(uri=uri))
        url = spec["audio_mirror"].format(uri=uri)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if os.path.exists(dest):
            print(f"present  {uri} ({os.path.getsize(dest)/1e6:.0f}MB)")
            continue
        print(f"fetching {uri} <- {url}")
        subprocess.run(["curl", "-sSL", "--retry", "3", "-C", "-", "-o", dest, url], check=True)
    print(f"done: {len(uris)} sessions under {audio_root}")
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", default="test")
    args = parser.parse_args()
    fetch(args.dataset, args.split)

if __name__ == "__main__":
    main()
