"""Rewritten markdown, change-list markdown, and sidecar assembly for Content Redo."""
from ctools import config as ctools_config
from . import config

DISCLOSURE = "AI-TRANSFORMATION: This is an AI transformation of the named source for private educational use; every change is listed with its grounding."
def _tone_label(knobs):
    """Human-readable tone row."""
    return ctools_config.TONES.get(knobs.get("tone"), ctools_config.TONES[ctools_config.DEFAULT_TONE])
def _header(provenance, knobs):
    """Markdown provenance header block."""
    tone = _tone_label(knobs)
    degree = config.REMIX_DEGREES.get(knobs.get("degree"), config.REMIX_DEGREES[config.DEFAULT_DEGREE])
    level = config.READING_LEVELS.get(knobs.get("reading_level"), config.READING_LEVELS[config.DEFAULT_READING_LEVEL])
    return "\n".join([
        "source-name: " + provenance.get("source_name", ""),
        "tool: content-redo",
        "tone: %s (%s)" % (tone["label"], knobs.get("tone")),
        "degree: %s (%s)" % (degree["label"], knobs.get("degree")),
        "reading-level: %s (%s)" % (level["label"], knobs.get("reading_level")),
        "model: " + (provenance.get("model") or "default"),
        "generated-at: " + provenance.get("generated_at", ""),
        DISCLOSURE,
    ])
def _turn_prefix(row):
    """Speaker/timestamp prefix for one rewritten row."""
    prefix = ""
    if row.get("timestamp"):
        prefix += "[" + row["timestamp"] + "] "
    if row.get("speaker"):
        prefix += "**" + row["speaker"] + ":** "
    return prefix
def _citation_marks(citations):
    """Markdown citation node marks."""
    return " ".join("[node:%s]" % cid for cid in citations)
def markdown(diff, provenance, knobs):
    """Render the rewritten document with additions clearly marked."""
    lines = [_header(provenance, knobs), "", "# Rewritten document", ""]
    for row in diff:
        lines.append(_turn_prefix(row) + row.get("rewritten_text", ""))
        for add in row.get("additions", []):
            marks = _citation_marks(add.get("citations", []))
            suffix = (" " + marks) if marks else ""
            lines.append("")
            lines.append("> [added] %s%s" % (add.get("text", ""), suffix))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
def _claim_verdict_lines(change):
    """Render claim verdicts supporting one change."""
    rows = []
    for claim in change.get("claim_verdicts", []):
        text = "%s: %s" % (claim.get("id"), claim.get("verdict"))
        if claim.get("deutsch_position"):
            text += " - " + claim.get("deutsch_position")
        rows.append(text)
    return rows
def change_list(changes, skipped_notes, provenance, knobs):
    """Render the per-change audit list."""
    lines = [_header(provenance, knobs), "", "# Change list", ""]
    if not changes:
        lines.append("No changes were applied.")
        lines.append("")
    for change in changes:
        lines.append("## %s - %s, turn %s" % (change.get("id"), change.get("change_type"), change.get("turn_index")))
        lines.append("- Original: " + (change.get("original_text") or "[new paragraph]"))
        lines.append("- New: " + (change.get("new_text") or "[unchanged]"))
        lines.append("- Why: " + change.get("why", ""))
        verdicts = _claim_verdict_lines(change)
        lines.append("- Claim verdicts: " + ("; ".join(verdicts) if verdicts else "none"))
        lines.append("- Citations: " + (_citation_marks(change.get("citations", [])) or "none"))
        lines.append("")
    if skipped_notes:
        lines.append("# Skipped notes")
        lines.append("")
        for note in skipped_notes:
            lines.append("- %s" % note.get("reason", note.get("note", "")))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
def sidecar(turns, claims, plan, diff, changes, skipped_notes, provenance, knobs):
    """Build the machine-readable sidecar."""
    return {"provenance": provenance, "knobs": knobs, "turns": turns, "claims": claims,
            "plan": plan, "diff": diff, "changes": changes, "skipped_notes": skipped_notes,
            "disclosure": DISCLOSURE}
def assemble(turns, claims, plan, diff, changes, skipped_notes, provenance, knobs):
    """Return rewritten markdown, change-list markdown, and JSON sidecar."""
    md = markdown(diff, provenance, knobs)
    changes_md = change_list(changes, skipped_notes, provenance, knobs)
    sc = sidecar(turns, claims, plan, diff, changes, skipped_notes, provenance, knobs)
    return md, changes_md, sc
