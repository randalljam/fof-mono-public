"""
Extract surrounding text for each occurrence of a phrase in boi.md and write boi-problems.md.
"""
import re
from pathlib import Path


def _start_of_paragraph(text, i):
    """Return index of the start of the paragraph containing position i."""
    p = text.rfind("\n\n", 0, i)
    return 0 if p == -1 else p + 2


def _expand_to_paragraph_bounds(text, match_start, match_end, n_before, n_after):
    """
    Return (start, end) indices covering the paragraph with the match plus n_before paragraphs
    before and n_after paragraphs after.

    :param text: str, full source.
    :param match_start: int, match start index.
    :param match_end: int, match end index.
    :param n_before: int, paragraph breaks to include before the match paragraph.
    :param n_after: int, paragraph breaks to include after the match paragraph.
    :return bounds: tuple, (start, end) slice indices for text[start:end].
    """
    p_start = _start_of_paragraph(text, match_start)
    pos = p_start
    for _ in range(n_before):
        before = text.rfind("\n\n", 0, pos)
        if before == -1:
            pos = 0
            break
        pos = before + 2
    p_after = text.find("\n\n", match_end)
    chunk_end = len(text) if p_after == -1 else p_after
    end = chunk_end
    for _ in range(n_after):
        nxt = text.find("\n\n", end + 2)
        if nxt == -1:
            end = len(text)
            break
        end = nxt
    return pos, end


def _chapter_at(pos, chapters):
    """
    Return (number, title) for the latest chapter heading at or before pos.

    :param pos: int, index in text.
    :param chapters: list, tuples (start_index, chapter_num_str, title_str).
    :return result: tuple, (chapter_num_str, title_str) or None.
    """
    result = None
    for start, num, title in chapters:
        if start <= pos:
            result = (num, title)
    return result


def _extend_left_to_chars(text, estart, match_start, min_left):
    """
    Move estart left so that (match_start - estart) is at least min_left, aligned to paragraph start.

    :param text: str, full source.
    :param estart: int, excerpt start.
    :param match_start: int, match position.
    :param min_left: int, minimum characters before match.
    :return new_start: int, new excerpt start index.
    """
    left_len = match_start - estart
    if left_len >= min_left:
        return estart
    need = min_left - left_len
    new_estart = max(0, estart - need)
    return _start_of_paragraph(text, new_estart)


def _extend_right_to_chars(text, eend, match_end, min_right):
    """
    Move eend right so that (eend - match_end) is at least min_right.

    :param text: str, full source.
    :param eend: int, excerpt end.
    :param match_end: int, match end position.
    :param min_right: int, minimum characters after match.
    :return new_end: int, new excerpt end index.
    """
    right_len = eend - match_end
    if right_len >= min_right:
        return eend
    need = min_right - right_len
    return min(len(text), eend + need)


def run_extract(boi_path, out_path, phrase_regex, n_before=4, n_after=4, min_chars_each_side=3200):
    """
    Scan boi.md for phrase_regex and write markdown excerpts with chapter headings.

    :param boi_path: path, source markdown file.
    :param out_path: path, output markdown file.
    :param phrase_regex: str, regex pattern (e.g. problems are soluble/solved with word boundary).
    :param n_before: int, paragraph breaks to walk backward from the match paragraph.
    :param n_after: int, paragraph breaks to walk forward after the match paragraph.
    :param min_chars_each_side: int, expand excerpt if fewer than this many chars on a side of the match.
    :return count: int, number of matches written.
    """
    text = boi_path.read_text(encoding="utf-8")
    chapter_re = re.compile(r"^# Chapter (\d+) - (.+)$", re.MULTILINE)
    chapters = []
    for m in chapter_re.finditer(text):
        chapters.append((m.start(), m.group(1), m.group(2).strip()))
    pat = re.compile(phrase_regex)
    matches = list(pat.finditer(text))
    lines_out = []
    lines_out.append("# BOI excerpts: “problems are sol…”")
    lines_out.append("")
    lines_out.append("Compiled from `boi.md` by regex matching whole phrases `problems are soluble` (ten times) and `problems are solved` (once; the substring “problems are sol” would otherwise match inside that phrase without a word boundary). Eleven excerpts; each block includes several paragraphs before and after the match.")
    lines_out.append("")
    for idx, m in enumerate(matches, start=1):
        if idx > 1:
            lines_out.append("")
            lines_out.append("")
        ch = _chapter_at(m.start(), chapters)
        ch_label = f"Chapter {ch[0]} — {ch[1]}" if ch else "Unknown chapter"
        estart, eend = _expand_to_paragraph_bounds(text, m.start(), m.end(), n_before, n_after)
        estart = _extend_left_to_chars(text, estart, m.start(), min_chars_each_side)
        eend = _extend_right_to_chars(text, eend, m.end(), min_chars_each_side)
        excerpt = text[estart:eend]
        rel = m.start() - estart
        hl = excerpt[:rel] + "**" + m.group(0) + "**" + excerpt[rel + len(m.group(0)) :]
        lines_out.append(f"## {ch_label} (occurrence {idx} of {len(matches)})")
        lines_out.append("")
        lines_out.append(hl.strip())
    out_path.write_text("\n".join(lines_out).rstrip() + "\n", encoding="utf-8")
    return len(matches)


if __name__ == "__main__":
    _root = Path(__file__).resolve().parents[2]
    _boi = _root / "data" / "deutsch" / "books" / "boi.md"
    _out = _root / "data" / "deutsch" / "books" / "boi-problems.md"
    n = run_extract(_boi, _out, r"problems are sol(?:uble|ved)\b")
    print(f"wrote {_out} ({n} matches)")
