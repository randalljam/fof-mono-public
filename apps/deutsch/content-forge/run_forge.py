"""Deutsch Content Forge CLI. From the repo root with the venv active:
  python apps/deutsch/content-forge/run_forge.py create "essay about optimism" --format essay --length medium --tone 3
  python apps/deutsch/content-forge/run_forge.py selftest
  python apps/deutsch/content-forge/run_forge.py serve [--port 8971]"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)
sys.path.insert(0, os.path.join(os.path.dirname(APP_DIR), "content-tools"))
from dforge import config

### Helpers
def _now_string():
    """UTC timestamp for provenance."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
def _slug(text):
    """Short filesystem-safe slug."""
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return (text or "content-forge")[:48].strip("-") or "content-forge"
def _print_summary(coverage):
    """Small terminal summary table."""
    print("sections:             %d" % coverage["n_sections"])
    print("grounded sections:    %d" % coverage["n_grounded"])
    print("ungrounded sections:  %d" % coverage["n_ungrounded"])
    print("citations:            %d" % coverage["n_citations"])
    print("invalid stripped:     %d" % coverage["n_invalid"])

### Commands
def cmd_create(args):
    """Create one graph-conditioned piece from a description."""
    from dforge import engine
    out_dir = args.out or config.OUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    result = engine.run(args.description, fmt=args.fmt, length=args.length, tone=args.tone, generated_at=_now_string())
    stem = _slug(args.description)
    md_path = os.path.join(out_dir, stem + "_forge.md")
    sidecar_md_path = os.path.join(out_dir, stem + "_citations.md")
    json_path = os.path.join(out_dir, stem + "_citations.json")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(result["markdown"])
    with open(sidecar_md_path, "w", encoding="utf-8") as f:
        f.write(result["sidecar_markdown"])
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result["sidecar"], f, indent=2, sort_keys=True)
    _print_summary(result["coverage"])
    print("markdown:        %s" % md_path)
    print("sidecar md:      %s" % sidecar_md_path)
    print("sidecar json:    %s" % json_path)
    return 0
def cmd_selftest(args):
    """Report graph, harness, format, corpus, and key readiness."""
    from ctools import config as ctools_config
    from dgraph import grounding
    from dgraph import query as dquery
    graph = grounding.load_graph()
    stats = dquery.stats(graph)
    print("graph nodes: %s" % ", ".join("%s=%d" % (k, stats["nodes"][k]) for k in sorted(stats["nodes"])))
    print("corpus fetched: %s" % grounding.corpus_available(repo_root=config.REPO_ROOT))
    print("content-tools forge installed: %s" % ctools_config.tool_available("forge"))
    print("formats: %s (default %s)" % (", ".join(sorted(config.FORMATS)), config.DEFAULT_FORMAT))
    print("lengths: %s (default %s)" % (", ".join(sorted(config.LENGTHS)), config.DEFAULT_LENGTH))
    print("tones: %s (default %s)" % (", ".join(str(k) for k in sorted(ctools_config.TONES)), ctools_config.DEFAULT_TONE))
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
    print("Deutsch Content Tools -> http://127.0.0.1:%d/forge  (session token auto-injected into pages)" % args.port)
    uvicorn.run(server.app, host="127.0.0.1", port=args.port, log_level="warning")
    return 0

### Entry
def main():
    parser = argparse.ArgumentParser(description="Deutsch Content Forge")
    sub = parser.add_subparsers(dest="command", required=True)
    p_create = sub.add_parser("create", help="create a new text piece from a description")
    p_create.add_argument("description")
    p_create.add_argument("--format", dest="fmt", choices=sorted(config.FORMATS), default=config.DEFAULT_FORMAT)
    p_create.add_argument("--length", choices=sorted(config.LENGTHS), default=config.DEFAULT_LENGTH)
    p_create.add_argument("--tone", type=int, default=config.DEFAULT_TONE)
    p_create.add_argument("--out")
    sub.add_parser("selftest", help="report runtime readiness")
    p_serve = sub.add_parser("serve", help="run the shared local web server")
    p_serve.add_argument("--port", type=int, default=8971)
    args = parser.parse_args()
    return {"create": cmd_create, "selftest": cmd_selftest, "serve": cmd_serve}[args.command](args) or 0
if __name__ == "__main__":
    sys.exit(main())
