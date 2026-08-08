"""
Batch-evaluate de novo draft variants against references (M3 Phase E).

Builds deterministic drafts for all pairs; LLM variants when --llm is set.
Scores each variant with the M2 eval harness and writes denovo-eval-results.md.

Run from repo root:
    .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/run_draft_eval.py
    .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/run_draft_eval.py --limit 5
    .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/run_draft_eval.py --llm --limit 3
"""
import argparse
import csv
import os
import statistics
import sys
import tempfile
from collections import defaultdict
from unittest.mock import MagicMock

CATALOG_REL = os.path.join("apps", "transcription", "stellar-transcriber", "references", "corpus-inventory-catalog.csv")
CORPORA = ["deutsch", "pv", "sovereign-child"]
VARIANTS = [
    ("single", "deterministic", "_draftds"),
    ("single", "llm", "_draftls"),
    ("dual", "deterministic", "_draftdd"),
    ("dual", "llm", "_draftld"),
]

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
os.environ.setdefault("ELEVENLABS_API_KEY", "unused-for-draft-eval")
sys.modules.setdefault("elevenlabs", MagicMock())
sys.modules.setdefault("elevenlabs.client", MagicMock())

from core.denovo import (
    create_draft_deterministic,
    create_draft_llm,
    merge_dual_deterministic,
    merge_dual_llm,
)
from core.fileops import get_current_datetime_filefriendly, get_heading
from core.transcript_eval import (
    EVAL_CODE_VERSION,
    evaluate_transcript,
    get_normalization_policy,
    load_eval_corpus_config,
)
def suffix_from_filename(filename):
    base, ext = os.path.splitext(filename)
    if ext != ".md":
        return None
    idx = base.rfind("_")
    if idx == -1:
        return None
    return base[idx:] + ext
def pick_ref_path(repo_root, s3_keys, ref_priority):
    keys_by_suffix = {}
    for key in s3_keys:
        suffix = suffix_from_filename(os.path.basename(key))
        if suffix:
            keys_by_suffix[suffix] = key
    for suffix in ref_priority:
        key = keys_by_suffix.get(suffix)
        if not key:
            continue
        path = os.path.join(repo_root, key)
        if os.path.isfile(path) and get_heading(path, "### transcript"):
            return path
    return None
def pick_eval_keys(s3_keys, eval_suffixes):
    result = {}
    keys_by_suffix = {}
    for key in s3_keys:
        suffix = suffix_from_filename(os.path.basename(key))
        if suffix:
            keys_by_suffix[suffix] = key
    for suffix in eval_suffixes:
        if suffix in keys_by_suffix:
            result[suffix] = keys_by_suffix[suffix]
    return result
def load_catalog_rows(catalog_path):
    rows = []
    with open(catalog_path, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("has_pair") == "yes":
                rows.append(row)
    return rows
def build_variant(raw_a, raw_b, mode, method, profile, tmpdir):
    """Build one draft variant; return eval path."""
    if mode == "single":
        raw = raw_a
        if method == "deterministic":
            return create_draft_deterministic(raw, profile=profile, output_path=os.path.join(tmpdir, os.path.basename(raw).replace(".md", "_draftds.md")))
        return create_draft_llm(raw, profile=profile)
    if method == "deterministic":
        return merge_dual_deterministic(raw_a, raw_b, profile=profile)
    return merge_dual_llm(raw_a, raw_b, profile=profile)
def summarize_metric(rows, key):
    vals = [float(r[key]) for r in rows if r.get(key) not in (None, "")]
    if not vals:
        return None
    return {"count": len(vals), "mean": round(statistics.mean(vals), 2), "median": round(statistics.median(vals), 2)}
def write_denovo_results_markdown(repo_root, run_ts, config, summaries, total_runs, llm_ran):
    out_path = os.path.join(repo_root, "apps", "transcription", "stellar-transcriber",
                            "references", "denovo-eval-results.md")
    lines = [
        "file: apps/transcription/stellar-transcriber/references/denovo-eval-results.md",
        "title: Stellar Transcriber — de novo eval results",
        f"last-updated: {run_ts[:10].replace('-', '-')}_{run_ts.split('_')[-1] if '_' in run_ts else '0000'}",
        "ai: Cursor - Composer 2.5 Fast",
        "session: `Stellar Transcriber M3 — de novo cleanup pipeline`",
        "",
        f"De novo eval run `{run_ts}`. Eval code `{EVAL_CODE_VERSION}`. Total scored runs: {total_runs}. "
        f"LLM variants: {'included' if llm_ran else 'deterministic only (--llm to include)'}.",
        "",
        "## Overall score by variant (0-100 composite)",
        "",
        "| Corpus | Variant | n | Mean | Median |",
        "|--------|---------|---|------|--------|",
    ]
    for corpus in CORPORA:
        for variant_key, stats in sorted(summaries.get(corpus, {}).items()):
            if stats:
                lines.append(f"| {corpus} | {variant_key} | {stats['count']} | {stats['mean']} | {stats['median']} |")
    lines.extend([
        "",
        "## Alignment subscore (segmentation focus)",
        "",
        "| Corpus | Variant | n | Mean | Median |",
        "|--------|---------|---|------|--------|",
    ])
    for corpus in CORPORA:
        for variant_key, stats in sorted(summaries.get(corpus, {}).items()):
            align = stats.get("alignment") if stats else None
            if align:
                lines.append(f"| {corpus} | {variant_key} | {align['count']} | {align['mean']} | {align['median']} |")
    lines.extend([
        "",
        "## Speaker consistency subscore",
        "",
        "| Corpus | Variant | n | Mean | Median |",
        "|--------|---------|---|------|--------|",
    ])
    for corpus in CORPORA:
        for variant_key, stats in sorted(summaries.get(corpus, {}).items()):
            sp = stats.get("speaker") if stats else None
            if sp:
                lines.append(f"| {corpus} | {variant_key} | {sp['count']} | {sp['mean']} | {sp['median']} |")
    lines.extend([
        "",
        "## Observations",
        "",
        "- Headline metrics: alignment and speaker subscores reflect M3's segmentation-repair target.",
        "- Compare `_draftds` vs raw baseline (`baseline-eval-results.md`) for deterministic single-mode lift.",
        "- Dual LLM (`_draftld`) is the primary fusion bet; run with `--llm` when API keys are available.",
        "",
        "Regenerate: `.venv/bin/python3 apps/transcription/stellar-transcriber/scripts/run_draft_eval.py`",
    ])
    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nWrote {os.path.relpath(out_path, repo_root)}")
    return out_path

### Main
def main():
    parser = argparse.ArgumentParser(description="Evaluate de novo draft variants")
    parser.add_argument("--limit", type=int, default=None, help="K2 episodes per corpus")
    parser.add_argument("--llm", action="store_true", help="Include LLM variants (requires API keys)")
    parser.add_argument("--corpus", choices=CORPORA, default=None)
    args = parser.parse_args()
    repo_root = _REPO_ROOT
    catalog_path = os.path.join(repo_root, CATALOG_REL)
    config = load_eval_corpus_config(repo_root=repo_root)
    run_ts = get_current_datetime_filefriendly()
    all_summaries = defaultdict(dict)
    metric_rows = defaultdict(lambda: defaultdict(list))
    total_runs = 0
    corpora = [args.corpus] if args.corpus else CORPORA
    active_variants = [v for v in VARIANTS if v[1] != "llm" or args.llm]
    for corpus in corpora:
        profile = config.get(corpus, {})
        if not profile:
            continue
        ref_priority = profile.get("ref_suffix_priority", [])
        eval_suffixes = profile.get("eval_suffixes", [])
        policy = get_normalization_policy(profile.get("policy_id", "keep-all"), config)
        weights = profile.get("weights")
        pn_method = profile.get("proper_names_method", "caprules")
        output_dir = os.path.join(repo_root, "data", "stellar-eval", corpus, f"denovo-{run_ts}")
        os.makedirs(output_dir, exist_ok=True)
        corpus_rows = [r for r in load_catalog_rows(catalog_path) if r.get("corpus") == corpus]
        if args.limit:
            corpus_rows = corpus_rows[:args.limit]
        for row in corpus_rows:
            s3_keys = [k.strip() for k in row.get("s3_keys", "").split(";") if k.strip()]
            ref_path = pick_ref_path(repo_root, s3_keys, ref_priority)
            if not ref_path:
                continue
            eval_map = pick_eval_keys(s3_keys, eval_suffixes)
            raw_a = os.path.join(repo_root, eval_map.get("_nova2gen.md", ""))
            raw_b = os.path.join(repo_root, eval_map.get("_dgwhspm.md", ""))
            if not os.path.isfile(raw_a):
                continue
            with tempfile.TemporaryDirectory(prefix="denovo-eval-") as tmpdir:
                for mode, method, _suffix in active_variants:
                    if mode == "dual" and not os.path.isfile(raw_b):
                        continue
                    variant_key = f"{mode}_{method}"
                    try:
                        draft_path = build_variant(
                            raw_a, raw_b if os.path.isfile(raw_b) else raw_a,
                            mode, method, corpus, tmpdir,
                        )
                    except Exception as exc:
                        print(f"BUILD ERROR {corpus} {row.get('stem')} {variant_key}: {exc}", flush=True)
                        continue
                    try:
                        result = evaluate_transcript(
                            draft_path, ref_path, output_dir,
                            verbose=False, interactive=False, on_mismatch="continue",
                            normalization_policy=policy, corpus_weights=weights,
                            policy_id=profile.get("policy_id"), proper_names_method=pn_method,
                        )
                    except Exception as exc:
                        print(f"EVAL ERROR {corpus} {row.get('stem')} {variant_key}: {exc}", flush=True)
                        continue
                    if result is None:
                        continue
                    _, metrics = result
                    overall = metrics.get("overall_score")
                    if overall in (None, ""):
                        continue
                    metric_rows[corpus][variant_key].append({
                        "overall_score": float(overall),
                        "subscore_alignment": metrics.get("subscore_alignment"),
                        "subscore_speaker": metrics.get("subscore_speaker"),
                    })
                    total_runs += 1
                    print(f"  {corpus} {row.get('stem')} {variant_key}: {overall}", flush=True)
        for variant_key, rows in metric_rows[corpus].items():
            overall_stats = summarize_metric(rows, "overall_score")
            align_stats = summarize_metric(rows, "subscore_alignment")
            sp_stats = summarize_metric(rows, "subscore_speaker")
            if overall_stats:
                overall_stats["alignment"] = align_stats
                overall_stats["speaker"] = sp_stats
                all_summaries[corpus][variant_key] = overall_stats
    if total_runs > 0:
        write_denovo_results_markdown(repo_root, run_ts, config, all_summaries, total_runs, args.llm)
    print(f"\nTotal scored runs: {total_runs}")
    return 0 if total_runs > 0 else 1

if __name__ == "__main__":
    sys.exit(main())
