# Run with: .venv/bin/python3 -m pytest tests/test_deutsch_interject.py -q
# Self-contained: engine/server tests stub all LLM and engine calls; the committed deutsch graph is the fixture.

import json
import os
import shutil
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_TOOLS_DIR = os.path.join(REPO_ROOT, "apps", "deutsch", "content-tools")
INTERJECT_APP_DIR = os.path.join(REPO_ROOT, "apps", "deutsch", "deutsch-interject")
DGRAPH_APP_DIR = os.path.join(REPO_ROOT, "apps", "deutsch", "deutsch-graph")
for path in (CONTENT_TOOLS_DIR, INTERJECT_APP_DIR, DGRAPH_APP_DIR):
    if path not in sys.path:
        sys.path.append(path)
from ctools import config as ctools_config
from ctools import runs
from dgraph import grounding
from dinterject import engine

GRAPH = grounding.load_graph()

### Helpers
def optimism_quote():
    """Return one optimism QA id plus an eight-word verbatim span from its grounding."""
    items = grounding.qa_grounding(GRAPH, ["topic:optimism"], per_topic=3)
    for item in items:
        text = item.get("answer") or item.get("question") or item.get("brief") or ""
        words = text.split()
        if len(words) >= 8:
            return item["id"], " ".join(words[:8])
    raise AssertionError("no long optimism grounding text")
def fixture_text():
    """Small transcript with divergent, agreeing, and no-position claims."""
    return """[0:00:01] Host: Knowledge comes from induction over many observations.
[0:00:20] Guest: A good theory can still be mistaken and improved by criticism.
[0:00:45] Host: The fictional Northbridge goalkeeper was unbeatable in 1987.
"""
def chat_sequence(responses):
    """LLM stub that returns JSON responses in order."""
    calls = []
    def fake_chat(messages, model=None, temperature=None):
        calls.append(messages)
        if not responses:
            raise AssertionError("unexpected chat call: " + messages[0]["content"][:80])
        return responses.pop(0)
    fake_chat.calls = calls
    return fake_chat
def pipeline_responses(include_agreement=False, outside_citation=False):
    """Responses for segment -> route -> judge -> interject."""
    qa_id, quote = optimism_quote()
    claims_json = {"claims": [
        {"text": "Knowledge comes from induction over many observations.", "turn_index": 0, "quote": "induction over many observations"},
        {"text": "Good theories can be mistaken and improved by criticism.", "turn_index": 1, "quote": "mistaken and improved by criticism"},
        {"text": "The fictional Northbridge goalkeeper was unbeatable in 1987.", "turn_index": 2, "quote": "Northbridge goalkeeper was unbeatable"},
    ]}
    routes_json = {"routes": [
        {"id": "clm:001", "topics": ["optimism"], "concept_needles": []},
        {"id": "clm:002", "topics": ["optimism"], "concept_needles": []},
        {"id": "clm:003", "topics": [], "concept_needles": []},
    ]}
    judge_json = {"judgments": [
        {"id": "clm:001", "verdict": "diverge", "deutsch_position": "Deutsch rejects induction as the source of knowledge.", "citations": [qa_id], "confidence": 0.9, "note": ""},
        {"id": "clm:002", "verdict": "agree", "deutsch_position": "Deutsch treats fallibility and criticism as central.", "citations": [qa_id], "confidence": 0.8, "note": ""},
    ]}
    interjections = [{"claim_id": "clm:001", "text": "Deutsch would push back: \"%s\"." % quote,
                      "citations": [qa_id, "qa:outside"] if outside_citation else [qa_id]}]
    if include_agreement:
        interjections.append({"claim_id": "clm:002", "text": "Deutsch would likely agree: \"%s\"." % quote,
                              "citations": [qa_id]})
    return [json.dumps(claims_json), json.dumps(routes_json), json.dumps(judge_json),
            json.dumps({"interjections": interjections})], qa_id

### Engine
class TestDeutschInterjectEngine(unittest.TestCase):
    def test_end_to_end_inserts_virtual_turn_and_keeps_provenance(self):
        responses, qa_id = pipeline_responses(outside_citation=True)
        result = engine.run(fixture_text(), "fixture.md", tone=3, fidelity="quote", include_agreements=False,
                            chat=chat_sequence(responses), graph=GRAPH, generated_at="2026-07-12T13:10:00Z")
        self.assertEqual(result["summary"]["claims"], 3)
        self.assertEqual(result["summary"]["diverge"], 1)
        self.assertEqual(result["summary"]["agree"], 1)
        self.assertEqual(result["summary"]["no-position"], 1)
        self.assertEqual(result["summary"]["interjections"], 1)
        md = result["markdown"]
        self.assertIn("SYNTHETIC-CONTENT:", md)
        self.assertIn("generated-at: 2026-07-12T13:10:00Z", md)
        self.assertIn("**David Deutsch (virtual):**", md)
        self.assertLess(md.index("**Host:** Knowledge comes from"), md.index("**David Deutsch (virtual):**"))
        self.assertLess(md.index("**David Deutsch (virtual):**"), md.index("**Guest:** A good theory"))
        self.assertEqual(result["interjections"][0]["citations"], [qa_id])
        self.assertEqual(result["sidecar"]["provenance"]["source_name"], "fixture.md")
        skipped = [row for row in result["sidecar"]["skipped"] if row.get("verdict") == "no-position"]
        self.assertEqual(len(skipped), 1)
        self.assertIn("no recorded position", skipped[0]["reason"])
    def test_include_agreements_adds_agree_interjection(self):
        responses, qa_id = pipeline_responses(include_agreement=True)
        result = engine.run(fixture_text(), "fixture.md", tone=3, fidelity="quote", include_agreements=True,
                            chat=chat_sequence(responses), graph=GRAPH, generated_at="now")
        self.assertEqual(len(result["interjections"]), 2)
        self.assertEqual([item["claim_id"] for item in result["interjections"]], ["clm:001", "clm:002"])
        self.assertEqual(result["interjections"][1]["citations"], [qa_id])
    def test_quote_verification_drops_fabricated_quote_after_failed_regeneration(self):
        claim = {"id": "clm:bad", "turn_index": 0, "verdict": "diverge", "text": "Bad quote.",
                 "citations": ["qa:ok"], "grounding": [{"id": "qa:ok", "answer": "Real source text has grounded words that appear here for testing."}]}
        draft = {"claim_id": "clm:bad", "turn_index": 0, "verdict": "diverge",
                 "text": "Deutsch says \"This fabricated quote has many words not found in sources\".", "citations": ["qa:ok"]}
        regen = json.dumps({"interjection": {"claim_id": "clm:bad", "text": "Still bad: \"This fabricated quote has many words not found in sources\".", "citations": ["qa:ok"]}})
        notes = []
        result = engine._verify_or_regenerate(draft, claim, 3, "quote", None, chat_sequence([regen]), notes)
        self.assertIsNone(result)
        self.assertIn("Dropped interjection", notes[0]["note"])
    def test_citation_filtering_drops_outside_ids(self):
        claim = {"id": "clm:001", "turn_index": 0, "verdict": "diverge", "text": "Claim.",
                 "citations": ["qa:allowed"], "grounding": [{"id": "qa:allowed", "answer": "Source answer."}]}
        row = {"claim_id": "clm:001", "text": "Text.", "citations": ["qa:outside", "qa:allowed"]}
        self.assertEqual(engine._sanitize_interjection(row, claim)["citations"], ["qa:allowed"])
    def test_interjection_without_grounded_citation_is_dropped(self):
        claim = {"id": "clm:001", "turn_index": 0, "verdict": "diverge", "text": "Claim.",
                 "citations": [], "grounding": [{"id": "qa:allowed", "answer": "Source answer."}]}
        row = {"claim_id": "clm:001", "text": "Text.", "citations": ["qa:outside"]}
        self.assertIsNone(engine._sanitize_interjection(row, claim))
    def test_no_position_is_listed_but_not_interjected(self):
        responses, _ = pipeline_responses()
        result = engine.run(fixture_text(), "fixture.md", tone=3, fidelity="quote", include_agreements=False,
                            chat=chat_sequence(responses), graph=GRAPH, generated_at="now")
        self.assertNotIn("clm:003", [item["claim_id"] for item in result["interjections"]])
        self.assertIn("clm:003", [row["claim_id"] for row in result["skipped"] if row.get("verdict") == "no-position"])

### Runs
class TestRunStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.original = ctools_config.TOOLS["interject"]["app_dir"]
        ctools_config.TOOLS["interject"]["app_dir"] = self.tmp
    def tearDown(self):
        ctools_config.TOOLS["interject"]["app_dir"] = self.original
        shutil.rmtree(self.tmp)
    def test_save_list_load_delete_round_trip(self):
        first = runs.save_run("interject", {"source_name": "Sample Discussion", "claims": [1], "interjections": [1, 2], "knobs": {"tone": 3, "fidelity": "quote"}})
        second = runs.save_run("interject", {"source_name": "Another Run", "claims": [], "interjections": [], "knobs": {"tone": 4, "fidelity": "voice"}})
        self.assertTrue(first["run_id"].startswith("run-0001-sample-discussion"))
        self.assertTrue(second["run_id"].startswith("run-0002-another-run"))
        listed = runs.list_runs("interject")
        self.assertEqual([row["run_id"] for row in listed], [second["run_id"], first["run_id"]])
        self.assertEqual(runs.load_run("interject", first["run_id"])["source_name"], "Sample Discussion")
        self.assertTrue(runs.delete_run("interject", first["run_id"]))
        self.assertIsNone(runs.load_run("interject", first["run_id"]))
        self.assertFalse(runs.delete_run("interject", first["run_id"]))

### Server
class TestContentToolsServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from ctools import server
        cls.server = server
        cls.original_token = server.SESSION_TOKEN
        cls.original_import = server._import_engine
        cls.original_save = server.runs.save_run
        server.SESSION_TOKEN = "test-token"
        class FakeEngine:
            def run_from_request(self, payload, state):
                return {"source_name": payload.get("source_name", "stub"), "generated_at": state.get("generated_at"),
                        "turns": [], "claims": [], "interjections": [], "skipped": [], "markdown": "md",
                        "sidecar": {"ok": True}, "knobs": {"tone": 3, "fidelity": "quote"}, "summary": {"claims": 0, "diverge": 0, "agree": 0, "no-position": 0, "interjections": 0}}
        server._import_engine = lambda tool: FakeEngine()
        server.runs.save_run = lambda tool, run: dict(run, run_id="run-0001-stub")
        cls.client = TestClient(server.app)
        cls.client.__enter__()
        cls.headers = {"X-CT-Token": "test-token"}
    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        cls.server.SESSION_TOKEN = cls.original_token
        cls.server._import_engine = cls.original_import
        cls.server.runs.save_run = cls.original_save
    def test_api_requires_token(self):
        self.assertEqual(self.client.get("/api/state").status_code, 401)
        self.assertEqual(self.client.get("/api/state", headers={"X-CT-Token": "wrong"}).status_code, 401)
    def test_state_ok(self):
        state = self.client.get("/api/state", headers=self.headers).json()
        self.assertEqual(len(state["tones"]), 5)
        self.assertIn("interject", [row["key"] for row in state["tools"]])
        self.assertIn("nodes", state["graph_stats"])
    def test_post_interject_run_uses_stub_engine(self):
        res = self.client.post("/api/interject/run", headers=self.headers,
                               json={"text": "Host: text", "source_name": "stub"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["run_id"], "run-0001-stub")
        self.assertEqual(res.json()["source_name"], "stub")

if __name__ == "__main__":
    unittest.main()
