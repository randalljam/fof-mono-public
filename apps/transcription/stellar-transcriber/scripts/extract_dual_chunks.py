"""
Extract word-anchored dual-chunk triples (raw A, raw B, reference) for one episode.

Partitions a dual transcript pair into aligned chunks bounded by dual segment-start
word anchors (see core/denovo.py build_dual_chunks), classifies each chunk as match or
diff, optionally projects the human reference onto the same chunks, and writes the
result as a JSON list of dicts — the prompt-exploration artifact for dual arbitration.

Run from the repo root:
    .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/extract_dual_chunks.py \
        --raw-a "data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_nova2gen.md" \
        --raw-b "data/pv/meetings_epc/f9_raw/2025-03-06_PV-EPC_dgwhspm.md" \
        --ref "data/pv/meetings_epc/2025-03-06_PV-EPC_cemanual.md" \
        --profile pv
"""
import argparse
import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("ELEVENLABS_API_KEY", "unused-for-chunk-extraction")
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

def main():
    parser = argparse.ArgumentParser(description="Extract dual-chunk triples for prompt exploration")
    parser.add_argument("--raw-a", required=True, help="Path to raw A (_nova2gen) transcript md")
    parser.add_argument("--raw-b", required=True, help="Path to raw B (_dgwhspm) transcript md")
    parser.add_argument("--ref", default=None, help="Optional reference transcript md to project onto chunks")
    parser.add_argument("--profile", default=None, help="Corpus profile for normalization policy (e.g. pv)")
    parser.add_argument("--out", default=None, help="Output JSON path (default: data/stellar-eval/dual-chunks/<stem>_dual-chunks.json)")
    parser.add_argument("--min-anchor-words", type=int, default=None)
    parser.add_argument("--edge-words", type=int, default=None)
    args = parser.parse_args()
    from core.denovo import extract_dual_chunk_triples
    out_path, summary = extract_dual_chunk_triples(
        args.raw_a, args.raw_b, ref_path=args.ref, profile=args.profile,
        out_path=args.out, min_anchor_words=args.min_anchor_words, edge_words=args.edge_words,
    )
    diff_share = summary["diff_word_count_a"] / max(summary["total_word_count_a"], 1)
    print(
        f"chunks: {summary['chunk_count']} decisions from {summary['parent_chunk_count']} parents = "
        f"{summary['match_chunk_count']} match + {summary['wording_chunk_count']} wording + "
        f"{summary['diff_chunk_count']} diff"
    )
    print(f"diff share of A words: {diff_share:.0%} ({summary['diff_word_count_a']}/{summary['total_word_count_a']})")
    print(f"Wrote {out_path}")
    return 0
if __name__ == "__main__":
    sys.exit(main())
