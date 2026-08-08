"""Deutsch content-tools CLI. From this directory or the repo root:
  python apps/deutsch/content-tools/run_tools.py serve [--port 8971]
  python apps/deutsch/content-tools/run_tools.py selftest"""
import argparse
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ctools import config

### Commands
def cmd_serve(args):
    """Run the shared local server on 127.0.0.1."""
    import uvicorn
    from ctools import server
    print("Deutsch Content Tools -> http://127.0.0.1:%d/  (session token auto-injected into pages)" % args.port)
    uvicorn.run(server.app, host="127.0.0.1", port=args.port, log_level="warning")
def cmd_selftest(args):
    """Report graph, corpus, tool, and key readiness."""
    from dgraph import grounding
    from dgraph import query as dquery
    graph = grounding.load_graph()
    stats = dquery.stats(graph)
    print("graph nodes: %s" % ", ".join("%s=%d" % (k, stats["nodes"][k]) for k in sorted(stats["nodes"])))
    print("corpus fetched: %s" % grounding.corpus_available(repo_root=config.REPO_ROOT))
    for row in config.tool_rows():
        print("tool %-10s %s (%s)" % (row["key"] + ":", "installed" if row["installed"] else "missing", row["module"]))
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except Exception:
        pass
    print("openai key present: %s" % bool(os.environ.get("OPENAI_API_KEY_LOCAL") or os.environ.get("OPENAI_API_KEY")))
    return 0

### Entry
def main():
    parser = argparse.ArgumentParser(description="Deutsch content-tools harness")
    sub = parser.add_subparsers(dest="command", required=True)
    p_serve = sub.add_parser("serve", help="run the shared local web server")
    p_serve.add_argument("--port", type=int, default=8971)
    sub.add_parser("selftest", help="report graph/tool/API-key readiness")
    args = parser.parse_args()
    return {"serve": cmd_serve, "selftest": cmd_selftest}[args.command](args) or 0
if __name__ == "__main__":
    sys.exit(main())
