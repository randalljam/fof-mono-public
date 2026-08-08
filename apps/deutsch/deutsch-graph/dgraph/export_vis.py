"""Exports for the web viewer and programmatic consumers:
- build_vis_payload/export: aggregate works+topics+categories JSON (exports/graph_vis.json)
- export_viewer_data: full slimmed graph as script-loadable shards (web/graphdata/*.js).
  Shards load via <script> tags so the viewer works from file:// (fetch is CORS-blocked
  there); each shard stays under the repo's 512 KB pre-commit limit.
The viewer itself (web/deutsch-graph-viewer.html) is hand-authored SOURCE, not generated."""
import json
import math
import os
from . import query

VIS_LIB_RELPATH = "lib/vis-9.1.2"
KIND_GROUPS = {"interview": "interview", "talk": "talk", "documentary": "interview",
               "book": "book", "essay": "essay", "tcs_post": "tcs", "paper": "essay", "about": "about"}

def build_vis_payload(graph, min_edge_weight=1, min_topic_qa=2):
    """Aggregate view: category nodes (first-tier layer) + work nodes (with QA) + topic nodes,
    with category_topic bridges and weighted work_topic edges.
    Topics below min_topic_qa QA items are dropped to keep the view readable."""
    nodes, edges = [], []
    kept_topics = set()
    for cid in graph["by_type"].get("category", []):
        c = graph["nodes"][cid]
        nodes.append({
            "id": cid, "label": c["label"], "group": "category",
            "value": max(c["excerpt_count"], 8),
            "title": "%s — %d claims, %d excerpts (%s)" % (c["label"], c["claim_count"], c["excerpt_count"], c["origin"]),
        })
    for tid in graph["by_type"].get("topic", []):
        t = graph["nodes"][tid]
        if t["qa_count"] >= min_topic_qa:
            kept_topics.add(tid)
            nodes.append({
                "id": tid, "label": t["label"], "group": "topic",
                "value": t["qa_count"],
                "title": "%s — %d QA items in %d works" % (t["label"], t["qa_count"], t["work_count"]),
            })
    for wid in graph["by_type"].get("work", []):
        w = graph["nodes"][wid]
        if w["qa_count"] < 1:
            continue
        label = w["title"] if len(w["title"]) <= 40 else w["title"][:37] + "..."
        nodes.append({
            "id": wid, "label": label, "group": KIND_GROUPS.get(w["kind"], "work"),
            "value": w["qa_count"],
            "title": "%s (%s, %s) — %d QA items" % (w["title"], w["kind"], w["date"] or "n.d.", w["qa_count"]),
        })
    for e in graph["edges"]:
        if e["type"] == "work_topic" and e["weight"] >= min_edge_weight and e["dst"] in kept_topics:
            edges.append({"from": e["src"], "to": e["dst"], "value": e["weight"],
                          "width": 1 + math.log(e["weight"], 2)})
        elif e["type"] == "category_topic" and e["dst"] in kept_topics:
            edges.append({"from": e["src"], "to": e["dst"], "width": 2, "dashes": True,
                          "color": {"color": "#b07fd6"}})
    return {"nodes": nodes, "edges": edges}
def viewer_html(payload, lib_prefix):
    """Standalone HTML embedding the payload; script/css loaded from the vendored lib."""
    data_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return VIEWER_TEMPLATE.replace("__LIB__", lib_prefix).replace("__DATA__", data_json)
def export(graph_path, out_json, out_html, min_edge_weight=1, min_topic_qa=2):
    """Write exports/graph_vis.json and the web viewer; returns payload counts."""
    graph = query.load_graph(graph_path)
    payload = build_vis_payload(graph, min_edge_weight, min_topic_qa)
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    os.makedirs(os.path.dirname(out_html), exist_ok=True)
    depth = len(os.path.relpath(os.path.dirname(out_html), repo_root_from(out_html)).split(os.sep))
    lib_prefix = "../" * depth + VIS_LIB_RELPATH
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(viewer_html(payload, lib_prefix))
    return {"nodes": len(payload["nodes"]), "edges": len(payload["edges"])}
def repo_root_from(path):
    """Walk up from a path until the repo root (dir containing manifests/) is found."""
    cur = os.path.dirname(os.path.abspath(path))
    while cur != os.path.dirname(cur):
        if os.path.isdir(os.path.join(cur, "manifests")) and os.path.isdir(os.path.join(cur, "lib")):
            return cur
        cur = os.path.dirname(cur)
    return os.getcwd()

VIEWER_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Deutsch Graph — works and topics</title>
<script src="__LIB__/vis-network.min.js"></script>
<link rel="stylesheet" href="__LIB__/vis-network.css">
<style>
  html, body { margin: 0; height: 100%; font-family: sans-serif; }
  #graph { width: 100%; height: 100%; }
  #panel { position: absolute; top: 10px; left: 10px; z-index: 10; background: rgba(255,255,255,0.92);
           padding: 10px 14px; border-radius: 6px; box-shadow: 0 1px 4px rgba(0,0,0,0.3); max-width: 340px; }
  #panel h1 { font-size: 15px; margin: 0 0 6px 0; }
  #panel p { font-size: 12px; margin: 4px 0; color: #333; }
  #search { width: 100%; box-sizing: border-box; margin-top: 6px; }
</style>
</head>
<body>
<div id="panel">
  <h1>Deutsch Graph — works &amp; topics</h1>
  <p>Generated by <code>build_graph.py export-vis</code>. Node size = QA count; edge width = topic weight. Drag, zoom, click.</p>
  <input id="search" type="text" placeholder="Find node (press Enter)">
  <p id="status"></p>
</div>
<div id="graph"></div>
<script>
const data = __DATA__;
const nodes = new vis.DataSet(data.nodes);
const edges = new vis.DataSet(data.edges);
const groups = {
  category:  { color: { background: "#9d4edd", border: "#5a189a" }, shape: "hexagon",
               font: { size: 20, color: "#3c096c" } },
  topic:     { color: { background: "#f9c74f", border: "#c79a2a" }, shape: "dot" },
  interview: { color: { background: "#4d908e", border: "#2f5d5c" }, shape: "dot" },
  talk:      { color: { background: "#577590", border: "#354c61" }, shape: "dot" },
  book:      { color: { background: "#f94144", border: "#a32729" }, shape: "diamond" },
  essay:     { color: { background: "#90be6d", border: "#5e8145" }, shape: "square" },
  tcs:       { color: { background: "#43aa8b", border: "#2a6f5a" }, shape: "square" },
  about:     { color: { background: "#adb5bd", border: "#6c757d" }, shape: "square" }
};
const network = new vis.Network(document.getElementById("graph"), { nodes, edges }, {
  groups,
  nodes: { scaling: { min: 6, max: 40 }, font: { size: 13 } },
  edges: { color: { color: "#c9c9c9", highlight: "#333" }, smooth: false },
  physics: { solver: "forceAtlas2Based", forceAtlas2Based: { gravitationalConstant: -60, springLength: 90 },
             stabilization: { iterations: 300 } },
  interaction: { hover: true, tooltipDelay: 120 }
});
document.getElementById("status").textContent = data.nodes.length + " nodes, " + data.edges.length + " edges";
document.getElementById("search").addEventListener("keydown", function (ev) {
  if (ev.key !== "Enter") return;
  const needle = this.value.toLowerCase();
  const hit = data.nodes.find(n => n.label.toLowerCase().includes(needle) || n.id.toLowerCase().includes(needle));
  if (hit) { network.selectNodes([hit.id]); network.focus(hit.id, { scale: 1.1, animation: true }); }
});
</script>
</body>
</html>
"""


### Full viewer payload (slimmed per docs/graph-spec.md D3: previews + pointers, no bodies)
SHARD_BUDGET = 400 * 1024
def build_viewer_payload(graph):
    """Slim the loaded graph into the section arrays the web viewer consumes."""
    nodes = graph["nodes"]
    payload = {"categories": [], "claims": [], "topics": [], "works": [], "concepts": [],
               "chapters": [], "qa": [], "excerpts": [], "work_topic": [], "category_topic": []}
    for nid in graph["by_type"].get("category", []):
        c = nodes[nid]
        payload["categories"].append({"id": c["id"], "label": c["label"], "def": c["definition"],
                                      "origin": c["origin"], "topics": c["topics"],
                                      "claims": c["claim_count"], "excerpts": c["excerpt_count"]})
    for nid in graph["by_type"].get("claim", []):
        c = nodes[nid]
        payload["claims"].append({"id": c["id"], "cat": c["category"], "text": c["text"], "path": c["path"]})
    for nid in graph["by_type"].get("topic", []):
        t = nodes[nid]
        payload["topics"].append({"id": t["id"], "label": t["label"], "qa_count": t["qa_count"],
                                  "work_count": t["work_count"]})
    for nid in graph["by_type"].get("work", []):
        w = nodes[nid]
        payload["works"].append({"id": w["id"], "label": w["title"], "kind": w["kind"], "date": w["date"],
                                 "qa_count": w["qa_count"], "starred": w["starred_count"],
                                 "youtube": w["link_youtube"], "link": w["link"],
                                 "path": w["formats"].get("qafixed") or w["formats"].get("text")
                                         or w["formats"].get("vrb")})
    for nid in graph["by_type"].get("concept", []):
        c = nodes[nid]
        payload["concepts"].append({"id": c["id"], "label": c["label"], "def": c["definition"],
                                    "work": c["source_work"], "chap": c.get("chapter")})
    for nid in graph["by_type"].get("chapter", []):
        c = nodes[nid]
        payload["chapters"].append({"id": c["id"], "book": c["book"], "num": c["number"],
                                    "title": c["title"], "summary": c["summary"], "path": c["path"]})
    for nid in graph["by_type"].get("qa", []):
        q = nodes[nid]
        payload["qa"].append({"id": q["id"], "work": q["work"], "q": q["question"],
                              "t": q["timestamp_sec"], "u": q["youtube_ts_url"], "topics": q["topics"],
                              "stars": q["stars"], "starred": q["starred"],
                              "path": q["answer_pointer"]["path"], "block": q["answer_pointer"]["block"]})
    for nid in graph["by_type"].get("excerpt", []):
        e = nodes[nid]
        payload["excerpts"].append({"id": e["id"], "claim": e["claim"], "cat": e["category"],
                                    "text": e["text_preview"], "chars": e["text_chars"],
                                    "work": e["source_work"], "chap": e["source_chapter"], "path": e["path"]})
    for e in graph["edges"]:
        if e["type"] == "work_topic":
            payload["work_topic"].append([e["src"], e["dst"], e["weight"]])
        elif e["type"] == "category_topic":
            payload["category_topic"].append([e["src"], e["dst"]])
    return payload
def chunk_section(name, items):
    """Split one section's array into JSON chunks under the shard budget."""
    chunks, current, size = [], [], 0
    for item in items:
        blob = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if current and size + len(blob.encode()) > SHARD_BUDGET:
            chunks.append(current)
            current, size = [], 0
        current.append(blob)
        size += len(blob.encode()) + 1
    if current:
        chunks.append(current)
    return [(name, chunk) for chunk in chunks]
def export_viewer_data(graph_path, out_dir):
    """Write web/graphdata/: index.js (shard list) + numbered shard files. Returns file list."""
    graph = query.load_graph(graph_path)
    payload = build_viewer_payload(graph)
    pieces = []
    for name in ("categories", "claims", "topics", "works", "concepts", "chapters", "qa", "excerpts",
                 "work_topic", "category_topic"):
        pieces.extend(chunk_section(name, payload[name]))
    os.makedirs(out_dir, exist_ok=True)
    for stale in os.listdir(out_dir):
        if stale.endswith(".js"):
            os.remove(os.path.join(out_dir, stale))
    shard_files = []
    for i, (name, blobs) in enumerate(pieces):
        fname = "dgraph-%02d-%s.js" % (i, name)
        shard_files.append(fname)
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as f:
            f.write("window.DGRAPH_PARTS.push([%s,[\n" % json.dumps(name))
            f.write(",\n".join(blobs))
            f.write("\n]]);\n")
    with open(os.path.join(out_dir, "index.js"), "w", encoding="utf-8") as f:
        f.write("window.DGRAPH_PARTS = [];\nwindow.DGRAPH_SHARDS = %s;\n"
                % json.dumps(shard_files))
    return shard_files
