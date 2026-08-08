# Run with: .venv/bin/python3 -m pytest tests/test_content_forge.py -q
# Self-contained: engine tests stub all LLM calls and use the committed deutsch graph fixture.

import json
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_TOOLS_DIR = os.path.join(REPO_ROOT, "apps", "deutsch", "content-tools")
FORGE_APP_DIR = os.path.join(REPO_ROOT, "apps", "deutsch", "content-forge")
DGRAPH_APP_DIR = os.path.join(REPO_ROOT, "apps", "deutsch", "deutsch-graph")
for path in (CONTENT_TOOLS_DIR, FORGE_APP_DIR, DGRAPH_APP_DIR):
    if path not in sys.path:
        sys.path.append(path)
from dgraph import grounding
from dforge import engine

GRAPH = grounding.load_graph()
CITE_INDEX = grounding.citation_index(GRAPH)

### Helpers
def optimism_qa_id():
    """Return one committed optimism QA node id."""
    return grounding.qa_grounding(GRAPH, ["topic:optimism"], per_topic=1)[0]["id"]
def chat_sequence(responses):
    """LLM stub that returns responses in order and captures prompts."""
    calls = []
    def fake_chat(messages, model=None, temperature=None):
        calls.append(messages)
        if not responses:
            raise AssertionError("unexpected chat call: " + messages[0]["content"][:80])
        return responses.pop(0)
    fake_chat.calls = calls
    return fake_chat
def first_route(*topics):
    """Shared route_claims JSON response."""
    return json.dumps({"routes": [{"id": "forge:description", "topics": list(topics) or ["optimism"],
                                   "concept_needles": ["optimism"]}]})
def fallback_route():
    """Forge wider routing JSON response."""
    return json.dumps({"topics": ["optimism", "knowledge", "progress", "explanation", "problems"],
                       "categories": ["Principle of Optimism", "Explanatory Knowledge"],
                       "concept_needles": ["optimism", "knowledge", "wealth"]})
def basic_piece():
    """Two-section draft with one valid and one invalid cite."""
    qa_id = optimism_qa_id()
    return "## Grounded Thesis\nProblems can be approached through new knowledge [%s] [qa:not-real:000].\n\n## Review Gap\nThe selected graph sources do not cover the requested classroom activity details." % qa_id
def route_and_piece(piece=None):
    """Standard route + fallback + generation responses."""
    return [first_route("optimism"), fallback_route(), piece or basic_piece()]

### Engine
class TestContentForgeEngine(unittest.TestCase):
    def test_end_to_end_sections_citations_invalid_strip_and_ungrounded_flag(self):
        chat = chat_sequence(route_and_piece())
        result = engine.run("Make a lesson about optimism.", fmt="essay", length="short", tone=3,
                            chat=chat, graph=GRAPH, citation_index=CITE_INDEX, generated_at="2026-07-12T13:25:00Z")
        self.assertEqual(len(chat.calls), 3)
        self.assertNotIn("[qa:not-real:000]", result["markdown"])
        self.assertEqual([s["heading"] for s in result["sidecar"]["sections"]], ["Grounded Thesis", "Review Gap"])
        self.assertTrue(result["sidecar"]["sections"][0]["grounded"])
        self.assertFalse(result["sidecar"]["sections"][1]["grounded"])
        self.assertEqual(result["sidecar"]["sections"][0]["cited_node_ids"], [optimism_qa_id()])
        self.assertEqual(result["sidecar"]["sections"][0]["citations"][0]["id"], optimism_qa_id())
        self.assertIn("youtube_ts_url", result["sidecar"]["sections"][0]["citations"][0])
        self.assertEqual(result["sidecar"]["invalid_citations"], [{"section": "Grounded Thesis", "id": "qa:not-real:000"}])
        self.assertTrue(result["package_manifest"]["retrieved_but_uncited"])
    def test_routing_wrapper_uses_fallback_when_shared_router_is_too_narrow(self):
        chat = chat_sequence([first_route("optimism", "knowledge", "progress"), fallback_route()])
        routing = engine.route_description("Make an essay about optimism and knowledge.", GRAPH, chat=chat)
        self.assertEqual(len(chat.calls), 2)
        self.assertTrue(routing["fallback_used"])
        self.assertEqual(routing["router_calls"], 2)
        self.assertGreaterEqual(len(routing["topics"]), 4)
        self.assertIn("Principle of Optimism", routing["category_labels"])
    def test_length_retry_path(self):
        qa_id = optimism_qa_id()
        long_piece = "## Long Draft\n" + ("word " * 650) + "[%s]" % qa_id
        short_piece = "## Short Draft\nTight grounded text [%s]." % qa_id
        chat = chat_sequence(route_and_piece(long_piece) + [short_piece])
        result = engine.run("Make a short essay about optimism.", fmt="essay", length="short", tone=3,
                            chat=chat, graph=GRAPH, citation_index=CITE_INDEX, generated_at="now")
        self.assertEqual(len(chat.calls), 4)
        self.assertEqual(result["piece_markdown"], short_piece)
        self.assertEqual(result["notes"][0]["type"], "length")
        self.assertIn("Regenerated once", result["notes"][0]["note"])
    def test_format_templates_reach_generation_prompt(self):
        lesson_chat = chat_sequence(route_and_piece("## Lesson\nGrounded [%s]." % optimism_qa_id()))
        engine.run("Teach optimism.", fmt="lesson", length="short", tone=3,
                   chat=lesson_chat, graph=GRAPH, citation_index=CITE_INDEX, generated_at="now")
        lesson_prompt = lesson_chat.calls[2][0]["content"]
        self.assertIn("objectives, explanation, examples, and questions-to-explore", lesson_prompt)
        dialogue_chat = chat_sequence(route_and_piece("## Dialogue\nAlex: Grounded [%s]." % optimism_qa_id()))
        engine.run("Dialogue about optimism.", fmt="dialogue", length="short", tone=3,
                   chat=dialogue_chat, graph=GRAPH, citation_index=CITE_INDEX, generated_at="now")
        dialogue_prompt = dialogue_chat.calls[2][0]["content"]
        self.assertIn("two named fictional speakers", dialogue_prompt)
        self.assertIn("Do not label either speaker as David Deutsch", dialogue_prompt)
    def test_provenance_disclosure_and_run_from_request(self):
        chat = chat_sequence(route_and_piece())
        result = engine.run_from_request({"description": "Make an essay about optimism.", "format": "essay",
                                          "length": "short", "tone": 3},
                                         {"graph": GRAPH, "citation_index": CITE_INDEX,
                                          "repo_root": REPO_ROOT, "generated_at": "2026-07-12T13:25:00Z",
                                          "chat": chat})
        self.assertIn("description: Make an essay about optimism.", result["markdown"])
        self.assertIn("AI-GENERATED: This piece was generated from cited deutsch-graph sources", result["markdown"])
        self.assertIn("generated-at: 2026-07-12T13:25:00Z", result["markdown"])
    def test_sidecar_coverage_stats_are_correct(self):
        result = engine.run("Make a lesson about optimism.", fmt="lesson", length="short", tone=3,
                            chat=chat_sequence(route_and_piece()), graph=GRAPH,
                            citation_index=CITE_INDEX, generated_at="now")
        self.assertEqual(result["coverage"]["n_sections"], 2)
        self.assertEqual(result["coverage"]["n_grounded"], 1)
        self.assertEqual(result["coverage"]["n_ungrounded"], 1)
        self.assertEqual(result["coverage"]["n_citations"], 1)
        self.assertEqual(result["coverage"]["n_invalid"], 1)

if __name__ == "__main__":
    unittest.main()
