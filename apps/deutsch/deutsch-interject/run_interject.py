"""Deutsch Interjector CLI. From the repo root with the venv active:
  python apps/deutsch/deutsch-interject/run_interject.py process input.md [--tone 3] [--fidelity quote]
  python apps/deutsch/deutsch-interject/run_interject.py selftest
  python apps/deutsch/deutsch-interject/run_interject.py serve [--port 8971]"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)
sys.path.insert(0, os.path.join(os.path.dirname(APP_DIR), "content-tools"))
from dinterject import config

### Helpers
def _now_string():
    """UTC timestamp for provenance."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
def _print_summary(summary):
    """Small terminal summary table."""
    print("claims found:        %d" % summary["claims"])
    print("diverge:             %d" % summary["diverge"])
    print("agree:               %d" % summary["agree"])
    print("no-position:         %d" % summary["no-position"])
    print("interjections kept:  %d" % summary["interjections"])

### Commands
def cmd_process(args):
    """Process one transcript/article file."""
    from dinterject import engine
    with open(args.input_file, encoding="utf-8") as f:
        text = f.read()
    out_dir = args.out or config.OUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    source_name = args.source_name or os.path.basename(args.input_file)
    result = engine.run(text, source_name, tone=args.tone, fidelity=args.fidelity,
                        include_agreements=args.include_agreements, generated_at=_now_string())
    stem = os.path.splitext(os.path.basename(args.input_file))[0]
    md_path = os.path.join(out_dir, stem + "_interjected.md")
    json_path = os.path.join(out_dir, stem + "_interjected.json")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(result["markdown"])
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result["sidecar"], f, indent=2, sort_keys=True)
    _print_summary(result["summary"])
    print("markdown: %s" % md_path)
    print("json:     %s" % json_path)
    return 0
def cmd_selftest(args):
    """Report graph, harness, fidelity, corpus, and key readiness."""
    from ctools import config as ctools_config
    from dgraph import grounding
    from dgraph import query as dquery
    graph = grounding.load_graph()
    stats = dquery.stats(graph)
    print("graph nodes: %s" % ", ".join("%s=%d" % (k, stats["nodes"][k]) for k in sorted(stats["nodes"])))
    print("corpus fetched: %s" % grounding.corpus_available(repo_root=config.REPO_ROOT))
    print("content-tools interject installed: %s" % ctools_config.tool_available("interject"))
    print("fidelity modes: %s (default %s)" % (", ".join(sorted(config.QUOTE_FIDELITY)), config.DEFAULT_FIDELITY))
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
    print("Deutsch Content Tools -> http://127.0.0.1:%d/interject  (session token auto-injected into pages)" % args.port)
    uvicorn.run(server.app, host="127.0.0.1", port=args.port, log_level="warning")
    return 0

### Entry
def main():
    parser = argparse.ArgumentParser(description="Deutsch Interjector")
    sub = parser.add_subparsers(dest="command", required=True)
    p_process = sub.add_parser("process", help="process one transcript/article file")
    p_process.add_argument("input_file")
    p_process.add_argument("--tone", type=int, default=config.DEFAULT_TONE)
    p_process.add_argument("--fidelity", choices=sorted(config.QUOTE_FIDELITY), default=config.DEFAULT_FIDELITY)
    p_process.add_argument("--include-agreements", action="store_true")
    p_process.add_argument("--source-name")
    p_process.add_argument("--out")
    sub.add_parser("selftest", help="report runtime readiness")
    p_serve = sub.add_parser("serve", help="run the shared local web server")
    p_serve.add_argument("--port", type=int, default=8971)
    args = parser.parse_args()
    return {"process": cmd_process, "selftest": cmd_selftest, "serve": cmd_serve}[args.command](args) or 0
if __name__ == "__main__":
    sys.exit(main())
