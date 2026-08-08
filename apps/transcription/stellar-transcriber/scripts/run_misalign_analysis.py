import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("ELEVENLABS_API_KEY", "unused")
sys.modules.setdefault("elevenlabs", MagicMock())
sys.modules.setdefault("elevenlabs.client", MagicMock())

import argparse
import json

CATALOG_REL = os.path.join("apps", "transcription", "stellar-transcriber", "references", "corpus-inventory-catalog.csv")
DEUTSCH_STEMS = [
    "2024-08-26_Reason Is Fun - Ep6 Are Feelings Ideas",
    "2024-03-31_Sagenhaft und Sonderbar der Podcast",
    "2024-03-04_Alex OConnor - The Multiverse is Real",
    "2024-01-04_Reason Is Fun - Ep5 The Art of Decision Making",
    "2024-01-01_Arjun Khemani - Free-Will TCS and Anarcho-Capitalism",
]
DEFAULT_CANDIDATE_SUFFIXES = ["_nova2gen.md", "_dgwhspm.md"]
DEFAULT_CANDIDATE_FOLDER = os.path.join("data", "deutsch", "f9_raw")
DEFAULT_REF_FOLDER = os.path.join("data", "deutsch", "f8_done_qafixed_and_vrb")
DEFAULT_REF_SUFFIX = "_vrb.md"
DEFAULT_OUT_DIR = os.path.join("data", "stellar-eval", "misalign-runs")
DEFAULT_JSONL = os.path.join("apps", "transcription", "stellar-transcriber", "references", "stellar-run-log.jsonl")
DEFAULT_MD = os.path.join("apps", "transcription", "stellar-transcriber", "references", "stellar-run-log.md")

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

from core.fileops import get_current_datetime_filefriendly
from core.misalign_classify import classify_misalignment_windows
from core.stellar_run_log import append_run_record, build_episode_record, build_run_record, render_run_log_md
from core.transcript_eval import get_normalization_policy, load_eval_corpus_config
from core.transcript_misalign import misalignment_windows_from_paths, write_misalignment_windows_json

### Args
def _split_values(value):
    if value is None:
        return []
    if isinstance(value, list):
        pieces = []
        for item in value:
            pieces.extend(_split_values(item))
        return pieces
    return [item.strip() for item in str(value).split(",") if item.strip()]
def _resolve_path(path):
    if os.path.isabs(path):
        return path
    return os.path.join(_REPO_ROOT, path)
def _selected_stems(episodes_arg):
    filters = [item.lower() for item in _split_values(episodes_arg)]
    if not filters:
        return list(DEUTSCH_STEMS)
    return [stem for stem in DEUTSCH_STEMS if any(item in stem.lower() for item in filters)]
def _asr_from_suffix(suffix):
    name = suffix
    if name.endswith(".md"):
        name = name[:-3]
    return name.lstrip("_")
def _build_parser():
    parser = argparse.ArgumentParser(description="Extract and optionally classify Stellar Transcriber misalignment windows")
    parser.add_argument("--episodes", default=None, help="Comma list of stem substrings to run; default all Deutsch five")
    parser.add_argument("--candidate-folder", default=DEFAULT_CANDIDATE_FOLDER)
    parser.add_argument("--candidate-suffixes", nargs="+", default=DEFAULT_CANDIDATE_SUFFIXES)
    parser.add_argument("--ref-folder", default=DEFAULT_REF_FOLDER)
    parser.add_argument("--ref-suffix", default=DEFAULT_REF_SUFFIX)
    parser.add_argument("--mode", choices=["strict", "loose"], default="strict")
    parser.add_argument("--context-segments", type=int, default=1)
    parser.add_argument("--model", default="gpt-5-mini")
    parser.add_argument("--limit-windows", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Skip LLM classification")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--jsonl", default=DEFAULT_JSONL)
    parser.add_argument("--md", default=DEFAULT_MD)
    parser.add_argument("--notes", default="")
    return parser

### Run
def _top_labels(label_counts):
    if not label_counts:
        return "-"
    items = sorted(label_counts.items(), key=lambda item: (-item[1], item[0]))[:3]
    return ", ".join(f"{label}:{count}" for label, count in items)
def _print_summary(rows, usage_summary, dry_run):
    print("")
    print("Episode | ASR | strict | loose | windows | top labels")
    print("--------|-----|--------|-------|---------|-----------")
    for row in rows:
        print(
            f"{row['stem']} | {row['asr']} | {row['strict']} | {row['loose']} | "
            f"{row['n_windows']} | {_top_labels(row.get('label_counts') or {})}"
        )
    print("")
    if dry_run:
        print("Cost summary: dry-run, no LLM usage.")
    else:
        print("Cost summary: " + json.dumps(usage_summary or {}, sort_keys=True))
def _pair_paths(stem, suffix, candidate_folder, ref_folder, ref_suffix):
    candidate_path = os.path.join(candidate_folder, stem + suffix)
    ref_path = os.path.join(ref_folder, stem + ref_suffix)
    return candidate_path, ref_path
def _load_policy():
    config = load_eval_corpus_config(repo_root=_REPO_ROOT)
    profile = config.get("deutsch", {})
    policy_id = profile.get("policy_id", "keep-all")
    return policy_id, get_normalization_policy(policy_id, config)
def run(args):
    """
    Run misalignment extraction, optional classification, and ledger rendering.

    :param args: argparse Namespace.
    :return exit_code: int process exit code.
    """
    stems = _selected_stems(args.episodes)
    if not stems:
        print("No episodes matched the requested filters.")
        return 1
    candidate_folder = _resolve_path(args.candidate_folder)
    ref_folder = _resolve_path(args.ref_folder)
    out_dir = _resolve_path(args.out_dir)
    jsonl_path = _resolve_path(args.jsonl)
    md_path = _resolve_path(args.md)
    suffixes = _split_values(args.candidate_suffixes)
    run_datetime = get_current_datetime_filefriendly()
    run_id = f"misalign_{run_datetime}"
    run_dir = os.path.join(out_dir, run_id)
    os.makedirs(run_dir, exist_ok=True)
    policy_id, normalization_policy = _load_policy()
    usage_accumulator = None
    if not args.dry_run:
        from core.llm import LlmUsageAccumulator

        usage_accumulator = LlmUsageAccumulator(args.model)
    episode_records = []
    for stem in stems:
        for suffix in suffixes:
            candidate_path, ref_path = _pair_paths(stem, suffix, candidate_folder, ref_folder, args.ref_suffix)
            if not os.path.isfile(ref_path):
                print(f"Warning: missing reference, skipping {stem}: {ref_path}")
                continue
            if not os.path.isfile(candidate_path):
                print(f"Warning: missing candidate, skipping {stem} {suffix}: {candidate_path}")
                continue
            print(f"Processing {stem} {suffix}...", flush=True)
            result = misalignment_windows_from_paths(
                candidate_path, ref_path, mode=args.mode, context_segments=args.context_segments,
                normalization_policy=normalization_policy)
            classify_summary = None
            if not args.dry_run:
                classify_summary = classify_misalignment_windows(
                    result, model=args.model, limit=args.limit_windows,
                    usage_accumulator=usage_accumulator)
            asr = _asr_from_suffix(suffix)
            out_path = os.path.join(run_dir, f"{stem}__{asr}_windows.json")
            write_misalignment_windows_json(result, out_path)
            episode_records.append(build_episode_record(stem, asr, args.mode, result, classify_summary=classify_summary))
    if not episode_records:
        print("No episode/candidate pairs were processed.")
        return 1
    run_record = build_run_record(
        run_id, run_datetime, args.mode, "deutsch", "deutsch",
        "dry-run" if args.dry_run else args.model, policy_id, episode_records, run_dir,
        notes=args.notes)
    append_run_record(run_record, jsonl_path)
    render_run_log_md(jsonl_path, md_path)
    usage_summary = usage_accumulator.summary() if usage_accumulator else None
    _print_summary(episode_records, usage_summary, args.dry_run)
    print(f"Wrote windows under {run_dir}")
    print(f"Appended {jsonl_path}")
    print(f"Rendered {md_path}")
    return 0
def main():
    parser = _build_parser()
    args = parser.parse_args()
    return run(args)
if __name__ == "__main__":
    sys.exit(main())
