"""Build single or dual transcript review ledgers as JSON and Markdown."""
import argparse
import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("ELEVENLABS_API_KEY", "unused-for-review-ledger")
sys.modules.setdefault("elevenlabs", MagicMock())
sys.modules.setdefault("elevenlabs.client", MagicMock())

CATALOG_REL = os.path.join(
    "apps", "transcription", "stellar-transcriber", "references",
    "corpus-inventory-catalog.csv",
)
def find_repo_root(start_dir):
    current = os.path.abspath(start_dir)
    while True:
        if os.path.isfile(os.path.join(current, CATALOG_REL)):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            raise FileNotFoundError(f"Could not locate repo root containing {CATALOG_REL}")
        current = parent
REPO_ROOT = find_repo_root(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
def _default_out(ref_path, mode, source_path=None):
    if source_path:
        stem = os.path.splitext(os.path.basename(source_path))[0]
    else:
        stem = os.path.basename(ref_path).rsplit("_", 1)[0]
    return os.path.join(
        REPO_ROOT, "data", "stellar-eval", "review-ledgers",
        f"{stem}_{mode}-review-ledger.json",
    )
def _episode_stem(path):
    from core.draftds_change_ledger import _episode_stem as stem_from_path
    return stem_from_path(path)
def _add_shared_args(parser):
    parser.add_argument("--ref", required=True, help="Human-reviewed reference transcript")
    parser.add_argument("--profile", default=None, help="Corpus profile, e.g. pv or deutsch")
    parser.add_argument("--out", default=None, help="Output JSON path; Markdown is written beside it")
def main():
    parser = argparse.ArgumentParser(description="Build transcript review ledgers")
    subparsers = parser.add_subparsers(dest="mode", required=True)
    single = subparsers.add_parser("single", help="Review raw -> draftds -> reference")
    single.add_argument("--raw", required=True)
    single.add_argument("--draft", required=True)
    single.add_argument("--include-wording", action="store_true")
    single.add_argument("--remaining-only", action="store_true")
    _add_shared_args(single)
    dual = subparsers.add_parser("dual", help="Review source A/B -> dual output -> reference")
    dual.add_argument("--raw-a", required=True)
    dual.add_argument("--raw-b", required=True)
    dual.add_argument("--dual-output", required=True)
    _add_shared_args(dual)
    draftds_change = subparsers.add_parser(
        "draftds-change",
        help="Review raw -> draftds fixes from deterministic repair logs",
    )
    draftds_change.add_argument("--raw", required=True)
    draftds_change.add_argument("--draft", default=None, help="Optional existing draftds file to verify")
    draftds_change.add_argument("--profile", default=None, help="Corpus profile, e.g. pv or deutsch")
    draftds_change.add_argument("--out", default=None, help="Output JSON path; Markdown is written beside it")
    draftds_change.add_argument(
        "--max-cases-per-type",
        type=int,
        default=8,
        help="Deprecated; markdown is summary-only",
    )
    pipeline_change = subparsers.add_parser(
        "pipeline-change",
        help="Review stage-to-stage changes (raw/draftds/draftls/dual)",
    )
    pipeline_change.add_argument("--raw", default=None)
    pipeline_change.add_argument("--draftds", default=None)
    pipeline_change.add_argument("--draftls", default=None)
    pipeline_change.add_argument("--raw-a", default=None)
    pipeline_change.add_argument("--raw-b", default=None)
    pipeline_change.add_argument("--draftds-a", default=None)
    pipeline_change.add_argument("--draftds-b", default=None)
    pipeline_change.add_argument("--draftld", default=None)
    pipeline_change.add_argument("--draftls-a", default=None)
    pipeline_change.add_argument("--draftls-b", default=None)
    pipeline_change.add_argument("--draftls-draftld", default=None)
    pipeline_change.add_argument("--profile", default=None)
    pipeline_change.add_argument("--out", default=None, help="Output JSON path; default includes run timestamp")
    pipeline_change.add_argument(
        "--run-suffix",
        default=None,
        help="Optional slug inserted before run timestamp in default output filename",
    )
    args = parser.parse_args()
    from core.review_ledger import (
        build_dual_review_ledger,
        build_single_review_ledger,
        write_review_ledger,
    )
    from core.draftds_change_ledger import (
        build_draftds_change_ledger,
        build_pipeline_change_ledger,
        write_draftds_change_ledger,
        write_pipeline_change_ledger,
        _normalize_episode_stem,
    )
    if args.mode == "pipeline-change":
        from core.fileops import get_current_datetime_filefriendly

        stem = _normalize_episode_stem(
            args.raw, args.draftds, args.raw_a, args.raw_b, args.draftls_a, args.draftls_b)
        run_ts = get_current_datetime_filefriendly()
        suffix = f"-{args.run_suffix}" if args.run_suffix else ""
        out_path = os.path.abspath(args.out or os.path.join(
            REPO_ROOT, "data", "stellar-eval", "review-ledgers",
            f"pipeline-change-ledger_{stem}{suffix}_{run_ts}.json",
        ))
        existing_path = out_path if os.path.isfile(out_path) else None
        payload = build_pipeline_change_ledger(
            raw_path=args.raw,
            draftds_path=args.draftds,
            draftls_path=args.draftls,
            raw_a_path=args.raw_a,
            raw_b_path=args.raw_b,
            draftds_a_path=args.draftds_a,
            draftds_b_path=args.draftds_b,
            draftld_path=args.draftld,
            draftls_a_path=args.draftls_a,
            draftls_b_path=args.draftls_b,
            draftls_draftld_path=args.draftls_draftld,
            profile=args.profile,
            existing_path=existing_path,
        )
        payload["run_timestamp"] = run_ts
        if args.run_suffix:
            payload["run_suffix"] = args.run_suffix
        json_path, markdown_path = write_pipeline_change_ledger(payload, out_path)
        print(f"mode: {payload['mode']}")
        print(f"stages: {payload['summary']['stage_ids']}")
        print(f"changes: {payload['summary']['change_count']}")
        print(f"Wrote {json_path}")
        print(f"Wrote {markdown_path}")
        return 0
    if args.mode == "draftds-change":
        source_path = args.raw
        stem = os.path.splitext(os.path.basename(source_path))[0]
        out_path = os.path.abspath(args.out or os.path.join(
            REPO_ROOT, "data", "stellar-eval", "review-ledgers",
            f"{stem}_draftds-change-ledger.json",
        ))
        existing_path = out_path if os.path.isfile(out_path) else None
        payload = build_draftds_change_ledger(
            args.raw,
            profile=args.profile,
            draft_path=args.draft,
            existing_path=existing_path,
        )
        json_path, markdown_path = write_draftds_change_ledger(
            payload, out_path, max_cases_per_type=args.max_cases_per_type,
        )
        print(f"mode: {payload['mode']}")
        print(f"repairs: {payload['summary']['change_count']}")
        print(f"segments: {payload['summary']['input_segment_count']} -> {payload['summary']['output_segment_count']}")
        print(f"change type counts: {payload['summary']['change_type_counts']}")
        if payload.get("draft_matches_recomputed") is False:
            print("WARNING: supplied draftds does not exactly match a fresh deterministic run")
        print(f"Wrote {json_path}")
        print(f"Wrote {markdown_path}")
        return 0
    source_path = args.raw if args.mode == "single" else args.dual_output
    out_path = os.path.abspath(args.out or _default_out(args.ref, args.mode, source_path))
    existing_path = out_path if os.path.isfile(out_path) else None
    if args.mode == "single":
        payload = build_single_review_ledger(
            args.raw, args.draft, args.ref,
            profile=args.profile,
            include_wording=args.include_wording,
            include_fixed=not args.remaining_only,
            existing_path=existing_path,
        )
    else:
        payload = build_dual_review_ledger(
            args.raw_a, args.raw_b, args.dual_output, args.ref,
            profile=args.profile,
            existing_path=existing_path,
        )
    json_path, markdown_path = write_review_ledger(payload, out_path)
    print(f"mode: {payload['mode']}")
    print(f"cases: {payload['summary']['case_count']}")
    print(f"status counts: {payload['summary']['status_counts']}")
    if payload["mode"] == "dual" and not payload.get("choices_matched_exactly"):
        print("WARNING: dual output does not exactly match the supplied A/B inputs")
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")
    return 0
if __name__ == "__main__":
    sys.exit(main())
