"""Parsers for the corpus markdown grammar (metadata blocks, QA blocks, essays).

The QA-block grammar intentionally matches core/structured.py (get_blocks_from_file /
get_all_fields_dict) so graph block ordinals line up with QRAG's Pinecone vector ids.
Reimplemented stdlib-only because core/structured.py imports GUI deps (pyperclip,
pyautogui) that are unavailable headless."""
import re

### Heading and block extraction (mirrors core/structured.get_blocks_from_file)
def get_heading_text(text, heading):
    """Return the text under `heading` up to the next heading of the same or higher level."""
    level = len(heading) - len(heading.lstrip("#"))
    pattern = re.compile(r"^" + re.escape(heading) + r"\s*$", re.MULTILINE)
    m = pattern.search(text)
    if not m:
        return None
    rest = text[m.end():]
    stop = re.compile(r"^#{1,%d} " % level, re.MULTILINE)
    m2 = stop.search(rest)
    return rest[:m2.start()] if m2 else rest
def get_blocks(text, heading="### qa"):
    """Split the section under `heading` into blocks on blank lines (core/structured parity)."""
    section = get_heading_text(text, heading)
    if section is None:
        return None
    section = re.sub(r"^#.*\n?", "", section, flags=re.MULTILINE)
    section = re.sub(r"\n{3,}", "\n\n", section)
    return [b.strip() for b in section.split("\n\n") if b.strip()]

### Field parsing (mirrors core/structured.get_all_fields_dict grammar)
FIELD_RE = re.compile(r"^([A-Z][A-Z0-9 _-]*?):[ \t]?(.*)$")
def get_fields(block):
    """Parse one block into an ordered dict of ALLCAPS fields; values run to the next field line."""
    fields = {}
    current = None
    for line in block.split("\n"):
        m = FIELD_RE.match(line)
        if m:
            current = m.group(1)
            fields[current] = m.group(2)
        elif current is not None:
            fields[current] = fields[current] + "\n" + line
    return {k: v.strip() for k, v in fields.items()}
def parse_timestamp(value):
    """Parse 'TIMESTAMP: [m:ss](url&t=SECONDS)' -> (seconds, url) or (None, None)."""
    m = re.search(r"\((https?://[^)]+)\)", value or "")
    if not m:
        return None, None
    url = m.group(1)
    t = re.search(r"[?&]t=(\d+)", url)
    return (int(t.group(1)) if t else None), url
def parse_topics(value):
    """Comma-separated TOPICS field -> list of stripped labels."""
    if not value:
        return []
    return [t.strip() for t in value.split(",") if t.strip()]
def parse_stars(value):
    """STARS field -> int (blank/invalid -> 0)."""
    try:
        return int(value.strip())
    except (ValueError, AttributeError):
        return 0

### Metadata section
def parse_metadata(text):
    """Parse the '## metadata' section into a lowercase key dict ('link youtube', 'length', ...)."""
    section = get_heading_text(text, "## metadata")
    meta = {}
    if not section:
        return meta
    for line in section.strip().split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip().lower()] = val.strip()
    return meta

### QA files
def numbered_questions(fields):
    """All QUESTION / QUESTION N values in numeric order; plain QUESTION first."""
    out = []
    if "QUESTION" in fields:
        out.append(fields["QUESTION"])
    numbered = []
    for name, value in fields.items():
        m = re.match(r"^QUESTION (\d+)$", name)
        if m:
            numbered.append((int(m.group(1)), value))
    out.extend(v for _, v in sorted(numbered))
    return out
def parse_qa_file(text, quirks=None):
    """Parse a _qafixed/_qa-multi/_qa-topstars file.
    Returns (metadata, qa_blocks) where each qa block dict has: ordinal (0-based over
    question-bearing blocks, matching core/vectordb block_num), questions, timestamp_sec,
    youtube_ts_url, topics, stars, answer_chars. Blocks without a QUESTION are skipped.
    Data quirks (e.g. duplicate QUESTION fields in one block, where the last wins as in
    core/structured) are appended to the optional `quirks` list."""
    meta = parse_metadata(text)
    blocks = get_blocks(text, "### qa")
    if blocks is None:
        return meta, None
    out = []
    ordinal = 0
    for block in blocks:
        fields = get_fields(block)
        if quirks is not None and len(re.findall(r"^QUESTION:", block, re.MULTILINE)) > 1:
            quirks.append("duplicate QUESTION field in block %d (last wins)" % ordinal)
        questions = numbered_questions(fields)
        if not questions:
            continue
        sec, url = parse_timestamp(fields.get("TIMESTAMP", ""))
        out.append({
            "ordinal": ordinal,
            "questions": questions,
            "timestamp_sec": sec,
            "youtube_ts_url": url,
            "topics": parse_topics(fields.get("TOPICS", "")),
            "stars": parse_stars(fields.get("STARS", "")),
            "answer_chars": len(fields.get("ANSWER", "")),
        })
        ordinal += 1
    return meta, out

### Essays (two metadata shapes: TCS-style '## metadata' or top-of-file 'Publication:' headers)
ESSAY_HEADER_KEYS = ("publication", "title", "subtitle", "authors", "publication date", "original link", "main link")
def parse_essay(text):
    """Extract {link, date, publication} from either essay metadata shape."""
    info = {"link": None, "date": None, "publication": None}
    meta = parse_metadata(text)
    if meta:
        info["link"] = meta.get("link") or meta.get("original link")
    head = text[:2000]
    for line in head.split("\n"):
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().lower()
        val = val.strip()
        if key in ESSAY_HEADER_KEYS and val:
            if key == "publication":
                info["publication"] = val
            elif key == "publication date":
                info["date"] = val
            elif key in ("original link", "main link") and not info["link"]:
                info["link"] = val
    return info

### Book terms ('BOI - all terms.md': **_Term_** definition lines)
TERM_RE = re.compile(r"^\*\*_(.+?)_\*\*\s*(.*)$")
def parse_terms(text):
    """Parse term-definition lines -> list of (term, definition)."""
    out = []
    for para in text.split("\n\n"):
        para = para.strip()
        m = TERM_RE.match(para)
        if m:
            out.append((m.group(1).strip(), re.sub(r"\s+", " ", m.group(2)).strip()))
    return out
def parse_summary_paragraphs(text):
    """Chapter-summary file -> list of non-heading paragraphs (order = chapter order)."""
    paras = []
    for para in text.split("\n\n"):
        para = para.strip()
        if para and not para.startswith("#"):
            paras.append(re.sub(r"\s+", " ", para))
    return paras
