"""Worldview Mirror CLI. From the repo root with the venv active:
  python apps/deutsch/worldview-mirror/run_mirror.py serve [--port 8970]
  python apps/deutsch/worldview-mirror/run_mirror.py selftest
  python apps/deutsch/worldview-mirror/run_mirror.py chat "message" [--tone 3] [--lens profile:deep-optimism]"""
import argparse
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wvmirror import config

### Commands
def cmd_serve(args):
    """Run the local server (localhost only; prints the tokenized URL to open)."""
    import uvicorn
    from wvmirror import server
    print("Worldview Mirror -> http://127.0.0.1:%d/  (session token auto-injected into the page)" % args.port)
    uvicorn.run(server.app, host="127.0.0.1", port=args.port, log_level="warning")
def cmd_selftest(args):
    """Validate taxonomy against the graph and report runtime readiness."""
    from wvmirror import atlas, graph_access
    a = atlas.load_atlas()
    g = graph_access.load_graph()
    errors = atlas.validate_atlas(a, g["nodes"])
    print("axes: %d | profiles: %d | graph nodes: %d" % (len(a["axes"]), len(a["profiles"]), len(g["nodes"])))
    print("taxonomy: %s" % ("valid" if not errors else "INVALID"))
    for e in errors:
        print("  -", e)
    print("corpus fetched: %s (verbatim answers %s)" % (graph_access.corpus_available(),
          "available" if graph_access.corpus_available() else "unavailable — run deutsch-graph fetch"))
    from dotenv import load_dotenv
    load_dotenv(override=True)
    print("openai key present: %s" % bool(os.environ.get("OPENAI_API_KEY_LOCAL")))
    return 1 if errors else 0
def cmd_chat(args):
    """One-shot chat turn without the server (throwaway thread; profile IS updated)."""
    from wvmirror import atlas, engine, graph_access, profile_store, threads
    g = graph_access.load_graph()
    a = atlas.load_atlas()
    thread = threads.create_thread(tone=args.tone, lens=args.lens)
    profile = profile_store.load_profile()
    result = engine.answer_turn(g, a, graph_access.citation_index(g), thread, args.message, profile)
    threads.append_message(thread, "user", args.message)
    threads.append_message(thread, "assistant", result["reply"], meta={"citations": result["citations"]})
    for belief in result["observed"]:
        if belief["axis"]:
            profile_store.add_observation(profile, belief["belief"], belief["axis"], belief["position"],
                                          belief["confidence"], quote=belief["quote"], thread=thread["id"])
    profile_store.save_profile(profile, axes=a["axes"])
    print(result["reply"])
    if result["citations"]:
        print("\n--- citations ---")
        for c in result["citations"]:
            print("  %s | %s%s" % (c["id"], c["label"][:70], (" | " + c["url"]) if c.get("url") else ""))
    if result["observed"]:
        print("\n--- observed beliefs (added to your visible profile) ---")
        for b in result["observed"]:
            print("  [%s %+0.1f conf %.1f] %s" % (b["axis"] or "no-axis", b["position"], b["confidence"], b["belief"]))
    return 0

### Entry
def main():
    parser = argparse.ArgumentParser(description="Worldview Mirror")
    sub = parser.add_subparsers(dest="command", required=True)
    p_serve = sub.add_parser("serve", help="run the local web app")
    p_serve.add_argument("--port", type=int, default=8970)
    sub.add_parser("selftest", help="validate taxonomy + runtime readiness")
    p_chat = sub.add_parser("chat", help="one-shot chat turn in the terminal")
    p_chat.add_argument("message")
    p_chat.add_argument("--tone", type=int, default=config.DEFAULT_TONE)
    p_chat.add_argument("--lens", default=config.DEFAULT_LENS)
    args = parser.parse_args()
    return {"serve": cmd_serve, "selftest": cmd_selftest, "chat": cmd_chat}[args.command](args) or 0
if __name__ == "__main__":
    sys.exit(main())
