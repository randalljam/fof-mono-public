#!/usr/bin/env python3
"""Eval checks for the access-cursor-chat formatter."""

import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "format_cursor_chat.py"
SPEC = importlib.util.spec_from_file_location("format_cursor_chat", SCRIPT_PATH)
FORMATTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FORMATTER)


class FormatCursorChatTests(unittest.TestCase):
    """Formatter behavior tests."""
    def _make_state_db(self, folder, composer_id, composer, bubbles):
        """Create a minimal Cursor state.vscdb fixture."""
        db_path = Path(folder) / "state.vscdb"
        connection = sqlite3.connect(db_path)
        connection.execute("CREATE TABLE cursorDiskKV (key TEXT PRIMARY KEY, value TEXT)")
        connection.execute(
            "INSERT INTO cursorDiskKV (key, value) VALUES (?, ?)",
            (f"composerData:{composer_id}", json.dumps(composer)),
        )
        for bubble_id, bubble in bubbles.items():
            connection.execute(
                "INSERT INTO cursorDiskKV (key, value) VALUES (?, ?)",
                (f"bubbleId:{composer_id}:{bubble_id}", json.dumps(bubble)),
            )
        connection.commit()
        connection.close()
        return db_path
    def test_jsonl_extracts_user_query_and_ai_marker(self):
        """JSONL input should unwrap visible user prompts and mark unknown models."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "chat.jsonl"
            rows = [
                {
                    "role": "user",
                    "message": {
                        "content": [
                            {
                                "type": "text",
                                "text": "<timestamp>Today</timestamp>\n<user_query>\nPlease explain this.\n</user_query>",
                            }
                        ]
                    },
                },
                {
                    "role": "assistant",
                    "message": {"content": [{"type": "text", "text": "Sure.\n\n[REDACTED]"}]},
                },
            ]
            path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            title, exported, turns = FORMATTER._parse_input(path)
            rendered = FORMATTER._render_markdown(path, turns, title=title, exported=exported, last_updated="2026-07-10_0706")
            self.assertIn("# User\nPlease explain this.", rendered)
            self.assertIn("# Cursor\nai: unknown\nSure.", rendered)
            self.assertNotIn("<user_query>", rendered)
            self.assertNotIn("[REDACTED]", rendered)
    def test_markdown_export_parses_cursor_blocks(self):
        """Cursor markdown exports should become heading-based markdown."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "export.md"
            path.write_text(
                "# Test Chat\n_Exported on 7/10/2026 at 07:18:17 PDT from Cursor (3.10.20)_\n\n---\n\n**User**\n\nHello\n\n---\n\n**Cursor**\n\nHi there\n",
                encoding="utf-8",
            )
            title, exported, turns = FORMATTER._parse_input(path, state_db_path=str(Path(folder) / "missing-state.vscdb"))
            rendered = FORMATTER._render_markdown(path, turns, title=title, exported=exported, last_updated="2026-07-10_0718")
            self.assertIn("title: Test Chat", rendered)
            self.assertIn("_Exported on 7/10/2026", rendered)
            self.assertIn("# User\nHello", rendered)
            self.assertIn("# Cursor\nai: unknown\nHi there", rendered)
    def test_jsonl_uses_state_db_model_metadata(self):
        """JSONL turns should pick up model names from Cursor state.vscdb."""
        composer_id = "3743ab2b-df4c-47be-8c1e-851f632f71f1"
        with tempfile.TemporaryDirectory() as folder:
            folder_path = Path(folder)
            transcript_dir = folder_path / composer_id
            transcript_dir.mkdir()
            transcript_path = transcript_dir / f"{composer_id}.jsonl"
            transcript_path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "role": "user",
                                "message": {
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": "<user_query>\nHello\n</user_query>",
                                        }
                                    ]
                                },
                            }
                        ),
                        json.dumps(
                            {
                                "role": "assistant",
                                "message": {"content": [{"type": "text", "text": "Hi there"}]},
                            }
                        ),
                    ]
                ),
                encoding="utf-8",
            )
            db_path = self._make_state_db(
                folder_path,
                composer_id,
                {
                    "name": "Test Chat",
                    "modelConfig": {"modelName": "gpt-5.5"},
                    "fullConversationHeadersOnly": [
                        {"bubbleId": "user-1", "type": 1},
                        {"bubbleId": "assistant-1", "type": 2},
                    ],
                },
                {
                    "user-1": {"type": 1, "text": "Hello"},
                    "assistant-1": {"type": 2, "modelInfo": {"modelName": "composer-2.5"}, "text": "Hi there"},
                },
            )
            title, exported, turns = FORMATTER._parse_input(transcript_path, state_db_path=str(db_path))
            rendered = FORMATTER._render_markdown(
                transcript_path,
                turns,
                title=title,
                exported=exported,
                last_updated="2026-07-10_0706",
            )
            self.assertEqual(title, "Test Chat")
            self.assertIn("# Cursor\nai: composer-2.5\nHi there", rendered)


if __name__ == "__main__":
    unittest.main()
