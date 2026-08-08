"""Book layer: work nodes for BOI/FOR, chapter nodes (with per-chapter summaries),
and concept (term) nodes from chapter TERMINOLOGY sections + the all-terms file."""
import os
import re
from . import ids
from . import parse_corpus

BOOKS = [
    {"code": "boi", "title": "The Beginning of Infinity", "date": "2011-03-31", "full_text": "data/deutsch/books/boi.md",
     "chapters_dir": "data/deutsch/books/BOI chapters", "terms": "data/deutsch/books/BOI - all terms.md",
     "chapter_count": 18},
    {"code": "for", "title": "The Fabric of Reality", "date": "1997-08-01", "full_text": "data/deutsch/books/for.md",
     "chapters_dir": "data/deutsch/books/FOR chapters", "terms": None, "chapter_count": 14},
]
CHAPTER_FILE_RE = re.compile(r"^Chapter (\d+) ?- ?(.+)\.md$")
BOLD_TERM_RE = re.compile(r"^\*\*_?(.+?)_?\*\*\s*(.*)$", re.DOTALL)

def read_text(repo_root, rel_path):
    """Read a repo-relative file, or None if absent locally."""
    path = os.path.join(repo_root, rel_path)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()
def chapter_summary(text):
    """First paragraph of the chapter's '## SUMMARY' section, or None."""
    section = parse_corpus.get_heading_text(text, "## SUMMARY")
    if not section:
        return None
    paras = [p.strip() for p in section.split("\n\n") if p.strip() and not p.strip().startswith("#")]
    return re.sub(r"\s+", " ", paras[0]) if paras else None
def chapter_terms(text):
    """(term, definition) pairs from the chapter's '## TERMINOLOGY' section."""
    section = parse_corpus.get_heading_text(text, "## TERMINOLOGY")
    if not section:
        return []
    out = []
    for para in section.split("\n\n"):
        m = BOLD_TERM_RE.match(para.strip())
        if m:
            out.append((m.group(1).strip(), re.sub(r"\s+", " ", m.group(2)).strip()))
    return out
def build_book_nodes(repo_root, diagnostics):
    """Return (work_nodes, chapter_nodes, concept_nodes, chapter_of_edges, concept_of_edges)."""
    works, chapters, chapter_edges = [], [], []
    concepts, concept_edges, seen_concepts = [], [], set()
    for book in BOOKS:
        wid = "work:" + book["code"]
        formats = {}
        if os.path.exists(os.path.join(repo_root, book["full_text"])):
            formats["text"] = book["full_text"]
        works.append({
            "id": wid, "type": "work", "kind": "book", "label": book["title"],
            "title": book["title"], "date": book["date"], "by_deutsch": True,
            "base_name": book["code"], "formats": formats, "link_youtube": None, "link": None,
            "layer_max": 4, "qa_count": 0, "starred_count": 0, "collection": "books",
        })
        chapter_dir = os.path.join(repo_root, book["chapters_dir"])
        found = []
        if os.path.isdir(chapter_dir):
            for name in os.listdir(chapter_dir):
                m = CHAPTER_FILE_RE.match(name)
                if m:
                    found.append((int(m.group(1)), m.group(2).strip(), book["chapters_dir"] + "/" + name))
        for number, title, rel_path in sorted(found):
            cid = ids.chapter_id(book["code"], number)
            text = read_text(repo_root, rel_path)
            chapters.append({
                "id": cid, "type": "chapter", "label": "Ch %d - %s" % (number, title),
                "book": wid, "number": number, "title": title, "path": rel_path,
                "summary": chapter_summary(text) if text else None,
            })
            chapter_edges.append({"src": cid, "dst": wid, "type": "chapter_of"})
            for term, definition in (chapter_terms(text) if text else []):
                _add_concept(concepts, concept_edges, seen_concepts, book["code"], wid,
                             term, definition, rel_path, cid)
        if len(found) != book["chapter_count"]:
            diagnostics.append("found %d chapter files for %s, expected %d" % (len(found), book["code"], book["chapter_count"]))
        if book["terms"]:
            text = read_text(repo_root, book["terms"])
            if text:
                for term, definition in parse_corpus.parse_terms(text):
                    _add_concept(concepts, concept_edges, seen_concepts, book["code"], wid,
                                 term, definition, book["terms"], None)
    return works, chapters, concepts, chapter_edges, concept_edges
def _add_concept(concepts, concept_edges, seen, book_code, work_id, term, definition, source_path, chapter_id_or_none):
    """Add a concept node once per (book, term); first definition wins (chapters parse first)."""
    tid = ids.concept_id(book_code, term)
    if not tid.split("/")[-1] or tid in seen:
        return
    seen.add(tid)
    concepts.append({
        "id": tid, "type": "concept", "label": term, "definition": definition,
        "source_work": work_id, "source_path": source_path, "chapter": chapter_id_or_none,
        "source": "chapter-terminology" if chapter_id_or_none else "all-terms-file",
    })
    concept_edges.append({"src": tid, "dst": work_id, "type": "concept_of"})
