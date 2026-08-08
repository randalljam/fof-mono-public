"""Slug and node-id construction. IDs are permanent; see docs/graph-spec.md."""
import re

### Suffix vocabulary — corpus filename stems end with _<suffix>; anything else is part of the title
KNOWN_SUFFIXES = {
    "qafixed", "qa-multi", "vrb", "read-qafixed", "read-logan", "host",
    "randycomments", "qa-topstars", "vrb-topstars", "yt", "dgwhspm",
    "nova2gen", "whspm", "whspmerge", "prepqa", "propernames", "emilia",
    "bertafteremilia", "qa", "read", "dq", "hspm", "topstars",
}

### Slug and id helpers
def slugify(text):
    """Lowercase slug: spaces/underscores/dashes -> single dash, ascii alnum only."""
    text = text.lower()
    text = re.sub(r"[’'\"]", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")
def split_base_name(file_name):
    """Split a corpus file name into (base_name, suffix) using the known-suffix vocabulary.
    Strips the extension and repeatedly removes trailing _<known-suffix> tokens; the
    outermost (last) suffix is returned, e.g. 'X_vrb_propernames.md' -> ('X', 'vrb_propernames')."""
    stem = re.sub(r"\.(md|json|html|csv|txt|pdf)$", "", file_name)
    suffix_parts = []
    while "_" in stem:
        head, tail = stem.rsplit("_", 1)
        if tail.lower() in KNOWN_SUFFIXES:
            suffix_parts.insert(0, tail)
            stem = head
        else:
            break
    return stem, "_".join(suffix_parts)
def work_slug(base_name):
    """Work slug keeps the repo's date_slug convention: YYYY-MM-DD_rest-slugified."""
    m = re.match(r"^(\d{4}-\d{2}-\d{2})_(.*)$", base_name)
    if m:
        return m.group(1) + "_" + slugify(m.group(2))
    return slugify(base_name)
def work_id(base_name):
    """Node id for a work."""
    return "work:" + work_slug(base_name)
def topic_id(label):
    """Node id for a topic label."""
    return "topic:" + slugify(label)
def qa_id(work_slug_str, block_ordinal):
    """Node id for a QA block (zero-padded ordinal)."""
    return "qa:%s:%03d" % (work_slug_str, block_ordinal)
def concept_id(book_code, label):
    """Node id for a defined term."""
    return "concept:%s/%s" % (book_code, slugify(label))
def chapter_id(book_code, number):
    """Node id for a book chapter."""
    return "chapter:%s/%02d" % (book_code, number)
def date_from_base_name(base_name):
    """YYYY-MM-DD filename prefix, or None."""
    m = re.match(r"^(\d{4}-\d{2}-\d{2})_", base_name)
    return m.group(1) if m else None
def title_from_base_name(base_name):
    """Human title: base name minus the date prefix."""
    return re.sub(r"^\d{4}-\d{2}-\d{2}_", "", base_name)
