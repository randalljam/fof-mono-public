"""
Build draft transcript(s) from raw diarized markdown.

Run from repo root:
    .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/build_draft_transcript.py \\
        --raw data/deutsch/f9_raw/2007-01-16_TED Talk_nova2gen.md --method deterministic
    .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/build_draft_transcript.py \\
        --raw-a path/_nova2gen.md --raw-b path/_dgwhspm.md --mode dual --method llm --profile deutsch
"""
import argparse
import os
import sys

CATALOG_REL = os.path.join("apps", "transcription", "stellar-transcriber", "references", "corpus-inventory-catalog.csv")

def find_repo_root(start_dir):
    current = os.path.abspath(start_dir)
    while True:
        if os.path.isfile(os.path.join(current, CATALOG_REL)):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            raise FileNotFoundError(f"Could not locate repo root containing {CATALOG_REL}")
        current = parent

_REPO_ROOT = find_repo_root(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.denovo import (
    create_draft_deterministic,
    create_draft_llm,
    merge_dual_deterministic,
    merge_dual_llm,
)
def main():
    parser = argparse.ArgumentParser(description="Build Stellar Transcriber draft transcript(s)")
    parser.add_argument("--raw", help="Single raw .md path")
    parser.add_argument("--raw-a", help="Dual mode: first raw .md")
    parser.add_argument("--raw-b", help="Dual mode: second raw .md")
    parser.add_argument("--mode", choices=["single", "dual"], default="single")
    parser.add_argument("--method", choices=["deterministic", "llm"], default="deterministic")
    parser.add_argument("--profile", default=None, help="Corpus profile name (deutsch, pv, sovereign-child)")
    parser.add_argument("--model-tier", default=None, help="LLM model tier (cheap, standard)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    if args.mode == "single":
        if not args.raw:
            parser.error("--raw required for single mode")
        raw = args.raw if os.path.isabs(args.raw) else os.path.join(_REPO_ROOT, args.raw)
        if args.method == "deterministic":
            out = create_draft_deterministic(raw, profile=args.profile, verbose=args.verbose)
        else:
            out = create_draft_llm(raw, profile=args.profile, model_tier=args.model_tier, verbose=args.verbose)
    else:
        if not args.raw_a or not args.raw_b:
            parser.error("--raw-a and --raw-b required for dual mode")
        raw_a = args.raw_a if os.path.isabs(args.raw_a) else os.path.join(_REPO_ROOT, args.raw_a)
        raw_b = args.raw_b if os.path.isabs(args.raw_b) else os.path.join(_REPO_ROOT, args.raw_b)
        if args.method == "deterministic":
            out = merge_dual_deterministic(raw_a, raw_b, profile=args.profile, verbose=args.verbose)
        else:
            out = merge_dual_llm(raw_a, raw_b, profile=args.profile, model_tier=args.model_tier, verbose=args.verbose)
    print(out)
    return 0

if __name__ == "__main__":
    sys.exit(main())
