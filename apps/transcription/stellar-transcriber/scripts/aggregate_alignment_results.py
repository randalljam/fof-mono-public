"""
Aggregate per-episode alignment-ladder reports into one results reference doc.

Parses the per-episode markdown tables written by run_alignment_eval.py (matched by
--run-suffix) and emits a combined report with per-episode tables plus corpus totals
(sum of segment errors per variant, overall percent error reduction).

Run from the repo root:
    .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/aggregate_alignment_results.py \
        --run-suffix real5 --out apps/transcription/stellar-transcriber/references/alignment-results-real5.md
"""
import argparse
import glob
import os
import re
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

def parse_report(path):
    """Parse one ladder report; returns (stem, run_info_lines, rows)."""
    with open(path) as f:
        text = f.read()
    stem = None
    m = re.search(r"# Alignment ladder — (.+)", text)
    if m:
        stem = m.group(1).strip()
    run_info = [line for line in text.splitlines() if line.startswith("Run `") or line.startswith("Model:")]
    rows = []
    for line in text.splitlines():
        if not line.startswith("| ") or line.startswith("| Variant") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 11:
            variant, base, errors, strict, missing, spurious, boundary, misplaced, reduction, strict_red, word_acc = cells
        elif len(cells) >= 9:
            variant, base, errors, missing, spurious, boundary, _rate, reduction, word_acc = cells[:9]
            strict, misplaced, strict_red = "0", "0", "—"
        else:
            continue
        if errors == "—":
            continue
        rows.append({
            "variant": variant, "base": base,
            "errors": int(errors), "strict": int(strict), "missing": int(missing),
            "spurious": int(spurious), "boundary": int(boundary), "misplaced": int(misplaced),
            "reduction": reduction, "strict_red": strict_red, "word_acc": word_acc,
        })
    return stem, run_info, rows
def main():
    parser = argparse.ArgumentParser(description="Aggregate alignment ladder reports")
    parser.add_argument("--run-suffix", required=True)
    parser.add_argument("--runs-dir", default="data/stellar-eval/alignment-runs")
    parser.add_argument("--out", required=True)
    parser.add_argument("--title", default=None)
    args = parser.parse_args()
    runs_dir = args.runs_dir if os.path.isabs(args.runs_dir) else os.path.join(_REPO_ROOT, args.runs_dir)
    pattern = os.path.join(runs_dir, f"alignment-ladder_*-{args.run_suffix}_*.md")
    paths = sorted(glob.glob(pattern))
    # Keep only the newest report per episode stem
    by_stem = {}
    for path in paths:
        stem, run_info, rows = parse_report(path)
        if stem and rows:
            by_stem[stem] = (path, run_info, rows)
    if not by_stem:
        print(f"No reports matched {pattern}")
        return 1
    sections = []
    totals = {}
    variant_order = []
    for stem in sorted(by_stem):
        path, run_info, rows = by_stem[stem]
        sections.append(f"### `{stem}`")
        sections.extend(run_info[:1])
        sections.append("| Variant | Errors | Strict | Missing | Spurious | Boundary | Misplaced | Reduction | Strict red. | Word acc |")
        sections.append("|---------|--------|--------|---------|----------|----------|-----------|-----------|-------------|----------|")
        for r in rows:
            sections.append(
                f"| {r['variant']} | {r['errors']} | {r['strict']} | {r['missing']} | {r['spurious']} | "
                f"{r['boundary']} | {r['misplaced']} | {r['reduction']} | {r['strict_red']} | {r['word_acc']} |"
            )
            if r["variant"] not in totals:
                totals[r["variant"]] = {"errors": 0, "strict": 0, "missing": 0, "spurious": 0, "boundary": 0, "misplaced": 0, "episodes": 0}
                variant_order.append(r["variant"])
            t = totals[r["variant"]]
            for k in ("errors", "strict", "missing", "spurious", "boundary", "misplaced"):
                t[k] += r[k]
            t["episodes"] += 1
        sections.append("")
    def base_totals_for(variant):
        if variant.endswith("_A"):
            return totals.get("raw_A_nova2gen")
        if variant.endswith("_B"):
            return totals.get("raw_B_dgwhspm")
        raws = [totals[v] for v in totals if v.startswith("raw_")]
        return min(raws, key=lambda t: t["errors"]) if raws else None
    summary = [
        "## Corpus totals",
        "Sum of segment errors across episodes. Reduction is vs the variant's own base raw totals (singles vs their raw arm, duals vs the better raw).",
        "",
        "| Variant | Episodes | Errors | Strict | Missing | Spurious | Boundary | Misplaced | Reduction | Strict red. |",
        "|---------|----------|--------|--------|---------|----------|----------|-----------|-----------|-------------|",
    ]
    for v in variant_order:
        t = totals[v]
        red = strict_red = "—"
        base = base_totals_for(v) if not v.startswith("raw_") else None
        if base and base["errors"]:
            red = f"{(base['errors'] - t['errors']) / base['errors'] * 100:.1f}%"
        if base and base["strict"]:
            strict_red = f"{(base['strict'] - t['strict']) / base['strict'] * 100:.1f}%"
        summary.append(
            f"| {v} | {t['episodes']} | {t['errors']} | {t['strict']} | {t['missing']} | {t['spurious']} | "
            f"{t['boundary']} | {t['misplaced']} | {red} | {strict_red} |")
    summary.append("")
    title = args.title or f"Alignment ladder results — {args.run_suffix}"
    out_lines = [f"# {title}", ""] + summary + ["", "## Per-episode tables", ""] + sections
    out_path = args.out if os.path.isabs(args.out) else os.path.join(_REPO_ROOT, args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write("\n".join(out_lines).rstrip() + "\n")
    print(f"Wrote {out_path} ({len(by_stem)} episodes)")
    return 0
if __name__ == "__main__":
    sys.exit(main())
