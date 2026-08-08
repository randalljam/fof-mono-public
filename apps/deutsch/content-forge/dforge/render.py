"""Markdown output and citations-sidecar rendering for Deutsch Content Forge."""

DISCLOSURE = "AI-GENERATED: This piece was generated from cited deutsch-graph sources; it was not written or endorsed by David Deutsch."
def _header(provenance, knobs):
    """Markdown provenance header block."""
    return "\n".join([
        "description: " + provenance.get("description", ""),
        "tool: content-forge",
        "format: " + knobs.get("format", ""),
        "length: " + knobs.get("length", ""),
        "tone: %s (%s)" % (knobs.get("tone_label", ""), knobs.get("tone", "")),
        "model: " + (provenance.get("model") or "default"),
        "generated-at: " + provenance.get("generated_at", ""),
        DISCLOSURE,
    ])
def document(piece, provenance, knobs):
    """Render final document markdown."""
    lines = [_header(provenance, knobs), "", "# Content Forge Output", "", piece.strip()]
    return "\n".join(lines).rstrip() + "\n"
def _citation_label(citation):
    """Compact citation label for sidecar tables."""
    label = citation.get("label") or citation.get("id", "")
    work = citation.get("work")
    if work:
        return "%s (%s)" % (citation.get("id"), work)
    return citation.get("id", label)
def _table_escape(text):
    """Escape markdown table pipes."""
    return str(text or "").replace("|", "\\|").replace("\n", " ")
def sidecar_markdown(sidecar):
    """Render a human-readable citations sidecar."""
    coverage = sidecar.get("coverage", {})
    lines = [
        "# Content Forge Citations Sidecar",
        "",
        "description: " + sidecar.get("provenance", {}).get("description", ""),
        "generated-at: " + sidecar.get("provenance", {}).get("generated_at", ""),
        "coverage: %d/%d sections grounded; %d citations; %d invalid stripped" % (
            coverage.get("n_grounded", 0), coverage.get("n_sections", 0),
            coverage.get("n_citations", 0), coverage.get("n_invalid", 0)),
        "",
        "## Sections",
        "| Section | Words | Grounded | Citations | Invalid stripped |",
        "| --- | ---: | --- | --- | --- |",
    ]
    for section in sidecar.get("sections", []):
        citations = ", ".join(_citation_label(c) for c in section.get("citations", [])) or "-"
        invalid = ", ".join(section.get("invalid_citations", [])) or "-"
        grounded = "yes" if section.get("grounded") else "no"
        lines.append("| %s | %d | %s | %s | %s |" % (
            _table_escape(section.get("heading")), section.get("word_count", 0), grounded,
            _table_escape(citations), _table_escape(invalid)))
    lines.extend(["", "## Retrieved But Uncited"])
    unquoted = sidecar.get("context_package", {}).get("retrieved_but_uncited", [])
    if not unquoted:
        lines.append("All retrieved source nodes were cited at least once.")
    else:
        for node in unquoted:
            lines.append("- `%s` — %s" % (node.get("id"), node.get("label", "")))
    lines.extend(["", "## Invalid Citations"])
    if not sidecar.get("invalid_citations"):
        lines.append("No invalid citations were generated.")
    else:
        for item in sidecar.get("invalid_citations", []):
            lines.append("- `%s` in `%s`" % (item.get("id"), item.get("section")))
    return "\n".join(lines).rstrip() + "\n"
def assemble(piece, sidecar, provenance, knobs):
    """Return document markdown and sidecar markdown."""
    return document(piece, provenance, knobs), sidecar_markdown(sidecar)
