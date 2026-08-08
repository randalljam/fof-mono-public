"""Tests for consumer chat markdown skill."""

import json
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from normalize import parse_chatgpt_markdown_file, parse_claude_json_file, parse_numbered_markdown
from render_md import render_combined, render_single, write_outputs
from consumer_chat_md import collect_threads, build_parser

FIXTURES = Path(__file__).parent / "fixtures"
def test_parse_numbered_markdown():
    text = (FIXTURES / "sample_chatgpt.md").read_text(encoding="utf-8")
    title, date_str, source_ref, messages = parse_numbered_markdown(text)
    assert title == "Hermes agent setup options"
    assert date_str == "2026-06-05"
    assert "chatgpt.com/share" in source_ref
    assert len(messages) == 4
    assert messages[0]["role"] == "user"
def test_parse_chatgpt_markdown_file():
    thread = parse_chatgpt_markdown_file(FIXTURES / "sample_chatgpt.md")
    assert thread["source"] == "chatgpt"
    assert thread["title"] == "Hermes agent setup options"
    assert len(thread["messages"]) == 4
def test_parse_claude_json_file_with_select():
    threads = parse_claude_json_file(FIXTURES / "sample_claude.json", select="speech recognition")
    assert len(threads) == 1
    assert threads[0]["source"] == "claude"
    assert "Speech recognition" in threads[0]["title"]
    assert len(threads[0]["messages"]) == 4
def test_parse_claude_json_select_miss():
    with pytest.raises(ValueError):
        parse_claude_json_file(FIXTURES / "sample_claude.json", select="nonexistent-topic")
def test_render_single_contains_sections():
    thread = parse_chatgpt_markdown_file(FIXTURES / "sample_chatgpt.md")
    rendered = render_single(thread)
    assert rendered.startswith("# 2026-06-05 — Hermes agent setup options")
    assert "## 1. User" in rendered
    assert "## 1. Assistant" in rendered
    assert "## 2. User" in rendered
def test_render_combined():
    chatgpt = parse_chatgpt_markdown_file(FIXTURES / "sample_chatgpt.md")
    claude = parse_claude_json_file(FIXTURES / "sample_claude.json")[0]
    combined = render_combined([chatgpt, claude], topic="speech-recognition-benchmarks")
    assert "# speech-recognition-benchmarks" in combined
    assert "## ChatGPT —" in combined
    assert "## Claude —" in combined
def test_write_outputs(tmp_path):
    chatgpt = parse_chatgpt_markdown_file(FIXTURES / "sample_chatgpt.md")
    claude = parse_claude_json_file(FIXTURES / "sample_claude.json")[0]
    written = write_outputs([chatgpt, claude], tmp_path, combine=True, topic="asr-benchmarks")
    assert len(written) == 3
    assert any(path.endswith("_combined.md") for path in written)
    for path in written:
        assert Path(path).exists()
        assert Path(path).read_text(encoding="utf-8").strip()
def test_cli_collect_threads(tmp_path, monkeypatch):
    parser = build_parser()
    args = parser.parse_args([
        "--chatgpt-md", str(FIXTURES / "sample_chatgpt.md"),
        "--claude-json", str(FIXTURES / "sample_claude.json"),
        "--out-dir", str(tmp_path),
        "--combine",
        "--topic", "demo-combined",
    ])
    threads = collect_threads(args)
    assert len(threads) == 2
    written = write_outputs(threads, args.out_dir, combine=args.combine, topic=args.topic)
    assert len(written) == 3
