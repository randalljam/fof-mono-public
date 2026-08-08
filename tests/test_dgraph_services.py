# Run with: .venv/bin/python3 -m pytest tests/test_dgraph_services.py -q
# Self-contained: LLM calls are stubbed; the committed deutsch graph is the fixture.

import json
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DGRAPH_APP_DIR = os.path.join(REPO_ROOT, "apps", "deutsch", "deutsch-graph")
WVMIRROR_APP_DIR = os.path.join(REPO_ROOT, "apps", "deutsch", "worldview-mirror")
for path in (DGRAPH_APP_DIR, WVMIRROR_APP_DIR):
    if path not in sys.path:
        sys.path.append(path)
from dgraph import claims, divergence, grounding
from wvmirror import graph_access

GRAPH = grounding.load_graph()
CATALOG = grounding.topic_catalog(GRAPH)

### Helpers
def topic_by_label(label):
    """Catalog topic row by exact label."""
    return [topic for topic in CATALOG["topics"] if topic["label"] == label][0]

### Content parsing
class TestParseContent(unittest.TestCase):
    def test_speaker_transcript_timestamps_bold_and_heading_skip(self):
        text = """file: x.md
title: ignored

# Ignored Heading
[0:01:02] Alice: Knowledge grows by conjecture.
(0:02:03) **Bob:** Problems are soluble.
0:03:04 Cara: The future is open.
and mistakes are correctable.
"""
        turns = claims.parse_content(text)
        self.assertEqual([t["speaker"] for t in turns], ["Alice", "Bob", "Cara"])
        self.assertEqual([t["timestamp"] for t in turns], ["0:01:02", "0:02:03", "0:03:04"])
        self.assertEqual(turns[2]["text"], "The future is open. and mistakes are correctable.")
        self.assertNotIn("Ignored", " ".join(t["text"] for t in turns))
    def test_plain_prose_paragraphs_and_heading_skip(self):
        text = """# Title

First paragraph line one
continues here.

## Section
Second paragraph.
"""
        turns = claims.parse_content(text)
        self.assertEqual(len(turns), 2)
        self.assertEqual([t["speaker"] for t in turns], [None, None])
        self.assertEqual([t["index"] for t in turns], [0, 1])
        self.assertEqual(turns[0]["text"], "First paragraph line one continues here.")

### Claim segmentation
class TestSegmentClaims(unittest.TestCase):
    def test_segment_claims_fenced_json_and_malformed_rows(self):
        turns = [{"speaker": "Alice", "text": "We can solve problems.", "index": 0, "timestamp": "0:01"}]
        def fake_chat(messages, model=None, temperature=None):
            return """```json
{"claims": ["bad", {"text": "Missing turn", "quote": "x"}, {"text": "Bad turn", "turn_index": 99, "quote": "x"}, {"text": "Missing quote", "turn_index": 0}, {"text": "Empty quote", "turn_index": 0, "quote": "  "}, {"text": "Fabricated provenance", "turn_index": 0, "quote": "never appeared"}, {"claim": "People can solve problems.", "turn_index": 0, "quote": "solve problems"}]}
```"""
        result = claims.segment_claims(turns, chat=fake_chat)
        self.assertEqual(result, [{"id": "clm:001", "text": "People can solve problems.",
                                   "speaker": "Alice", "turn_index": 0, "quote": "solve problems"}])
    def test_segment_claims_chunks_long_input(self):
        turns = [{"speaker": None, "text": "a" * 4000, "index": 0, "timestamp": None},
                 {"speaker": None, "text": "b" * 4000, "index": 1, "timestamp": None}]
        calls = []
        def fake_chat(messages, model=None, temperature=None):
            calls.append(messages)
            return json.dumps({"claims": []})
        self.assertEqual(claims.segment_claims(turns, chat=fake_chat), [])
        self.assertEqual(len(calls), 2)

### Divergence routing and judging
class TestDivergenceServices(unittest.TestCase):
    def test_route_claims_maps_labels_and_drops_unknowns(self):
        topic = topic_by_label("optimism")
        external_claims = [{"id": "clm:001", "text": "Problems can be solved.", "quote": "Problems can be solved."}]
        def fake_chat(messages, model=None, temperature=None):
            return json.dumps({"routes": [{"id": "clm:001", "topics": ["optimism", "not-a-topic"],
                                           "concept_needles": ["optimism", "wealth", "extra"]}]})
        result = divergence.route_claims(external_claims, CATALOG, chat=fake_chat)
        self.assertEqual(result, [{"topics": [topic["id"]], "concept_needles": ["optimism", "wealth"]}])
    def test_judge_claims_filters_citations_and_sanitizes(self):
        claim = {"id": "clm:001", "text": "A claim.", "quote": "A claim.",
                 "grounding": [{"id": "qa:grounded", "question": "Q?", "answer": "A."}]}
        def fake_chat(messages, model=None, temperature=None):
            return json.dumps({"judgments": [{"id": "clm:001", "verdict": "maybe",
                                              "deutsch_position": "One. Two. Three.",
                                              "citations": ["qa:grounded", "qa:outside"],
                                              "confidence": 3.5, "note": 7}]})
        result = divergence.judge_claims([claim], chat=fake_chat)
        self.assertEqual(result[0]["verdict"], "no-position")
        self.assertEqual(result[0]["citations"], ["qa:grounded"])
        self.assertEqual(result[0]["confidence"], 1.0)
        self.assertEqual(result[0]["deutsch_position"], "One. Two.")
        self.assertEqual(result[0]["note"], "")
    def test_judge_claims_downgrades_unsupported_verdict(self):
        claim = {"id": "clm:001", "text": "A claim.", "quote": "A claim.",
                 "grounding": [{"id": "qa:grounded", "question": "Q?", "answer": "A."}]}
        responses = [
            {"id": "clm:001", "verdict": "diverge", "deutsch_position": "A position.",
             "citations": ["qa:outside"], "confidence": 0.9},
            {"id": "clm:001", "verdict": "agree", "deutsch_position": "",
             "citations": ["qa:grounded"], "confidence": 0.8},
        ]
        for response in responses:
            def fake_chat(messages, model=None, temperature=None):
                return json.dumps({"judgments": [response]})
            result = divergence.judge_claims([claim], chat=fake_chat)
            self.assertEqual(result[0]["verdict"], "no-position")
            self.assertEqual(result[0]["deutsch_position"], "")
            self.assertEqual(result[0]["citations"], [])
            self.assertEqual(result[0]["confidence"], 0.0)
            self.assertIn("Downgraded", result[0]["note"])
    def test_detect_routes_grounds_judges_and_short_circuits_unroutable(self):
        qa_id = grounding.qa_grounding(GRAPH, ["topic:optimism"], per_topic=1)[0]["id"]
        external_claims = [
            {"id": "clm:001", "text": "Problems can be solved.", "quote": "Problems can be solved."},
            {"id": "clm:002", "text": "The cafe opens at seven.", "quote": "opens at seven"},
        ]
        judge_calls = []
        def fake_chat(messages, model=None, temperature=None):
            prompt = messages[0]["content"]
            if "Route each external claim" in prompt:
                return json.dumps({"routes": [{"id": "clm:001", "topics": ["optimism"], "concept_needles": []},
                                               {"id": "clm:002", "topics": [], "concept_needles": []}]})
            if "Judge each external claim" in prompt:
                judge_calls.append(prompt)
                self.assertIn("clm:001", prompt)
                self.assertNotIn("clm:002", prompt)
                return json.dumps({"judgments": [{"id": "clm:001", "verdict": "diverge",
                                                  "deutsch_position": "Deutsch has a grounded position.",
                                                  "citations": [qa_id], "confidence": 0.8, "note": "grounded"}]})
            raise AssertionError("unexpected prompt")
        result = divergence.detect(GRAPH, external_claims, chat=fake_chat, per_topic=1)
        self.assertEqual(result[0]["topics"], ["topic:optimism"])
        self.assertEqual(result[0]["verdict"], "diverge")
        self.assertEqual(result[0]["citations"], [qa_id])
        self.assertEqual(result[1]["verdict"], "no-position")
        self.assertEqual(result[1]["citations"], [])
        self.assertEqual(len(judge_calls), 1)

### Grounding delegation
class TestGroundingDelegation(unittest.TestCase):
    def test_dgraph_and_wvmirror_build_grounding_match(self):
        direct = grounding.build_grounding(GRAPH, ["topic:optimism"], [], ["optimism"])
        delegated = graph_access.build_grounding(GRAPH, ["topic:optimism"], [], ["optimism"])
        self.assertEqual(direct, delegated)
        self.assertTrue(direct["qa"])
        self.assertTrue(direct["concepts"])
        if grounding.corpus_available():
            self.assertTrue(any(item["answer"] for item in direct["qa"]))
        else:
            self.assertTrue(all("answer" in item for item in direct["qa"]))
    def test_wvmirror_delegation_smoke(self):
        package = graph_access.build_grounding(GRAPH, ["topic:optimism"], [], [])
        self.assertIn("qa", package)
        self.assertIn("claims", package)
        self.assertIn("concepts", package)
        self.assertEqual(package["corpus_available"], graph_access.corpus_available())

if __name__ == "__main__":
    unittest.main()
