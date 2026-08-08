"""
Alignment-first eval ladder: score segment-alignment error reduction across the draft ladder.

Ladder per episode (the M4 alignment-first plan):
  A0  raw A (_nova2gen), raw B (_dgwhspm)          — baselines
  A1  _draftds on each raw                          — deterministic single (control arm)
  A2  _draftls on each raw                          — single-LLM repair (primary target)
  A3  _draftld on raw A + raw B                     — dual-LLM merge of raws
  A4  _draftld on draftls(A) + draftls(B)           — dual-LLM merge of single-repaired drafts

For every variant, reports ABSOLUTE segment-error counts by category (missing ref
segments, spurious eval segments, boundary-error segments), the total, and the percent
error reduction vs its base raw. Word accuracy is included as a content-damage guard.

Run from the repo root:
    .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/run_alignment_eval.py --fixture
    .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/run_alignment_eval.py --fixture --skip-llm
    .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/run_alignment_eval.py \
        --raw-a <path_nova2gen.md> --raw-b <path_dgwhspm.md> --ref <path_vrb.md> --profile deutsch
"""
import argparse
import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("ELEVENLABS_API_KEY", "unused-for-alignment-eval")
sys.modules.setdefault("elevenlabs", MagicMock())
sys.modules.setdefault("elevenlabs.client", MagicMock())

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

from core.fileops import get_current_datetime_filefriendly
from core.transcript_eval import (
    evaluate_step_segments_align,
    evaluate_step_word_error_rate,
    extract_transcript_data,
    get_normalization_policy,
    load_eval_corpus_config,
)

ERROR_FIELDS = ["seg_missing_count", "seg_spurious_count", "seg_boundary_error_count", "seg_error_count"]

### Scoring
def score_alignment(eval_path, ref_path, normalization_policy=None):
    """Segment-alignment error metrics + word accuracy guard for one eval/ref pair."""
    eval_data = extract_transcript_data(eval_path)
    ref_data = extract_transcript_data(ref_path)
    if not eval_data or not ref_data:
        return None
    eval_data, align_metrics, _ = evaluate_step_segments_align(
        eval_data, ref_data, verbose=False, normalization_policy=normalization_policy)
    wer_metrics, _ = evaluate_step_word_error_rate(eval_data, ref_data, verbose=False)
    align_metrics["word_accuracy"] = wer_metrics.get("word_accuracy")
    return align_metrics
def error_reduction(base_metrics, variant_metrics, field="seg_error_count"):
    """Percent segment-error reduction of variant vs base (positive = fewer errors)."""
    if not base_metrics or not variant_metrics:
        return None
    base = base_metrics.get(field)
    var = variant_metrics.get(field)
    if base is None or var is None or base == 0:
        return None
    return round((base - var) / base * 100.0, 1)

### Ladder
def run_ladder(raw_a, raw_b, ref, profile=None, run_llm=True, include_dual=True, model_tier="cheap", provider=None, verbose=True):
    """
    Run the alignment ladder on one episode; returns list of row dicts.

    Row: {variant, base_variant, path, metrics}
    """
    from core.denovo import create_draft_deterministic, create_draft_llm, merge_dual_llm

    policy = None
    if profile:
        config = load_eval_corpus_config(repo_root=_REPO_ROOT)
        policy = get_normalization_policy(config.get(profile, {}).get("policy_id", "keep-all"), config)
    rows = []
    def add_row(variant, path, base_variant=None):
        metrics = score_alignment(path, ref, normalization_policy=policy) if path else None
        rows.append({"variant": variant, "base_variant": base_variant, "path": path, "metrics": metrics})
        if verbose and metrics:
            print(f"  {variant:<22} errors={metrics['seg_error_count']:>3} strict={metrics.get('seg_error_count_strict', '—'):>3}  "
                  f"(missing={metrics['seg_missing_count']} spurious={metrics['seg_spurious_count']} "
                  f"boundary={metrics['seg_boundary_error_count']} misplaced={metrics.get('seg_boundary_misplaced_count', '—')})  "
                  f"word_acc={metrics.get('word_accuracy'):.3f}",
                  flush=True)
        return path
    # A0 baselines
    add_row("raw_A_nova2gen", raw_a)
    add_row("raw_B_dgwhspm", raw_b)
    # A1 deterministic single (control)
    draftds_a = create_draft_deterministic(raw_a, profile=profile)
    add_row("draftds_A", draftds_a, base_variant="raw_A_nova2gen")
    draftds_b = create_draft_deterministic(raw_b, profile=profile)
    add_row("draftds_B", draftds_b, base_variant="raw_B_dgwhspm")
    draftls_a = draftls_b = None
    if run_llm:
        # A2 single-LLM repair
        draftls_a = create_draft_llm(raw_a, profile=profile, model_tier=model_tier)
        add_row("draftls_A", draftls_a, base_variant="raw_A_nova2gen")
        draftls_b = create_draft_llm(raw_b, profile=profile, model_tier=model_tier)
        add_row("draftls_B", draftls_b, base_variant="raw_B_dgwhspm")
        if include_dual:
            # A3 dual-LLM on raws
            draftld_raw, _ = merge_dual_llm(raw_a, raw_b, profile=profile, model_tier=model_tier,
                                            provider=provider, return_summary=True)
            add_row("draftld_raws", draftld_raw, base_variant="best_raw")
            # A4 dual-LLM on single-repaired drafts
            if draftls_a and draftls_b:
                draftld_ls, _ = merge_dual_llm(draftls_a, draftls_b, profile=profile, model_tier=model_tier,
                                               provider=provider, return_summary=True)
                add_row("draftld_singles", draftld_ls, base_variant="best_raw")
    return rows

### Reporting
def build_report_rows(rows):
    """Attach error-reduction percentages; base 'best_raw' uses the lower-error raw."""
    by_variant = {r["variant"]: r for r in rows}
    raws = [r for r in rows if r["variant"].startswith("raw_") and r["metrics"]]
    best_raw = min(raws, key=lambda r: r["metrics"]["seg_error_count"]) if raws else None
    for r in rows:
        base = None
        if r["base_variant"] == "best_raw":
            base = best_raw
        elif r["base_variant"]:
            base = by_variant.get(r["base_variant"])
        base_metrics = base["metrics"] if base else None
        r["error_reduction_pct"] = error_reduction(base_metrics, r["metrics"])
        r["strict_reduction_pct"] = error_reduction(base_metrics, r["metrics"], field="seg_error_count_strict")
        r["base_label"] = base["variant"] if base else ""
    return rows, (best_raw["variant"] if best_raw else None)
def format_report_md(rows, best_raw_label, title, run_info_lines):
    lines = [f"# {title}", ""]
    lines.extend(run_info_lines)
    lines.extend([
        "",
        "Segment-error accounting vs reference. `errors` = missing ref segments + spurious eval segments + boundary-error segments; `strict` counts only repairable segmentation defects (missing + spurious + misplaced-text boundaries), excluding boundary word errors. `reduction` columns = percent fewer errors than the base (its raw for singles, the better raw for duals). Word accuracy is a 0-1 content guard — it must not drop vs the raw.",
        "",
        "| Variant | Base | Errors | Strict | Missing | Spurious | Boundary | Misplaced | Reduction | Strict red. | Word acc |",
        "|---------|------|--------|--------|---------|----------|----------|-----------|-----------|-------------|----------|",
    ])
    for r in rows:
        m = r["metrics"]
        if not m:
            lines.append(f"| {r['variant']} | — | — | — | — | — | — | — | — | — | — |")
            continue
        reduction = f"{r['error_reduction_pct']}%" if r.get("error_reduction_pct") is not None else "—"
        strict_red = f"{r['strict_reduction_pct']}%" if r.get("strict_reduction_pct") is not None else "—"
        wa = m.get("word_accuracy")
        wa_str = f"{wa:.3f}" if wa is not None else "—"
        lines.append(
            f"| {r['variant']} | {r.get('base_label') or '—'} | {m['seg_error_count']} | {m.get('seg_error_count_strict', '—')} | "
            f"{m['seg_missing_count']} | {m['seg_spurious_count']} | {m['seg_boundary_error_count']} | {m.get('seg_boundary_misplaced_count', '—')} | "
            f"{reduction} | {strict_red} | {wa_str} |"
        )
    lines.append("")
    if best_raw_label:
        lines.append(f"Best raw (dual base): `{best_raw_label}`")
    return "\n".join(lines)

def rescore_ladder(raw_a, raw_b, ref, profile=None, verbose=True):
    """
    Score existing draft files (written by a prior run) without any LLM calls.
    """
    from core.fileops import add_suffix_in_str

    policy = None
    if profile:
        config = load_eval_corpus_config(repo_root=_REPO_ROOT)
        policy = get_normalization_policy(config.get(profile, {}).get("policy_id", "keep-all"), config)
    candidates = [
        ("raw_A_nova2gen", raw_a, None),
        ("raw_B_dgwhspm", raw_b, None),
        ("draftds_A", add_suffix_in_str(raw_a, "_draftds"), "raw_A_nova2gen"),
        ("draftds_B", add_suffix_in_str(raw_b, "_draftds"), "raw_B_dgwhspm"),
        ("draftls_A", add_suffix_in_str(raw_a, "_draftls"), "raw_A_nova2gen"),
        ("draftls_B", add_suffix_in_str(raw_b, "_draftls"), "raw_B_dgwhspm"),
        ("draftld_raws", add_suffix_in_str(raw_a, "_draftld"), "best_raw"),
        ("draftld_singles", add_suffix_in_str(add_suffix_in_str(raw_a, "_draftls"), "_draftld"), "best_raw"),
    ]
    rows = []
    for variant, path, base_variant in candidates:
        if not os.path.isfile(path):
            continue
        metrics = score_alignment(path, ref, normalization_policy=policy)
        rows.append({"variant": variant, "base_variant": base_variant, "path": path, "metrics": metrics})
        if verbose and metrics:
            print(f"  {variant:<22} errors={metrics['seg_error_count']:>3} strict={metrics.get('seg_error_count_strict', '—'):>3}  "
                  f"(missing={metrics['seg_missing_count']} spurious={metrics['seg_spurious_count']} "
                  f"boundary={metrics['seg_boundary_error_count']} misplaced={metrics.get('seg_boundary_misplaced_count', '—')})  "
                  f"word_acc={metrics.get('word_accuracy'):.3f}",
                  flush=True)
    return rows

### Entry points
def run_fixture_mode(args):
    fixture_script = os.path.join(_REPO_ROOT, "apps", "transcription", "stellar-transcriber",
                                  "scripts", "make_alignment_fixture.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("make_alignment_fixture", fixture_script)
    fixture_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture_mod)
    out_dir = os.path.join(_REPO_ROOT, "data", "stellar-eval", "fixtures")
    result = fixture_mod.build_fixture_set(out_dir, max_segments=args.max_segments)
    print(f"Fixture: {result['ref_segment_count']} ref segments")
    print(f"  raw A injected errors (expected): {result['expected_a']['seg_error_count']}")
    print(f"  raw B injected errors (expected): {result['expected_b']['seg_error_count']}")
    rows = run_ladder(result["raw_a"], result["raw_b"], result["ref"], profile=None,
                      run_llm=not args.skip_llm, include_dual=not args.skip_dual,
                      model_tier=args.model_tier, provider=args.provider)
    return rows, "fixture-townhall30"
def main():
    parser = argparse.ArgumentParser(description="Alignment-first eval ladder")
    parser.add_argument("--fixture", action="store_true", help="Run on the defect-injection fixture")
    parser.add_argument("--raw-a", help="Path to raw A (_nova2gen) transcript md")
    parser.add_argument("--raw-b", help="Path to raw B (_dgwhspm) transcript md")
    parser.add_argument("--ref", help="Path to reference transcript md")
    parser.add_argument("--profile", default=None, help="Corpus profile for normalization policy (e.g. deutsch)")
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--skip-dual", action="store_true")
    parser.add_argument("--rescore", action="store_true", help="Score existing draft files only; no draft generation or LLM calls")
    parser.add_argument("--model-tier", choices=["cheap", "standard"], default="cheap")
    parser.add_argument("--provider", choices=["openai", "anthropic"], default=None)
    parser.add_argument("--max-segments", type=int, default=30)
    parser.add_argument("--run-suffix", default=None, help="Report filename suffix")
    args = parser.parse_args()
    if args.fixture:
        rows, stem = run_fixture_mode(args)
    elif args.raw_a and args.raw_b and args.ref:
        if args.rescore:
            rows = rescore_ladder(args.raw_a, args.raw_b, args.ref, profile=args.profile)
        else:
            rows = run_ladder(args.raw_a, args.raw_b, args.ref, profile=args.profile,
                              run_llm=not args.skip_llm, include_dual=not args.skip_dual,
                              model_tier=args.model_tier, provider=args.provider)
        stem = os.path.basename(args.ref).rsplit("_", 1)[0]
    else:
        parser.error("Provide --fixture or all of --raw-a/--raw-b/--ref")
    rows, best_raw_label = build_report_rows(rows)
    from core.denovo import load_denovo_pipeline_config, resolve_denovo_model
    denovo_cfg = load_denovo_pipeline_config()
    model_name, resolved_provider = resolve_denovo_model(args.model_tier, denovo_cfg, provider=args.provider)
    run_ts = get_current_datetime_filefriendly()
    run_info = [
        f"Run `{run_ts}` · episode `{stem}`",
        f"Model: **`{model_name}`** · provider `{resolved_provider}` · tier `{args.model_tier}` · prompts `{denovo_cfg.get('prompts_version')}`",
    ]
    report = format_report_md(rows, best_raw_label, f"Alignment ladder — {stem}", run_info)
    print("\n" + report)
    suffix = f"-{args.run_suffix}" if args.run_suffix else ""
    out_dir = os.path.join(_REPO_ROOT, "data", "stellar-eval", "alignment-runs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"alignment-ladder_{stem}{suffix}_{run_ts}.md")
    with open(out_path, "w") as f:
        f.write(report + "\n")
    print(f"\nWrote {out_path}")
    return 0
if __name__ == "__main__":
    sys.exit(main())
