"""deutsch-graph CLI: fetch corpus inputs, build the graph, validate, inspect, export.

Usage (from repo root, with .venv active):
  python apps/deutsch/deutsch-graph/build_graph.py fetch        # download inputs from S3
  python apps/deutsch/deutsch-graph/build_graph.py build        # full deterministic build -> graph/
  python apps/deutsch/deutsch-graph/build_graph.py validate     # integrity checks
  python apps/deutsch/deutsch-graph/build_graph.py stats        # load + print counts
  python apps/deutsch/deutsch-graph/build_graph.py export-vis   # vis-network JSON + web viewer
  python apps/deutsch/deutsch-graph/build_graph.py topic "AGI"  # top QA items for a topic
"""
import argparse
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgraph import build, export_vis, fetch, ids, query, validate

def cmd_fetch(args):
    """Download build inputs from S3 per the manifest."""
    fetch.fetch_corpus(build.repo_root())
def cmd_build(args):
    """Run the full build and write graph/."""
    result = build.build_graph()
    counts = build.write_graph(result)
    print("built:", counts)
    errors = validate.validate_graph(build.graph_dir())
    if errors:
        print("VALIDATION FAILED (%d errors):" % len(errors))
        for e in errors[:50]:
            print("  -", e)
        sys.exit(1)
    print("validation: OK")
def cmd_validate(args):
    """Validate the committed graph."""
    manifest_paths = None
    manifest_file = os.path.join(build.repo_root(), "manifests", "deutsch.manifest.jsonl")
    if os.path.exists(manifest_file):
        import json
        with open(manifest_file) as f:
            manifest_paths = {json.loads(line)["repo_path"] for line in f if line.strip()}
    errors = validate.validate_graph(build.graph_dir(), manifest_paths)
    if errors:
        print("INVALID (%d errors):" % len(errors))
        for e in errors[:100]:
            print("  -", e)
        sys.exit(1)
    print("valid")
def cmd_stats(args):
    """Print node/edge counts."""
    graph = query.load_graph(build.graph_dir())
    s = query.stats(graph)
    print("nodes:", s["nodes"])
    print("edges:", s["edges"])
def cmd_export_vis(args):
    """Write exports/graph_vis.json (aggregate) and web/graphdata/ shards for the viewer.
    web/deutsch-graph-viewer.html is hand-authored source and is NOT regenerated."""
    out_json = os.path.join(build.graph_dir(), "exports", "graph_vis.json")
    scratch_html = os.path.join(build.graph_dir(), "exports", "graph_vis_preview.html")
    counts = export_vis.export(build.graph_dir(), out_json, scratch_html,
                               min_edge_weight=args.min_weight, min_topic_qa=args.min_topic_qa)
    os.remove(scratch_html)
    shards = export_vis.export_viewer_data(build.graph_dir(), os.path.join(build.app_root(), "web", "graphdata"))
    print("exported:", counts, "+ %d viewer data shards -> web/graphdata/" % len(shards))
def cmd_topic(args):
    """Show top QA items for a topic label."""
    graph = query.load_graph(build.graph_dir())
    tid = ids.topic_id(args.label)
    if tid not in graph["nodes"]:
        print("unknown topic:", tid)
        sys.exit(1)
    for q in query.top_qa_for_topic(graph, tid, args.limit):
        star = "*" if q["starred"] else " "
        print("%s [%s] %s" % (star, q["work"], q["question"]))
        if q["youtube_ts_url"]:
            print("     ", q["youtube_ts_url"])
def main():
    """Dispatch subcommands."""
    parser = argparse.ArgumentParser(description="Deutsch Graph build tools")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("fetch")
    sub.add_parser("build")
    sub.add_parser("validate")
    sub.add_parser("stats")
    p_vis = sub.add_parser("export-vis")
    p_vis.add_argument("--min-weight", type=int, default=1)
    p_vis.add_argument("--min-topic-qa", type=int, default=2)
    p_topic = sub.add_parser("topic")
    p_topic.add_argument("label")
    p_topic.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    {"fetch": cmd_fetch, "build": cmd_build, "validate": cmd_validate, "stats": cmd_stats,
     "export-vis": cmd_export_vis, "topic": cmd_topic}[args.command](args)
if __name__ == "__main__":
    main()
