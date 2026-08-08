"""Tests for worktree-colors palette PNG generation."""

from pathlib import Path

from apps.holodeck import worktree_colors_palette as palette


def test_write_worktree_colors_palette_renders_png(tmp_path):
    colors = tmp_path / "apps/holodeck/worktree-colors.yaml"
    colors.parent.mkdir(parents=True)
    colors.write_text(
        "\n".join([
            'foreground: "#ffffff"',
            "rules:",
            "  - id: holodeck",
            "    name_contains: holodeck",
            '    background: "#2696d3"',
            "  - id: deutsch",
            "    name_contains: deutsch",
            '    background: "#c2185b"',
            "  - id: content-studio",
            "    name_contains: content-studio",
            '    background: "#d3872b"',
        ]) + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "apps/holodeck/data/worktree-colors.png"
    written = palette.write_worktree_colors_palette(tmp_path, output_path=out)
    assert written == out
    assert out.is_file()
    assert out.stat().st_size > 500
def test_swatch_foreground_uses_dark_text_on_light_backgrounds():
    assert palette.swatch_foreground("#d3872b", "#ffffff") == "#111111"
    assert palette.swatch_foreground("#22ae96", "#ffffff") == "#111111"
    assert palette.swatch_foreground("#800000", "#ffffff") == "#ffffff"
def test_rule_match_lines_formats_contains_all():
    lines = palette.rule_match_lines({
        "name_contains_all": ["website", "fof"],
        "id": "web-site-fof",
    })
    assert lines == ["name_contains_all: [website, fof]"]
