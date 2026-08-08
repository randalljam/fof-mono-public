"""Content Redo CLI. From the repo root with the venv active:
  python apps/deutsch/content-redo/run_redo.py process input.md [--tone 3] [--degree 2] [--reading-level adult]
  python apps/deutsch/content-redo/run_redo.py selftest
  python apps/deutsch/content-redo/run_redo.py serve [--port 8971]"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)
sys.path.insert(0, os.path.join(os.path.dirname(APP_DIR), "content-tools"))
from dredo import config

### Helpers
def _now_string():
    """UTC timestamp for provenance."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
def _print_summary(summary):
    """Small terminal summary table."""
    print("claims found:      %d" % summary["claims"])
    print("diverge:           %d" % summary["diverge"])
    print("agree:             %d" % summary["agree"])
    print("no-position:       %d" % summary["no-position"])
    print("plan kept:         %d" % summary["planned"])
    print("plan dropped:      %d" % summary["dropped_plan"])
    print("changes applied:   %d" % summary["changes"])
    print("skipped notes:     %d" % summary["skipped"])

### Commands
def cmd_process(args):
    """Process one article/transcript file."""
    from dredo import engine
    with open(args.input_file, encoding="utf-8") as f:
        text = f.read()
    out_dir = args.out or config.OUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    source_name = args.source_name or os.path.basename(args.input_file)
    result = engine.run(text, source_name, tone=args.tone, degree=args.degree,
                        reading_level=args.reading_level, generated_at=_now_string())
    stem = os.path.splitext(os.path.basename(args.input_file))[0]
    md_path = os.path.join(out_dir, stem + "_redo.md")
    changes_path = os.path.join(out_dir, stem + "_redo_changes.md")
    json_path = os.path.join(out_dir, stem + "_redo.json")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(result["markdown"])
    with open(changes_path, "w", encoding="utf-8") as f:
        f.write(result["change_list_markdown"])
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result["sidecar"], f, indent=2, sort_keys=True)
    _print_summary(result["summary"])
    print("markdown:    %s" % md_path)
    print("change list: %s" % changes_path)
    print("json:        %s" % json_path)
    return 0
def cmd_selftest(args):
    """Report graph, harness, remix, corpus, and key readiness."""
    from ctools import config as ctools_config
    from dgraph import grounding
    from dgraph import query as dquery
    graph = grounding.load_graph()
    stats = dquery.stats(graph)
    print("graph nodes: %s" % ", ".join("%s=%d" % (k, stats["nodes"][k]) for k in sorted(stats["nodes"])))
    print("corpus fetched: %s" % grounding.corpus_available(repo_root=config.REPO_ROOT))
    print("content-tools redo installed: %s" % ctools_config.tool_available("redo"))
    print("degrees: %s (default %s)" % (", ".join("%s=%s" % (k, config.REMIX_DEGREES[k]["label"]) for k in sorted(config.REMIX_DEGREES)), config.DEFAULT_DEGREE))
    print("reading levels: %s (default %s)" % (", ".join(sorted(config.READING_LEVELS)), config.DEFAULT_READING_LEVEL))
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except Exception:
        pass
    print("openai key present: %s" % bool(os.environ.get("OPENAI_API_KEY_LOCAL") or os.environ.get("OPENAI_API_KEY")))
    return 0
def cmd_serve(args):
    """Delegate to the shared content-tools server."""
    import uvicorn
    from ctools import server
    print("Deutsch Content Tools -> http://127.0.0.1:%d/redo  (session token auto-injected into pages)" % args.port)
    uvicorn.run(server.app, host="127.0.0.1", port=args.port, log_level="warning")
    return 0

### Entry
def main():
    parser = argparse.ArgumentParser(description="Content Redo")
    sub = parser.add_subparsers(dest="command", required=True)
    p_process = sub.add_parser("process", help="process one article/transcript file")
    p_process.add_argument("input_file")
    p_process.add_argument("--tone", type=int, default=config.DEFAULT_TONE)
    p_process.add_argument("--degree", type=int, choices=sorted(config.REMIX_DEGREES), default=config.DEFAULT_DEGREE)
    p_process.add_argument("--reading-level", choices=sorted(config.READING_LEVELS), default=config.DEFAULT_READING_LEVEL)
    p_process.add_argument("--source-name")
    p_process.add_argument("--out")
    sub.add_parser("selftest", help="report runtime readiness")
    p_serve = sub.add_parser("serve", help="run the shared local web server")
    p_serve.add_argument("--port", type=int, default=8971)
    args = parser.parse_args()
    return {"process": cmd_process, "selftest": cmd_selftest, "serve": cmd_serve}[args.command](args) or 0
if __name__ == "__main__":
    sys.exit(main())
