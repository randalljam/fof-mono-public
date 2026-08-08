"""Annotated-transcript markdown and JSON sidecar assembly for Deutsch Interjector."""
from ctools import config as ctools_config

DISCLOSURE = "SYNTHETIC-CONTENT: The virtual-Deutsch turns are AI-generated, not spoken or endorsed by David Deutsch; quotes are verbatim-cited where marked."
def _speaker(turn):
    """Speaker label for one original turn."""
    return turn.get("speaker") or "Source"
def _turn_line(turn):
    """Render one original source turn."""
    prefix = ""
    if turn.get("timestamp"):
        prefix += "[" + turn["timestamp"] + "] "
    return "%s**%s:** %s" % (prefix, _speaker(turn), turn.get("text", ""))
def _citation_marks(citations):
    """Markdown citation node marks."""
    return " ".join("[node:%s]" % cid for cid in citations)
def _header(provenance, knobs):
    """Markdown provenance header block."""
    tone = ctools_config.TONES.get(knobs.get("tone"), ctools_config.TONES[ctools_config.DEFAULT_TONE])
    return "\n".join([
        "source-name: " + provenance.get("source_name", ""),
        "tool: deutsch-interject",
        "tone: %s (%s)" % (tone["label"], knobs.get("tone")),
        "fidelity: " + knobs.get("fidelity", ""),
        "include-agreements: " + str(bool(knobs.get("include_agreements"))).lower(),
        "model: " + (provenance.get("model") or "default"),
        "generated-at: " + provenance.get("generated_at", ""),
        DISCLOSURE,
    ])
def markdown(turns, interjections, provenance, knobs):
    """Render the annotated transcript with virtual Deutsch turns inserted after source turns."""
    by_turn = {}
    for item in interjections:
        by_turn.setdefault(item.get("turn_index"), []).append(item)
    lines = [_header(provenance, knobs), "", "# Annotated transcript", ""]
    for turn in turns:
        lines.append(_turn_line(turn))
        for item in by_turn.get(turn["index"], []):
            cites = _citation_marks(item.get("citations", []))
            suffix = (" " + cites) if cites else ""
            lines.append("")
            lines.append("> **David Deutsch (virtual):** %s%s" % (item.get("text", ""), suffix))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
def sidecar(turns, claims, interjections, skipped, provenance, knobs, notes):
    """Build the machine-readable sidecar."""
    return {"provenance": provenance, "knobs": knobs, "turns": turns, "claims": claims,
            "interjections": interjections, "skipped": skipped, "notes": notes,
            "synthetic_content": DISCLOSURE}
def assemble(turns, claims, interjections, skipped, provenance, knobs, notes):
    """Return markdown plus JSON sidecar."""
    md = markdown(turns, interjections, provenance, knobs)
    sc = sidecar(turns, claims, interjections, skipped, provenance, knobs, notes)
    return md, sc
