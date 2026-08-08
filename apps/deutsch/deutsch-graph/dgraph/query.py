"""Load and traverse the built graph. Derived edges (qa->work, qa->topic) are
materialized here at load time; they are never stored (docs/graph-spec.md)."""
import json
import os

### Loading
def read_jsonl(path):
    """Read one JSONL file -> list of dicts ([] when absent)."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
def load_graph(graph_path):
    """Load the whole graph dir -> {'nodes': {id: node}, 'edges': [edge], 'by_type': {type: [id]}}."""
    nodes = {}
    by_type = {}
    for name in ("sources", "topics", "concepts", "chapters", "categories", "claims"):
        for node in read_jsonl(os.path.join(graph_path, "nodes", name + ".jsonl")):
            nodes[node["id"]] = node
            by_type.setdefault(node["type"], []).append(node["id"])
    for sub in ("qa", "excerpts"):
        sub_dir = os.path.join(graph_path, "nodes", sub)
        if os.path.isdir(sub_dir):
            for fname in sorted(os.listdir(sub_dir)):
                for node in read_jsonl(os.path.join(sub_dir, fname)):
                    nodes[node["id"]] = node
                    by_type.setdefault(node["type"], []).append(node["id"])
    edges = []
    edges_dir = os.path.join(graph_path, "edges")
    if os.path.isdir(edges_dir):
        for fname in sorted(os.listdir(edges_dir)):
            edges.extend(read_jsonl(os.path.join(edges_dir, fname)))
    for nid in by_type.get("qa", []):
        q = nodes[nid]
        edges.append({"src": nid, "dst": q["work"], "type": "qa_of"})
        for tid in q["topics"]:
            edges.append({"src": nid, "dst": tid, "type": "qa_topic"})
    for nid in by_type.get("claim", []):
        edges.append({"src": nid, "dst": nodes[nid]["category"], "type": "claim_of"})
    for nid in by_type.get("excerpt", []):
        e = nodes[nid]
        edges.append({"src": nid, "dst": e["claim"], "type": "excerpt_of"})
        if e.get("source_work"):
            edges.append({"src": nid, "dst": e["source_work"], "type": "excerpt_source"})
        if e.get("source_chapter"):
            edges.append({"src": nid, "dst": e["source_chapter"], "type": "excerpt_source_chapter"})
    return {"nodes": nodes, "edges": edges, "by_type": by_type}
def build_adjacency(graph):
    """id -> list of (neighbor_id, edge_type, direction) for both directions."""
    adj = {}
    for e in graph["edges"]:
        adj.setdefault(e["src"], []).append((e["dst"], e["type"], "out"))
        adj.setdefault(e["dst"], []).append((e["src"], e["type"], "in"))
    return adj

### Queries
def neighbors(graph, node_id, edge_type=None, adj=None):
    """Neighbor ids of a node, optionally filtered by edge type."""
    adj = adj or build_adjacency(graph)
    out = []
    for nid, etype, _ in adj.get(node_id, []):
        if edge_type is None or etype == edge_type:
            out.append(nid)
    return out
def top_qa_for_topic(graph, topic_node_id, limit=10):
    """Best QA items for a topic: starred first, then stars, then longer answers."""
    hits = [graph["nodes"][nid] for nid in graph["by_type"].get("qa", [])
            if topic_node_id in graph["nodes"][nid]["topics"]]
    hits.sort(key=lambda q: (not q["starred"], -q["stars"], -q["answer_chars"]))
    return hits[:limit]
def search_questions(graph, needle, limit=20):
    """Case-insensitive substring search over QA questions (incl. alternates)."""
    needle = needle.lower()
    out = []
    for nid in graph["by_type"].get("qa", []):
        q = graph["nodes"][nid]
        haystack = " | ".join([q["question"]] + q["questions_alt"]).lower()
        if needle in haystack:
            out.append(q)
            if len(out) >= limit:
                break
    return out
def topic_cooccurrence(graph, min_weight=2):
    """Topic-topic co-occurrence (same QA block) -> {(tid_a, tid_b): weight}, a < b."""
    weights = {}
    for nid in graph["by_type"].get("qa", []):
        topics = sorted(graph["nodes"][nid]["topics"])
        for i in range(len(topics)):
            for j in range(i + 1, len(topics)):
                key = (topics[i], topics[j])
                weights[key] = weights.get(key, 0) + 1
    return {k: w for k, w in weights.items() if w >= min_weight}
def stats(graph):
    """Summary counts by node and edge type."""
    node_counts = {t: len(v) for t, v in graph["by_type"].items()}
    edge_counts = {}
    for e in graph["edges"]:
        edge_counts[e["type"]] = edge_counts.get(e["type"], 0) + 1
    return {"nodes": node_counts, "edges": edge_counts}
