"""
M3B dual-LLM eval runner: build drafts, score vs reference, report subscores and cost.

Run from repo root:
    .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/run_m3b_dual_llm_eval.py --phase selection
    .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/run_m3b_dual_llm_eval.py --phase single
    .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/run_m3b_dual_llm_eval.py --phase five
    .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/run_m3b_dual_llm_eval.py --phase deutsch
    .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/run_m3b_dual_llm_eval.py --phase pv
"""
import argparse
import csv
import json
import os
import shutil
import statistics
import sys
from unittest.mock import MagicMock

CATALOG_REL = os.path.join("apps", "transcription", "stellar-transcriber", "references", "corpus-inventory-catalog.csv")
RAW_FOLDER_DE = "data/deutsch/f9_raw"
REF_FOLDER_DE = "data/deutsch/f8_done_qafixed_and_vrb"
REF_SUFFIX_DE = "_vrb.md"
PROFILE_DE = "deutsch"

BATCH_DEUTSCH_LAST_10 = [
    "2024-08-26_Reason Is Fun - Ep6 Are Feelings Ideas",
    "2024-03-06_Peter Boghossian - Ideological Contagion",
    "2024-03-31_Sagenhaft und Sonderbar der Podcast",
    "2024-03-04_Alex OConnor - The Multiverse is Real",
    "2024-01-04_Reason Is Fun - Ep5 The Art of Decision Making",
    "2024-01-01_Arjun Khemani - Free-Will TCS and Anarcho-Capitalism",
    "2023-12-23_Antisemitism in Britain",
    "2023-12-19_Steven Pinker 1 on Joe Walker - on AGI Doom and Enemies of Civilization",
    "2023-10-16_Sean Carroll Mindscape - On Science Complexity and Explanation",
    "2023-10-15_Deutsch Files 3 with Naval and Brett",
]
M3B_PRIMARY_STEM = "2024-03-06_Peter Boghossian - Ideological Contagion"
M3B_NEXT_FIVE = [
    "2024-08-26_Reason Is Fun - Ep6 Are Feelings Ideas",
    "2024-03-31_Sagenhaft und Sonderbar der Podcast",
    "2024-03-04_Alex OConnor - The Multiverse is Real",
    "2024-01-04_Reason Is Fun - Ep5 The Art of Decision Making",
    "2024-01-01_Arjun Khemani - Free-Will TCS and Anarcho-Capitalism",
]
SCORE_GUIDE_SECTIONS = [
    "## How to read these scores",
    "",
    "All subscores are on a **0–100 scale** (higher is better). **Overall** is a weighted composite for the deutsch profile: word accuracy 35%, speaker 25%, alignment 20%, proper names 12%, quotations 8%.",
    "",
    "**Important:** The **Word acc** column is stored as a **0–1 fraction** in the current harness (e.g. `0.85` means **85%** word accuracy). Mentally multiply by 100 when comparing to other columns.",
    "",
    "### What each column measures",
    "",
    "| Column | Meaning |",
    "|--------|---------|",
    "| **Overall** | Single headline number combining all dimensions below. On these podcast episodes it is **dominated by speaker** (~25 pts from speaker alone when speaker ≈ 99). Do not read overall ≈ 25 as \"25% transcript quality.\" |",
    "| **Alignment** | Do eval segment boundaries line up with the human reference? Low values (often **< 5**) mean timestamp/segmentation structure differs even when words are mostly right. |",
    "| **Speaker** | When segments align, do speaker labels match the reference? **95–100** is typical for good ASR on these episodes — this is the strongest raw baseline dimension. |",
    "| **Word acc** | Verbatim word correctness vs reference (after deutsch normalization). **0.80–0.95** (= 80–95%) is strong ASR; **< 0.50** indicates a broken merge path. |",
    "| **Proper names** | F1 on capitalized names vs reference. Human refs are heavily edited; **2–6** is common for raw ASR — names are a known weak spot. |",
    "| **Quotations** | Recovery of quoted speech. **0** when the episode has no quoted passages in ref; **100** when quotes are present and matched (see Reason Is Fun Ep5). |",
    "",
    "### Star tiers (per dimension, after fixing word-acc scale)",
    "",
    "| Stars | Word acc | Speaker | Alignment | Proper names |",
    "|-------|----------|---------|-----------|--------------|",
    "| ★★★★★ | ≥ 92% | ≥ 98 | ≥ 50 | ≥ 80 |",
    "| ★★★★ | 85–91% | 95–97 | 20–49 | 50–79 |",
    "| ★★★ | 75–84% | 90–94 | 5–19 | 25–49 |",
    "| ★★ | 60–74% | 80–89 | 1–4 | 10–24 |",
    "| ★ | < 60% | < 80 | < 1 | < 10 |",
    "",
    "### Typical raw-ASR profile on these episodes (★ summary)",
    "",
    "- **Speaker ★★★★★** (~99) — diarization is already excellent.",
    "- **Word acc ★★★★** (~85–95%) — verbatim content is good.",
    "- **Alignment ★** (< 5) — segment boundaries rarely match the human ref structure.",
    "- **Proper names ★★** (2–6) — names often wrong vs edited reference.",
    "- **Quotations** — N/A (0) unless the episode contains quoted speech.",
    "",
    "**What `_draftld` (LLM dual merge) should improve:** word accuracy and proper names in disputed islands without hurting speaker. Alignment gains are modest because the metric is mostly about global segmentation, not island text. **`_draftdd` (deterministic dual)** often collapses word acc — ignore for quality; it is a free control arm only.",
    "",
]
SCORE_FIELDS = [
    "overall_score", "subscore_word_accuracy", "subscore_speaker",
    "subscore_alignment", "subscore_proper_names", "subscore_quotations",
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
os.environ.setdefault("ELEVENLABS_API_KEY", "unused-for-m3b-eval")
sys.modules.setdefault("elevenlabs", MagicMock())
sys.modules.setdefault("elevenlabs.client", MagicMock())

from core.denovo import (
    estimate_dual_llm_cost,
    estimate_dual_llm_cost_for_stems,
    merge_dual_deterministic,
    merge_dual_llm,
)
from core.fileops import get_current_datetime_filefriendly
from core.fileops import add_suffix_in_str
from core.transcript_eval import (
    evaluate_transcript,
    get_normalization_policy,
    load_eval_corpus_config,
)
def paths_for_stem(repo_root, stem, raw_folder, ref_folder, ref_suffix):
    raw_a = os.path.join(repo_root, raw_folder, stem + "_nova2gen.md")
    raw_b = os.path.join(repo_root, raw_folder, stem + "_dgwhspm.md")
    ref = os.path.join(repo_root, ref_folder, stem + ref_suffix)
    return raw_a, raw_b, ref
def verify_stem(repo_root, stem, raw_folder, ref_folder, ref_suffix):
    raw_a, raw_b, ref = paths_for_stem(repo_root, stem, raw_folder, ref_folder, ref_suffix)
    missing = [p for p in (raw_a, raw_b, ref) if not os.path.isfile(p)]
    return {
        "stem": stem,
        "ok": len(missing) == 0,
        "raw_nova2gen": raw_a,
        "raw_dgwhspm": raw_b,
        "ref": ref,
        "missing": missing,
    }
def score_transcript(eval_path, ref_path, output_dir, profile_cfg):
    policy = get_normalization_policy(profile_cfg.get("policy_id", "keep-all"))
    weights = profile_cfg.get("weights")
    result = evaluate_transcript(
        eval_path, ref_path, output_dir,
        verbose=False, interactive=False, on_mismatch="continue",
        normalization_policy=policy, corpus_weights=weights,
        policy_id=profile_cfg.get("policy_id"),
        proper_names_method=profile_cfg.get("proper_names_method", "caprules"),
    )
    if result is None:
        return None
    _, metrics = result
    return {k: metrics.get(k) for k in SCORE_FIELDS}
def format_score_row(variant, scores):
    if not scores:
        return f"| {variant} | — | — | — | — | — | — |"
    return (
        f"| {variant} | {scores.get('overall_score', '—')} | "
        f"{scores.get('subscore_alignment', '—')} | {scores.get('subscore_speaker', '—')} | "
        f"{scores.get('subscore_word_accuracy', '—')} | {scores.get('subscore_proper_names', '—')} | "
        f"{scores.get('subscore_quotations', '—')} |"
    )
def run_episode(repo_root, stem, profile, profile_cfg, output_dir, run_llm=True, model_tier="cheap", provider=None, paths=None):
    if paths is None:
        paths = resolve_episode_paths(repo_root, stem, profile)
    if not paths:
        raise FileNotFoundError(f"Could not resolve paths for {profile} stem: {stem}")
    raw_a, raw_b, ref = paths["raw_a"], paths["raw_b"], paths["ref"]
    rows = []
    cost_summary = None
    for variant, path in [
        ("raw_nova2gen", raw_a),
        ("raw_dgwhspm", raw_b),
    ]:
        scores = score_transcript(path, ref, output_dir, profile_cfg)
        rows.append({"stem": stem, "variant": variant, "scores": scores, "cost_usd": 0})
    draft_dd = merge_dual_deterministic(raw_a, raw_b, profile=profile)
    rows.append({
        "stem": stem, "variant": "draftdd",
        "scores": score_transcript(draft_dd, ref, output_dir, profile_cfg),
        "cost_usd": 0,
    })
    if run_llm:
        draft_ld, cost_summary = merge_dual_llm(
            raw_a, raw_b, profile=profile, model_tier=model_tier, provider=provider,
            verbose=True, return_summary=True)
        draft_src = add_suffix_in_str(raw_a, "_draftld")
        draft_archive_dir = os.path.join(output_dir, "drafts")
        os.makedirs(draft_archive_dir, exist_ok=True)
        if os.path.isfile(draft_src):
            shutil.copy2(draft_src, os.path.join(draft_archive_dir, os.path.basename(draft_src)))
        rows.append({
            "stem": stem, "variant": "draftld",
            "scores": score_transcript(draft_ld, ref, output_dir, profile_cfg),
            "cost_usd": cost_summary.get("total_cost_usd", 0),
            "cost_summary": cost_summary,
        })
    return rows, cost_summary
def write_report_md(path, title, sections):
    lines = [
        f"file: {os.path.relpath(path, _REPO_ROOT)}",
        f"title: {title}",
        f"last-updated: {get_current_datetime_filefriendly()}",
        "ai: Cursor - Composer 2.5 Fast",
        "session: `Stellar Transcriber M3B — dual-LLM merge scoring`",
        "",
        f"# {title}",
        "",
    ]
    lines.extend(sections)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Wrote {path}")
def phase_selection(repo_root):
    verified = []
    for stem in BATCH_DEUTSCH_LAST_10:
        verified.append(verify_stem(repo_root, stem, RAW_FOLDER_DE, REF_FOLDER_DE, REF_SUFFIX_DE))
    ok_count = sum(1 for v in verified if v["ok"])
    sections = [
        "## STOP 1 — proposed episode selection",
        "",
        f"**Primary episode (single-file run):** `{M3B_PRIMARY_STEM}`",
        "",
        "Historical dev-eval reference: Peter Boghossian (`mrun_evaluate_transcript_dev`, `BATCH_DEUTSCH_LAST_10`).",
        "",
        "**Next five (batch run after STOP 2):**",
    ]
    for stem in M3B_NEXT_FIVE:
        sections.append(f"- `{stem}`")
    sections.extend([
        "",
        f"## Deutsch10 verification ({ok_count}/{len(BATCH_DEUTSCH_LAST_10)} complete triples)",
        "",
        "| Stem | nova2gen | dgwhspm | vrb |",
        "|------|----------|---------|-----|",
    ])
    for v in verified:
        mark = lambda p: "yes" if os.path.isfile(p) else "**missing**"
        sections.append(
            f"| `{v['stem']}` | {mark(v['raw_nova2gen'])} | {mark(v['raw_dgwhspm'])} | {mark(v['ref'])} |"
        )
    est_primary = estimate_dual_llm_cost(
        os.path.join(repo_root, RAW_FOLDER_DE, M3B_PRIMARY_STEM + "_nova2gen.md"),
        os.path.join(repo_root, RAW_FOLDER_DE, M3B_PRIMARY_STEM + "_dgwhspm.md"),
        profile=PROFILE_DE,
    )
    est_five = estimate_dual_llm_cost_for_stems(
        M3B_NEXT_FIVE, os.path.join(repo_root, RAW_FOLDER_DE), profile=PROFILE_DE)
    sections.extend([
        "",
        "## Pre-run cost estimates (dual-LLM, cheap tier)",
        "",
        f"- Primary episode: ~${est_primary['total_cost_usd']:.4f} "
        f"({est_primary['diff_chunk_count']} diff chunks, {est_primary['input_tokens']:,} est. input tokens)",
        f"- Next five total: ~${est_five['total_cost_usd']:.4f}",
        "",
        "**Awaiting Randy approval before LLM runs.**",
    ])
    out = os.path.join(repo_root, "apps/transcription/stellar-transcriber/references/m3b-episode-selection.md")
    write_report_md(out, "Stellar Transcriber M3B — episode selection (STOP 1)", sections)
    return verified
def phase_run_stems(repo_root, stems, phase_name, profile, run_llm=True, model_tier="cheap", provider=None, run_suffix=None):
    from core.denovo import load_denovo_pipeline_config, resolve_denovo_model

    config = load_eval_corpus_config(repo_root=repo_root)
    profile_cfg = config.get(profile, {})
    denovo_cfg = load_denovo_pipeline_config()
    model_name, resolved_provider = resolve_denovo_model(model_tier, denovo_cfg, provider=provider)
    run_ts = get_current_datetime_filefriendly()
    suffix_part = run_suffix or phase_name
    output_dir = os.path.join(repo_root, "data/stellar-eval", profile, f"m3b-{suffix_part}-{run_ts}")
    os.makedirs(output_dir, exist_ok=True)
    all_rows = []
    total_cost = 0.0
    total_in = 0
    total_out = 0
    total_islands = 0
    for stem in stems:
        print(f"\n=== {phase_name}: {stem} ({model_name}) ===", flush=True)
        paths = resolve_episode_paths(repo_root, stem, profile)
        if not paths:
            print(f"SKIP missing paths for {stem}", flush=True)
            continue
        rows, cost = run_episode(
            repo_root, stem, profile, profile_cfg, output_dir,
            run_llm=run_llm, model_tier=model_tier, provider=provider, paths=paths,
        )
        all_rows.extend(rows)
        if cost:
            total_cost += cost.get("total_cost_usd", 0)
            total_in += cost.get("input_tokens", 0)
            total_out += cost.get("output_tokens", 0)
            total_islands += cost.get("diff_chunk_count", cost.get("island_count", 0))
    sections = [
        f"Phase: **{phase_name}** · run `{run_ts}` · profile `{profile}`",
        f"Model: **`{model_name}`** · provider `{resolved_provider}` · tier `{model_tier or 'default'}`",
        "",
    ]
    if phase_name == "five":
        sections.extend(SCORE_GUIDE_SECTIONS)
    sections.extend([
        "## Per-episode subscores (0–100)",
        "",
        "Variants: raw `_nova2gen`, raw `_dgwhspm`, `_draftdd` (deterministic dual), `_draftld` (LLM dual).",
        "",
    ])
    for stem in stems:
        sections.append(f"### `{stem}`")
        sections.append("")
        sections.append("| Variant | Overall | Alignment | Speaker | Word acc | Proper names | Quotations |")
        sections.append("|---------|---------|-----------|---------|----------|--------------|------------|")
        for row in all_rows:
            if row["stem"] != stem:
                continue
            sections.append(format_score_row(row["variant"], row["scores"]))
        sections.append("")
    if run_llm:
        sections.extend([
            f"## LLM cost (actual): ${total_cost:.4f} total for {len(stems)} episode(s)",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Model | `{model_name}` |",
            f"| Provider | `{resolved_provider}` |",
            f"| Islands | {total_islands} |",
            f"| Input tokens | {total_in:,} |",
            f"| Output tokens | {total_out:,} |",
            "",
        ])
    if phase_name == "single":
        est_five = estimate_dual_llm_cost_for_stems(
            M3B_NEXT_FIVE, os.path.join(repo_root, RAW_FOLDER_DE), profile=profile)
        catalog_stems = load_deutsch_vrb_stems(repo_root)
        est_corpus_full = estimate_dual_llm_cost_for_stems(
            catalog_stems, os.path.join(repo_root, RAW_FOLDER_DE), profile=profile)
        sections.extend([
            "## STOP 2 — cost estimates for scale-up",
            "",
            f"- Next five episodes: ~${est_five['total_cost_usd']:.2f} "
            f"({est_five['diff_chunk_count']} diff chunks, {est_five['input_tokens']:,} est. input tokens)",
            f"- Full deutsch vrb corpus ({est_corpus_full['episode_count']} pairs): ~${est_corpus_full['total_cost_usd']:.2f}",
            "",
            "**Awaiting Randy go-ahead before 5-file batch.**",
        ])
    out_name = f"m3b-results-{phase_name}" if not run_suffix else f"m3b-results-{phase_name}-{run_suffix}"
    out = os.path.join(repo_root, "apps/transcription/stellar-transcriber/references", f"{out_name}.md")
    title_suffix = f" — {run_suffix}" if run_suffix else ""
    write_report_md(out, f"Stellar Transcriber M3B — {phase_name} results{title_suffix}", sections)
    return all_rows, total_cost
def load_catalog_rows(corpus=None, has_pair_only=True):
    catalog = os.path.join(_REPO_ROOT, CATALOG_REL)
    rows = []
    with open(catalog, newline="") as f:
        for row in csv.DictReader(f):
            if has_pair_only and row.get("has_pair") != "yes":
                continue
            if corpus and row.get("corpus") != corpus:
                continue
            rows.append(row)
    return rows
def suffix_from_filename(filename):
    base, ext = os.path.splitext(filename)
    if ext != ".md":
        return None
    idx = base.rfind("_")
    if idx == -1:
        return None
    return base[idx:] + ext
def resolve_episode_paths(repo_root, stem, corpus):
    """Resolve nova2gen, dgwhspm, and best reference paths from catalog + local files."""
    from core.fileops import get_heading

    config = load_eval_corpus_config(repo_root=repo_root)
    profile = config.get(corpus, {})
    ref_priority = profile.get("ref_suffix_priority", ["_vrb.md"])
    eval_suffixes = profile.get("eval_suffixes", ["_nova2gen.md", "_dgwhspm.md"])
    for row in load_catalog_rows(corpus=corpus):
        if row.get("stem") != stem:
            continue
        s3_keys = [k.strip() for k in row.get("s3_keys", "").split(";") if k.strip()]
        keys_by_suffix = {}
        for key in s3_keys:
            suffix = suffix_from_filename(os.path.basename(key))
            if suffix:
                keys_by_suffix[suffix] = key
        raw_a = keys_by_suffix.get("_nova2gen.md")
        raw_b = keys_by_suffix.get("_dgwhspm.md")
        ref_key = None
        for suffix in ref_priority:
            if suffix in keys_by_suffix:
                candidate = os.path.join(repo_root, keys_by_suffix[suffix])
                if os.path.isfile(candidate) and get_heading(candidate, "### transcript"):
                    ref_key = keys_by_suffix[suffix]
                    break
        if not raw_a or not raw_b or not ref_key:
            return None
        raw_a_path = os.path.join(repo_root, raw_a)
        raw_b_path = os.path.join(repo_root, raw_b)
        if not all(
            os.path.isfile(p) and get_heading(p, "### transcript")
            for p in (raw_a_path, raw_b_path)
        ):
            return None
        return {
            "raw_a": raw_a_path,
            "raw_b": raw_b_path,
            "ref": os.path.join(repo_root, ref_key),
        }
    return None
def load_deutsch_vrb_stems(repo_root):
    stems = []
    for row in load_catalog_rows(corpus="deutsch"):
        ref_sufs = row.get("ref_suffixes", "")
        raw_sufs = row.get("raw_suffixes", "")
        if "_vrb" not in ref_sufs:
            continue
        if "_nova2gen" not in raw_sufs or "_dgwhspm" not in raw_sufs:
            continue
        if resolve_episode_paths(repo_root, row.get("stem"), "deutsch"):
            stems.append(row.get("stem"))
    return sorted(stems)
def load_pv_stems(repo_root):
    stems = []
    for row in load_catalog_rows(corpus="pv"):
        if resolve_episode_paths(repo_root, row.get("stem"), "pv"):
            stems.append(row.get("stem"))
    return sorted(stems)
def main():
    parser = argparse.ArgumentParser(description="M3B dual-LLM eval runner")
    parser.add_argument(
        "--phase",
        choices=["selection", "single", "five", "deutsch", "pv"],
        required=True,
    )
    parser.add_argument("--skip-llm", action="store_true", help="Score baselines and draftdd only")
    parser.add_argument("--model-tier", choices=["cheap", "standard"], default="cheap")
    parser.add_argument("--provider", choices=["openai", "anthropic"], default=None)
    parser.add_argument(
        "--run-suffix", default=None,
        help="Output filename suffix (e.g. gpt54 → m3b-results-five-gpt54.md)",
    )
    args = parser.parse_args()
    repo_root = _REPO_ROOT
    run_kw = {
        "run_llm": not args.skip_llm,
        "model_tier": args.model_tier,
        "provider": args.provider,
        "run_suffix": args.run_suffix,
    }
    if args.phase == "selection":
        phase_selection(repo_root)
        return 0
    if args.phase == "single":
        phase_run_stems(repo_root, [M3B_PRIMARY_STEM], "single", PROFILE_DE, **run_kw)
        return 0
    if args.phase == "five":
        phase_run_stems(repo_root, M3B_NEXT_FIVE, "five", PROFILE_DE, **run_kw)
        return 0
    if args.phase == "deutsch":
        stems = load_deutsch_vrb_stems(repo_root)
        phase_run_stems(repo_root, stems, "deutsch", PROFILE_DE, **run_kw)
        return 0
    if args.phase == "pv":
        stems = load_pv_stems(repo_root)
        phase_run_stems(repo_root, stems, "pv", "pv", **run_kw)
        return 0
    return 1

if __name__ == "__main__":
    sys.exit(main())
