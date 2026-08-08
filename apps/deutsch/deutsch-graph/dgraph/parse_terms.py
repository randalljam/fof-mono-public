"""Parser for the curated terms collection (data/deutsch/terms):
- 'Terms - BOI/'  : '## Term' heading + definition + optional 'Chapter N: Title' ref (BOI glossary)
- 'Terms - FOR/'  : '## Term' heading + definition + optional 'The Fabric of Reality - Chapter N' ref
- 'Terms - BOIxyz/': '# Term' heading + definition (thebeginningofinfinity.xyz glossary)
- 'Topics - Important/': plain definition text; file name = Randy's hand-picked first-tier topic"""
import os
import re

TERMS_ROOT = "data/deutsch/terms"
CHAPTER_REF_BOI_RE = re.compile(r"^Chapter (\d+)\s*[:\-]", re.MULTILINE)
CHAPTER_REF_FOR_RE = re.compile(r"The Fabric of Reality\s*-\s*Chapter (\d+)", re.IGNORECASE)

def term_from_file(file_name, text):
    """Term label: markdown heading when present, else file stem with underscores as spaces."""
    m = re.search(r"^#{1,2}\s+(.+)$", text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return file_name[:-3].replace("_", " ").strip()
def definition_from_text(text, chapter_re):
    """Definition body: strip headings and the chapter-reference line; collapse whitespace."""
    lines = []
    for line in text.split("\n"):
        if line.startswith("#"):
            continue
        if chapter_re and chapter_re.search(line):
            continue
        lines.append(line)
    return re.sub(r"\s+", " ", " ".join(lines)).strip()
def load_folder(repo_root, folder, chapter_re):
    """Parse one terms subfolder -> list of {term, definition, chapter_num, path}."""
    dir_path = os.path.join(repo_root, TERMS_ROOT, folder)
    if not os.path.isdir(dir_path):
        return None
    out = []
    for file_name in sorted(os.listdir(dir_path)):
        if not file_name.endswith(".md"):
            continue
        rel_path = "%s/%s/%s" % (TERMS_ROOT, folder, file_name)
        with open(os.path.join(dir_path, file_name), encoding="utf-8") as f:
            text = f.read()
        chapter_num = None
        if chapter_re:
            m = chapter_re.search(text)
            if m:
                chapter_num = int(m.group(1))
        out.append({
            "term": term_from_file(file_name, text),
            "definition": definition_from_text(text, chapter_re),
            "chapter_num": chapter_num,
            "path": rel_path,
        })
    return out
def load_terms(repo_root, diagnostics):
    """Load all four term sources. Returns dict with keys boi/for/boixyz/important (lists, [] when absent)."""
    sources = {
        "boi": ("Terms - BOI", CHAPTER_REF_BOI_RE),
        "for": ("Terms - FOR", CHAPTER_REF_FOR_RE),
        "boixyz": ("Terms - BOIxyz", None),
        "important": ("Topics - Important", None),
    }
    out = {}
    for key, (folder, chapter_re) in sources.items():
        rows = load_folder(repo_root, folder, chapter_re)
        if rows is None:
            diagnostics.append("MISSING LOCAL FOLDER (run fetch): %s/%s" % (TERMS_ROOT, folder))
            rows = []
        out[key] = rows
    return out
