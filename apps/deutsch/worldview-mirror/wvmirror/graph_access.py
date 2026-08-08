"""Worldview Mirror graph access facade over shared dgraph.grounding services."""
from . import config
from dgraph import grounding as dgrounding

ANSWER_CHAR_CAP = dgrounding.ANSWER_CHAR_CAP
EXCERPT_CHAR_CAP = dgrounding.EXCERPT_CHAR_CAP
_qa_file_cache = dgrounding._qa_file_cache
_trim = dgrounding._trim

### Graph loading
def load_graph(graph_path=None):
    """Load the committed deutsch graph."""
    return dgrounding.load_graph(graph_path or config.GRAPH_DIR)
def corpus_available():
    """True when the fetched corpus dir exists (verbatim answer text resolvable)."""
    return dgrounding.corpus_available(repo_root=config.REPO_ROOT)

### Verbatim text resolution
def answer_text(qa_node):
    """Verbatim ANSWER text for a QA node, or None when the corpus file is absent."""
    return dgrounding.answer_text(qa_node, repo_root=config.REPO_ROOT)
def excerpt_text(excerpt_node):
    """Full text of a Deutsch Well excerpt file, or None when absent."""
    return dgrounding.excerpt_text(excerpt_node, repo_root=config.REPO_ROOT)

### Routing catalog
def topic_catalog(graph):
    """Compact routing catalog: sorted topic labels and category labels with ids."""
    return dgrounding.topic_catalog(graph, repo_root=config.REPO_ROOT)

### Grounding package
def qa_grounding(graph, topic_ids, per_topic=3):
    """Best QA items across `topic_ids` -> list of dicts with verbatim answers when available."""
    return dgrounding.qa_grounding(graph, topic_ids, per_topic=per_topic, repo_root=config.REPO_ROOT)
def category_grounding(graph, category_ids, per_category=4, excerpts_per_claim=1):
    """Claims (with one supporting excerpt each) for first-tier categories."""
    return dgrounding.category_grounding(graph, category_ids, per_category=per_category,
                                         excerpts_per_claim=excerpts_per_claim, repo_root=config.REPO_ROOT)
def concept_grounding(graph, needles, limit=4):
    """Concept (book term) nodes whose label contains any needle (case-insensitive)."""
    return dgrounding.concept_grounding(graph, needles, limit=limit, repo_root=config.REPO_ROOT)
def build_grounding(graph, topic_ids, category_ids, concept_needles=()):
    """Assemble the full grounding package for one chat turn."""
    return dgrounding.build_grounding(graph, topic_ids, category_ids, concept_needles, repo_root=config.REPO_ROOT)
def citation_index(graph):
    """id -> renderable citation info for every node type the engine may cite."""
    return dgrounding.citation_index(graph, repo_root=config.REPO_ROOT)
