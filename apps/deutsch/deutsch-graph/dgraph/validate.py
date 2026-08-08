"""Referential-integrity validation per docs/graph-spec.md §Validation rules."""
import json
import os
from . import query

def validate_graph(graph_path, manifest_paths=None):
    """Run all checks; returns list of error strings (empty = valid)."""
    errors = []
    graph = query.load_graph(graph_path)
    nodes = graph["nodes"]
    ### 1. Edge endpoints resolve
    for e in graph["edges"]:
        for end in ("src", "dst"):
            if e[end] not in nodes:
                errors.append("edge %s %s->%s: unresolved %s" % (e["type"], e["src"], e["dst"], end))
    ### 2. qa fields resolve; answer pointers exist in manifest (when provided)
    for nid in graph["by_type"].get("qa", []):
        q = nodes[nid]
        if q["work"] not in nodes:
            errors.append("qa %s: unresolved work %s" % (nid, q["work"]))
        for tid in q["topics"]:
            if tid not in nodes:
                errors.append("qa %s: unresolved topic %s" % (nid, tid))
        if manifest_paths is not None and q["answer_pointer"]["path"] not in manifest_paths:
            errors.append("qa %s: answer pointer not in manifest: %s" % (nid, q["answer_pointer"]["path"]))
    ### 3. ID uniqueness is guaranteed by dict load; re-check across files on disk
    seen = {}
    for sub in ("sources", "topics", "concepts", "chapters", "categories", "claims"):
        for node in query.read_jsonl(os.path.join(graph_path, "nodes", sub + ".jsonl")):
            if node["id"] in seen:
                errors.append("duplicate id %s (in %s and %s)" % (node["id"], seen[node["id"]], sub))
            seen[node["id"]] = sub
    for shard in ("qa", "excerpts"):
        shard_dir = os.path.join(graph_path, "nodes", shard)
        if os.path.isdir(shard_dir):
            for fname in sorted(os.listdir(shard_dir)):
                for node in query.read_jsonl(os.path.join(shard_dir, fname)):
                    if node["id"] in seen:
                        errors.append("duplicate id %s (in %s and %s)" % (node["id"], seen[node["id"]], fname))
                    seen[node["id"]] = fname
    ### 4. formats paths unique across works
    claimed = {}
    for nid in graph["by_type"].get("work", []):
        for path in nodes[nid]["formats"].values():
            if path in claimed:
                errors.append("file claimed twice: %s (%s and %s)" % (path, claimed[path], nid))
            claimed[path] = nid
    ### 6. counts match build-manifest.json
    manifest_file = os.path.join(graph_path, "build-manifest.json")
    if os.path.exists(manifest_file):
        with open(manifest_file) as f:
            manifest = json.load(f)
        live = query.stats(graph)
        file_to_type = {"sources": "work", "topics": "topic", "concepts": "concept", "chapters": "chapter",
                        "qa": "qa", "categories": "category", "claims": "claim", "excerpts": "excerpt"}
        for name, count in manifest["counts"]["nodes"].items():
            live_count = live["nodes"].get(file_to_type.get(name, name), 0)
            if live_count != count:
                errors.append("manifest count mismatch for %s: manifest=%d live=%d" % (name, count, live_count))
    else:
        errors.append("missing build-manifest.json")
    return errors
