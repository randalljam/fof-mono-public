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
DEFAULT_REF_FOLDER = os.path.join("data", "deutsch", "f8_done_qafixed_and_vrb")
DEFAULT_REF_SUFFIX = "_vrb.md"
DEFAULT_ARMS_FOLDER = os.path.join("data", "deutsch", "f9_raw")
NOVA2_SUFFIX = "_nova2gen.md"
WHISPER_SUFFIX = "_dgwhspm.md"
DEFAULT_OUT_DIR = os.path.join("data", "stellar-eval", "dual-recovery")

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

from core.dual_missing_recovery import analyze_missing_recovery
from core.fileops import get_current_datetime_filefriendly
from core.transcript_eval import extract_transcript_data, get_normalization_policy, load_eval_corpus_config

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
def _selected_stems(episodes_arg):
    filters = [item.lower() for item in _split_values(episodes_arg)]
    if not filters:
        return list(DEUTSCH_STEMS)
    return [stem for stem in DEUTSCH_STEMS if any(item in stem.lower() for item in filters)]
def _resolve_path(path):
    if os.path.isabs(path):
        return path
    return os.path.join(_REPO_ROOT, path)
def _default_out_path():
    run_datetime = get_current_datetime_filefriendly()
    return os.path.join(_REPO_ROOT, DEFAULT_OUT_DIR, f"dual_recovery_{run_datetime}.json")
def _build_parser():
    parser = argparse.ArgumentParser(description="Measure deterministic cross-arm missing-turn recovery for Deutsch five transcripts")
    parser.add_argument("--episodes", default=None, help="Comma list of stem substrings to run; default all Deutsch five")
    parser.add_argument("--window-secs", type=float, default=30)
    parser.add_argument("--sim-threshold", type=float, default=0.6)
    parser.add_argument("--out", default=None, help=f"JSON output path; default under {DEFAULT_OUT_DIR}")
    return parser

### Data
def _load_policy():
    config = load_eval_corpus_config(repo_root=_REPO_ROOT)
    profile = config.get("deutsch", {})
    policy_id = profile.get("policy_id", "keep-all")
    return policy_id, get_normalization_policy(policy_id, config)
def _episode_paths(stem):
    return {
        "ref": os.path.join(_REPO_ROOT, DEFAULT_REF_FOLDER, stem + DEFAULT_REF_SUFFIX),
        "nova2gen": os.path.join(_REPO_ROOT, DEFAULT_ARMS_FOLDER, stem + NOVA2_SUFFIX),
        "dgwhspm": os.path.join(_REPO_ROOT, DEFAULT_ARMS_FOLDER, stem + WHISPER_SUFFIX),
    }
def _relpath(path):
    return os.path.relpath(path, _REPO_ROOT)
def _load_episode_data(stem):
    paths = _episode_paths(stem)
    missing_paths = [path for path in paths.values() if not os.path.isfile(path)]
    if missing_paths:
        for path in missing_paths:
            print(f"Warning: missing file, skipping {stem}: {_relpath(path)}")
        return None, paths
    data = {
        "ref": extract_transcript_data(paths["ref"]),
        "nova2gen": extract_transcript_data(paths["nova2gen"]),
        "dgwhspm": extract_transcript_data(paths["dgwhspm"]),
    }
    return data, paths

### Summary
def _rate(recoverable, missing):
    if not missing:
        return None
    return round(recoverable / missing, 3)
def _format_rate(rate):
    if rate is None:
        return "-"
    return f"{rate:.3f}"
def _add_counts(target, result):
    target["arm_missing_count"] += result["arm_missing_count"]
    target["recoverable_from_sibling"] += result["recoverable_from_sibling"]
    target["not_in_sibling"] += result["not_in_sibling"]
def _empty_totals():
    return {
        "arm_missing_count": 0,
        "recoverable_from_sibling": 0,
        "not_in_sibling": 0,
        "recovery_rate": None,
    }
def _finalize_totals(totals):
    totals["recovery_rate"] = _rate(totals["recoverable_from_sibling"], totals["arm_missing_count"])
    return totals
def _print_table(rows, totals):
    print("")
    print("Episode | arm | missing | recoverable | rate")
    print("--------|-----|---------|-------------|-----")
    for row in rows:
        print(
            f"{row['stem']} | {row['arm']} | {row['missing']} | "
            f"{row['recoverable']} | {_format_rate(row['rate'])}"
        )
    print("")
    print("Corpus totals")
    print("arm | missing | recoverable | rate")
    print("----|---------|-------------|-----")
    for arm in ("nova2gen", "dgwhspm"):
        arm_totals = totals["by_arm"][arm]
        print(
            f"{arm} | {arm_totals['arm_missing_count']} | "
            f"{arm_totals['recoverable_from_sibling']} | {_format_rate(arm_totals['recovery_rate'])}"
        )
    overall = totals["overall"]
    print(
        f"overall | {overall['arm_missing_count']} | "
        f"{overall['recoverable_from_sibling']} | {_format_rate(overall['recovery_rate'])}"
    )

### Run
def run(args):
    """
    Run deterministic dual-arm missing-turn recovery measurement and write JSON output.

    :param args: argparse Namespace.
    :return exit_code: int process exit code.
    """
    stems = _selected_stems(args.episodes)
    if not stems:
        print("No episodes matched the requested filters.")
        return 1
    policy_id, normalization_policy = _load_policy()
    episode_records = []
    table_rows = []
    totals = {
        "by_arm": {
            "nova2gen": _empty_totals(),
            "dgwhspm": _empty_totals(),
        },
        "overall": _empty_totals(),
    }
    for stem in stems:
        data, paths = _load_episode_data(stem)
        if data is None:
            continue
        print(f"Processing {stem}...", flush=True)
        arms = {
            "nova2gen": {
                "sibling_arm": "dgwhspm",
                "result": analyze_missing_recovery(
                    data["ref"],
                    data["nova2gen"],
                    data["dgwhspm"],
                    window_secs=args.window_secs,
                    sim_threshold=args.sim_threshold,
                    normalization_policy=normalization_policy,
                ),
            },
            "dgwhspm": {
                "sibling_arm": "nova2gen",
                "result": analyze_missing_recovery(
                    data["ref"],
                    data["dgwhspm"],
                    data["nova2gen"],
                    window_secs=args.window_secs,
                    sim_threshold=args.sim_threshold,
                    normalization_policy=normalization_policy,
                ),
            },
        }
        episode_record = {
            "stem": stem,
            "paths": {key: _relpath(path) for key, path in paths.items()},
            "arms": {},
        }
        for arm, payload in arms.items():
            result = payload["result"]
            episode_record["arms"][arm] = {
                "sibling_arm": payload["sibling_arm"],
                "result": result,
            }
            table_rows.append({
                "stem": stem,
                "arm": arm,
                "missing": result["arm_missing_count"],
                "recoverable": result["recoverable_from_sibling"],
                "rate": result["recovery_rate"],
            })
            _add_counts(totals["by_arm"][arm], result)
            _add_counts(totals["overall"], result)
        episode_records.append(episode_record)
    if not episode_records:
        print("No episodes were processed.")
        return 1
    for arm in totals["by_arm"]:
        _finalize_totals(totals["by_arm"][arm])
    _finalize_totals(totals["overall"])
    out_path = _resolve_path(args.out) if args.out else _default_out_path()
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    payload = {
        "run": {
            "mode": "strict",
            "corpus": "deutsch",
            "policy_id": policy_id,
            "window_secs": args.window_secs,
            "sim_threshold": args.sim_threshold,
        },
        "episodes": episode_records,
        "totals": totals,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    _print_table(table_rows, totals)
    print(f"Wrote {out_path}")
    return 0
def main():
    parser = _build_parser()
    args = parser.parse_args()
    return run(args)
if __name__ == "__main__":
    sys.exit(main())
