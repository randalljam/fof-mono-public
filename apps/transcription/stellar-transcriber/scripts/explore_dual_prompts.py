"""
Explore dual-arbitration prompts against dual-chunk triple files.

Runs the configured (or overridden) dual prompt on diff chunks from a
*_dual-chunks.json triple file (see extract_dual_chunks.py) and scores each
consensus against the reference chunk: word similarity, segment-count delta, and
boundary recall (does the output start segments where the reference does). This is the
fast inner loop for iterating dual prompts without full-episode eval runs.

Run from the repo root:
    .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/explore_dual_prompts.py \
        --chunks "data/stellar-eval/dual-chunks/2025-03-06_PV-EPC_dual-chunks.json" --limit 10
    .venv/bin/python3 ... --chunk-ids 5,12,30
"""
import argparse
import json
import os
import re
import sys
from unittest.mock import MagicMock

os.environ.setdefault("ELEVENLABS_API_KEY", "unused-for-prompt-exploration")
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

def _norm_words(text):
    return [w for w in (re.sub(r"[^a-z0-9']", "", tok.lower()) for tok in (text or "").split()) if w]
def _segments_text(segments):
    return " ".join(seg.get("dialogue") or "" for seg in segments)
def _boundary_keys(segments, n_words=3):
    """Normalized first-words key per segment start (excluding the chunk-initial one)."""
    keys = []
    for seg in segments[1:]:
        words = _norm_words(seg.get("dialogue"))
        if words:
            keys.append(" ".join(words[:n_words]))
    return keys
def score_consensus_vs_ref(consensus, ref_segments):
    """Score one consensus segment list against the reference chunk."""
    from core.transcript_eval import calc_lev_dist_ratio

    ref_text = " ".join(_norm_words(_segments_text(ref_segments)))
    out_text = " ".join(_norm_words(_segments_text(consensus)))
    word_sim = calc_lev_dist_ratio(out_text, ref_text) if (ref_text or out_text) else 1.0
    ref_bounds = _boundary_keys(ref_segments)
    out_bounds = set(_boundary_keys(consensus))
    hits = sum(1 for k in ref_bounds if k in out_bounds)
    return {
        "word_sim_vs_ref": round(word_sim, 4),
        "seg_count_out": len(consensus),
        "seg_count_ref": len(ref_segments),
        "boundary_recall": round(hits / len(ref_bounds), 3) if ref_bounds else None,
        "boundary_precision": round(hits / len(out_bounds), 3) if out_bounds else None,
    }
def main():
    parser = argparse.ArgumentParser(description="Score dual prompts against chunk triples")
    parser.add_argument("--chunks", required=True, help="Path to *_dual-chunks.json (must include ref)")
    parser.add_argument("--limit", type=int, default=10, help="K2 diff chunks to run (default 10)")
    parser.add_argument("--chunk-ids", default=None, help="Comma-separated chunk ids to run instead of --limit")
    parser.add_argument("--prompts-version", default=None, help="Override selector prompt version")
    parser.add_argument("--model-tier", choices=["cheap", "standard"], default="cheap")
    parser.add_argument("--provider", choices=["openai", "anthropic"], default=None)
    args = parser.parse_args()
    from core.denovo import load_denovo_pipeline_config, resolve_denovo_model, resolve_denovo_prompts
    from core.llm import LlmUsageAccumulator, llm_select_dual_chunk_side
    payload = json.load(open(args.chunks))
    chunks = payload["chunks"]
    if not any(c.get("ref") for c in chunks):
        sys.exit("Chunk file has no ref projections — re-extract with --ref")
    config = load_denovo_pipeline_config()
    if args.prompts_version:
        config = {**config, "prompts_version": args.prompts_version}
    _, dual_prompt = resolve_denovo_prompts(config)
    model, provider = resolve_denovo_model(args.model_tier, config, provider=args.provider)
    usage_acc = LlmUsageAccumulator(model)
    base_side = config.get("dual_base_side", "b")
    diff_chunks = [c for c in chunks if c["kind"] == "diff" and c.get("ref")]
    if args.chunk_ids:
        wanted = {int(x) for x in args.chunk_ids.split(",")}
        selected = [c for c in diff_chunks if c["chunk_id"] in wanted]
    else:
        selected = diff_chunks[:args.limit]
    rows = []
    for chunk in selected:
        selected_side = llm_select_dual_chunk_side(
            chunk["a"]["segments"], chunk["b"]["segments"], dual_prompt, model, provider=provider,
            max_retries=config.get("llm_max_retries", 3),
            usage_accumulator=usage_acc,
        )
        ref_segments = chunk["ref"]["segments"]
        base = {
            "chunk_id": chunk["chunk_id"],
            "parent_chunk_id": chunk.get("parent_chunk_id", chunk["chunk_id"]),
            "decision_sub_id": chunk.get("decision_sub_id", 0),
            "similarity_a_b": chunk["similarity"],
        }
        if selected_side is None:
            selected_side = base_side
            status = f"fallback_{base_side}"
        else:
            status = f"selected_{selected_side}"
        selected = chunk[selected_side]["segments"]
        scored = score_consensus_vs_ref(selected, ref_segments)
        a_score = score_consensus_vs_ref(chunk["a"]["segments"], ref_segments)
        b_score = score_consensus_vs_ref(chunk["b"]["segments"], ref_segments)
        best_raw_sim = max(a_score["word_sim_vs_ref"], b_score["word_sim_vs_ref"])
        rows.append({**base, "status": status, "selected_side": selected_side, **scored,
                     "word_sim_best_raw": best_raw_sim,
                     "word_sim_gain": round(scored["word_sim_vs_ref"] - best_raw_sim, 4)})
        r = rows[-1]
        print(f"chunk {r['chunk_id']:>3} {r['status']:<10} word_sim={r['word_sim_vs_ref']:.3f} "
              f"segs {r['seg_count_out']}/{r['seg_count_ref']} "
              f"bound_recall={r['boundary_recall']} gain={r.get('word_sim_gain', '—')}", flush=True)
    ok_rows = [r for r in rows if r["status"].startswith("selected_")]
    summary = {
        "prompts_version": config.get("prompts_version"),
        "model": model,
        "chunks_run": len(rows),
        "fallbacks": sum(1 for r in rows if r["status"].startswith("fallback_")),
        "mean_word_sim_vs_ref": round(sum(r["word_sim_vs_ref"] for r in rows) / len(rows), 4) if rows else None,
        "mean_word_sim_gain": round(sum(r["word_sim_gain"] for r in ok_rows) / len(ok_rows), 4) if ok_rows else None,
        "mean_boundary_recall": round(
            sum(r["boundary_recall"] for r in rows if r["boundary_recall"] is not None)
            / max(sum(1 for r in rows if r["boundary_recall"] is not None), 1), 3),
        **usage_acc.summary(),
    }
    print(json.dumps(summary, indent=2))
    out_dir = os.path.join(_REPO_ROOT, "data", "stellar-eval", "dual-chunks")
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.basename(args.chunks).replace("_dual-chunks.json", "")
    from core.fileops import get_current_datetime_filefriendly
    out_path = os.path.join(out_dir, f"{stem}_prompt-run_{config.get('prompts_version')}_{get_current_datetime_filefriendly()}.json")
    with open(out_path, "w") as f:
        json.dump({"summary": summary, "rows": rows}, f, indent=2)
    print(f"Wrote {out_path}")
    return 0
if __name__ == "__main__":
    sys.exit(main())
