"""
Run baseline transcript evaluation across Stellar Transcriber eval corpora.

Reads the corpus inventory catalog and per-corpus config, evaluates each raw model
transcript against the highest-priority reference for paired episodes, and writes
results under data/stellar-eval/<corpus>/<run-timestamp>/ (gitignored).

Run from the repo root (after fetch_eval_pairs.py):
    .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/run_baseline_eval.py
"""
import csv
import os
import statistics
import sys
from collections import defaultdict
from unittest.mock import MagicMock

CATALOG_REL = os.path.join("apps", "transcription", "stellar-transcriber", "references", "corpus-inventory-catalog.csv")
CORPORA = ["deutsch", "pv", "sovereign-child"]

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
os.environ.setdefault("ELEVENLABS_API_KEY", "unused-for-baseline-eval")
sys.modules.setdefault("elevenlabs", MagicMock())
sys.modules.setdefault("elevenlabs.client", MagicMock())

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
    """Return local path for highest-priority reference that exists and has transcript content."""
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
    """Return {suffix: repo-relative path} for configured eval suffixes."""
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
def summarize_scores(rows_by_suffix):
    """Return {suffix: {mean, median, count}} for overall_score."""
    summary = {}
    for suffix, scores in rows_by_suffix.items():
        if not scores:
            continue
        summary[suffix] = {
            "count": len(scores),
            "mean": round(statistics.mean(scores), 2),
            "median": round(statistics.median(scores), 2),
        }
    return summary
def print_corpus_summary(corpus, summary):
    print(f"\n=== {corpus} ===")
    for suffix, stats in sorted(summary.items()):
        print(f"  {suffix:14s}  n={stats['count']:4d}  mean={stats['mean']:6.2f}  median={stats['median']:6.2f}")
def write_baseline_results_markdown(repo_root, run_ts, config, all_summaries, total_runs):
    """Write committed baseline results reference from run summaries."""
    out_path = os.path.join(repo_root, "apps", "transcription", "stellar-transcriber",
                            "references", "baseline-eval-results.md")
    lines = [
        "file: apps/transcription/stellar-transcriber/references/baseline-eval-results.md",
        "title: Stellar Transcriber — baseline eval results",
        f"last-updated: {run_ts.replace('_', '-')[:10]}_{run_ts.split('_')[-1] if '_' in run_ts else '0000'}",
        "ai: Cursor - Fable 5",
        "session: `Stellar Transcriber M2 — eval harness implementation`",
        "",
        f"Baseline eval run `{run_ts}`. Eval code version `{EVAL_CODE_VERSION}`. "
        f"Total runs: {total_runs}. Output artifacts: `data/stellar-eval/<corpus>/{run_ts}/` (gitignored).",
        "",
        "## Run configuration",
        "",
    ]
    for corpus in CORPORA:
        profile = config.get(corpus, {})
        if not profile:
            continue
        pid = profile.get("policy_id", "keep-all")
        w = profile.get("weights", {})
        lines.append(f"- **{corpus}:** policy `{pid}`; weights word={w.get('word_accuracy')} speaker={w.get('speaker')} "
                     f"alignment={w.get('alignment')} proper_names={w.get('proper_names')} quotations={w.get('quotations')}")
    lines.extend(["", "## Overall score summary (0-100 composite)", ""])
    lines.append("| Corpus | Model | n | Mean | Median |")
    lines.append("|--------|-------|---|------|--------|")
    for corpus in CORPORA:
        summary = all_summaries.get(corpus, {})
        for suffix, stats in sorted(summary.items()):
            lines.append(f"| {corpus} | {suffix} | {stats['count']} | {stats['mean']} | {stats['median']} |")
    lines.extend([
        "",
        "## Observations",
        "",
        "- **deutsch** (101 pairs): primary tuning corpus; both `_nova2gen` and `_dgwhspm` evaluated against highest-priority reference (`_qafixed` > `_vrb`).",
        "- **pv** (19 pairs only): 77 episodes remain raw-only — candidate refs `_pub`, `_postce`, `_partialcemanual` excluded pending review. Scores reflect meeting-domain stress test on limited ground truth.",
        "- **sovereign-child** (7 pairs): small held-out set.",
        "",
        "Regenerate: `.venv/bin/python3 apps/transcription/stellar-transcriber/scripts/run_baseline_eval.py` (after `fetch_eval_pairs.py`).",
    ])
    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nWrote {os.path.relpath(out_path, repo_root)}")
    return out_path

### Main
def main():
    repo_root = _REPO_ROOT
    catalog_path = os.path.join(repo_root, CATALOG_REL)
    config = load_eval_corpus_config(repo_root=repo_root)
    run_ts = get_current_datetime_filefriendly()
    all_summaries = {}
    total_runs = 0
    missing_files = 0
    for corpus in CORPORA:
        profile = config.get(corpus, {})
        if not profile:
            continue
        ref_priority = profile.get("ref_suffix_priority", [])
        eval_suffixes = profile.get("eval_suffixes", [])
        policy = get_normalization_policy(profile.get("policy_id", "keep-all"), config)
        weights = profile.get("weights")
        pn_method = profile.get("proper_names_method", "caprules")
        output_dir = os.path.join(repo_root, "data", "stellar-eval", corpus, run_ts)
        os.makedirs(output_dir, exist_ok=True)
        scores_by_suffix = defaultdict(list)
        corpus_rows = [r for r in load_catalog_rows(catalog_path) if r.get("corpus") == corpus]
        for row in corpus_rows:
            s3_keys = [k.strip() for k in row.get("s3_keys", "").split(";") if k.strip()]
            ref_key = pick_ref_path(repo_root, s3_keys, ref_priority)
            if not ref_key:
                continue
            ref_path = ref_key
            if not os.path.isfile(ref_path):
                missing_files += 1
                continue
            eval_map = pick_eval_keys(s3_keys, eval_suffixes)
            for suffix, eval_key in eval_map.items():
                eval_path = os.path.join(repo_root, eval_key)
                if not os.path.isfile(eval_path):
                    missing_files += 1
                    continue
                if not get_heading(eval_path, "### transcript"):
                    continue
                print(f"Evaluating {corpus} {row.get('stem')} {suffix} ...", flush=True)
                try:
                    result = evaluate_transcript(
                        eval_path, ref_path, output_dir,
                        verbose=False, interactive=False, on_mismatch="continue",
                        normalization_policy=policy, corpus_weights=weights,
                        policy_id=profile.get("policy_id"), proper_names_method=pn_method,
                    )
                except Exception as exc:
                    print(f"ERROR {corpus} {row.get('stem')} {suffix}: {exc}", flush=True)
                    continue
                if result is None:
                    continue
                _, metrics = result
                score = metrics.get("overall_score")
                if score not in (None, ""):
                    scores_by_suffix[suffix].append(float(score))
                    total_runs += 1
        all_summaries[corpus] = summarize_scores(scores_by_suffix)
        print_corpus_summary(corpus, all_summaries[corpus])
    print(f"\nEval code version: {EVAL_CODE_VERSION}")
    print(f"Total eval runs: {total_runs}; missing local files skipped: {missing_files}")
    print(f"Output root: data/stellar-eval/<corpus>/{run_ts}/")
    if total_runs > 0:
        write_baseline_results_markdown(repo_root, run_ts, config, all_summaries, total_runs)
    if missing_files and total_runs == 0:
        print("\nERROR: No local transcript files found. Run fetch_eval_pairs.py first.")
        return 1
    return 0
if __name__ == "__main__":
    sys.exit(main())
