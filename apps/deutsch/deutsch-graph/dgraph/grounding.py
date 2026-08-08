"""Shared read-only grounding access for the committed Deutsch graph.

The graph is committed, but verbatim QA answers and Deutsch Well excerpts live
under the optional S3-backed data/deutsch/ corpus. These helpers degrade cleanly
when that corpus has not been fetched."""
import os
from . import parse_corpus
from . import query as dquery

ANSWER_CHAR_CAP = 1600
EXCERPT_CHAR_CAP = 900
_qa_file_cache = {}

### Paths
def find_repo_root(start):
    """Walk up from `start` until a directory containing AGENTS.md and .git is found."""
    path = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(path, "AGENTS.md")) and os.path.exists(os.path.join(path, ".git")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            raise RuntimeError("repo root not found above " + start)
        path = parent
REPO_ROOT = find_repo_root(os.path.dirname(os.path.abspath(__file__)))
GRAPH_DIR = os.path.join(REPO_ROOT, "apps", "deutsch", "deutsch-graph", "graph")
def _root(repo_root=None):
    """Resolve an optional repo root override."""
    return repo_root or REPO_ROOT

### Graph loading
def load_graph(graph_path=None):
    """Load the committed deutsch graph by default."""
    return dquery.load_graph(graph_path or GRAPH_DIR)
def corpus_available(repo_root=None):
    """True when the fetched corpus dir exists (verbatim answer text resolvable)."""
    return os.path.isdir(os.path.join(_root(repo_root), "data", "deutsch"))

### Verbatim text resolution
def answer_text(qa_node, repo_root=None):
    """Verbatim ANSWER text for a QA node via its answer_pointer, or None when the
    corpus file is absent. Block index = ordinal over question-bearing blocks,
    the same convention as dgraph.parse_corpus.parse_qa_file."""
    pointer = qa_node.get("answer_pointer") or {}
    rel_path, block_idx = pointer.get("path"), pointer.get("block")
    if rel_path is None or block_idx is None:
        return None
    path = os.path.join(_root(repo_root), rel_path)
    if not os.path.exists(path):
        return None
    if path not in _qa_file_cache:
        with open(path, encoding="utf-8") as f:
            blocks = parse_corpus.get_blocks(f.read(), "### qa") or []
        answers = []
        for block in blocks:
            fields = parse_corpus.get_fields(block)
            if parse_corpus.numbered_questions(fields):
                answers.append(fields.get("ANSWER", ""))
        _qa_file_cache[path] = answers
    answers = _qa_file_cache[path]
    return answers[block_idx] if 0 <= block_idx < len(answers) else None
def excerpt_text(excerpt_node, repo_root=None):
    """Full text of a Deutsch Well excerpt file, or None when absent."""
    rel_path = excerpt_node.get("path")
    if not rel_path:
        return None
    path = os.path.join(_root(repo_root), rel_path)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read().strip()

### Routing catalog
def topic_catalog(graph, repo_root=None):
    """Compact routing catalog: sorted topic labels and category labels with ids."""
    topics = [{"id": tid, "label": graph["nodes"][tid]["label"]} for tid in graph["by_type"].get("topic", [])]
    topics.sort(key=lambda t: t["label"])
    categories = [{"id": cid, "label": graph["nodes"][cid]["label"]} for cid in graph["by_type"].get("category", [])]
    categories.sort(key=lambda c: c["label"])
    return {"topics": topics, "categories": categories}

### Grounding package
def _trim(text, cap):
    """Trim text to `cap` chars on a word boundary with an ellipsis marker."""
    if text is None or len(text) <= cap:
        return text
    return text[:cap].rsplit(" ", 1)[0] + " [...]"
def qa_grounding(graph, topic_ids, per_topic=3, repo_root=None):
    """Best QA items across `topic_ids` -> list of dicts with verbatim answers when available."""
    items, seen = [], set()
    for tid in topic_ids:
        for qa in dquery.top_qa_for_topic(graph, tid, limit=per_topic):
            if qa["id"] in seen:
                continue
            seen.add(qa["id"])
            work = graph["nodes"].get(qa["work"], {})
            items.append({
                "id": qa["id"], "question": qa["question"], "answer": _trim(answer_text(qa, repo_root=repo_root), ANSWER_CHAR_CAP),
                "stars": qa["stars"], "starred": qa["starred"], "youtube_ts_url": qa.get("youtube_ts_url"),
                "work": qa["work"], "work_label": work.get("label", qa["work"]), "topics": qa["topics"],
            })
    return items
def category_grounding(graph, category_ids, per_category=4, excerpts_per_claim=1, repo_root=None):
    """Claims (with one supporting excerpt each) for first-tier categories."""
    adj = dquery.build_adjacency(graph)
    out = []
    for cid in category_ids:
        claim_ids = dquery.neighbors(graph, cid, edge_type="claim_of", adj=adj)[:per_category]
        for claim_id in claim_ids:
            claim = graph["nodes"][claim_id]
            entry = {"id": claim_id, "category": cid, "claim": claim["label"], "excerpts": []}
            for eid in dquery.neighbors(graph, claim_id, edge_type="excerpt_of", adj=adj)[:excerpts_per_claim]:
                node = graph["nodes"][eid]
                entry["excerpts"].append({"id": eid, "text": _trim(excerpt_text(node, repo_root=repo_root) or node["label"], EXCERPT_CHAR_CAP)})
            out.append(entry)
    return out
def concept_grounding(graph, needles, limit=4, repo_root=None):
    """Concept (book term) nodes whose label contains any needle (case-insensitive)."""
    needles = [n.lower() for n in needles if n]
    out = []
    for nid in graph["by_type"].get("concept", []):
        node = graph["nodes"][nid]
        label = node["label"].lower()
        if any(n in label or label in n for n in needles):
            out.append({"id": nid, "label": node["label"], "definition": _trim(node.get("definition"), EXCERPT_CHAR_CAP)})
            if len(out) >= limit:
                break
    return out
def build_grounding(graph, topic_ids, category_ids, concept_needles=(), repo_root=None):
    """Assemble the full grounding package for one chat turn."""
    return {
        "qa": qa_grounding(graph, topic_ids, repo_root=repo_root),
        "claims": category_grounding(graph, category_ids, repo_root=repo_root),
        "concepts": concept_grounding(graph, concept_needles),
        "corpus_available": corpus_available(repo_root=repo_root),
    }
def citation_index(graph, repo_root=None):
    """id -> renderable citation info for every node type the engine may cite."""
    index = {}
    for nid, node in graph["nodes"].items():
        entry = {"id": nid, "type": node["type"], "label": node.get("label", nid)}
        if node["type"] == "qa":
            entry["url"] = node.get("youtube_ts_url")
            work = graph["nodes"].get(node.get("work"), {})
            entry["work_label"] = work.get("label", node.get("work"))
        index[nid] = entry
    return index
