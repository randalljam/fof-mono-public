# Run with: .venv/bin/python3 -m pytest tests/test_content_redo.py -q
# Self-contained: engine tests stub all LLM calls; the committed deutsch graph is the fixture.

import json
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_TOOLS_DIR = os.path.join(REPO_ROOT, "apps", "deutsch", "content-tools")
REDO_APP_DIR = os.path.join(REPO_ROOT, "apps", "deutsch", "content-redo")
DGRAPH_APP_DIR = os.path.join(REPO_ROOT, "apps", "deutsch", "deutsch-graph")
for path in (CONTENT_TOOLS_DIR, REDO_APP_DIR, DGRAPH_APP_DIR):
    if path not in sys.path:
        sys.path.append(path)
from dgraph import grounding
from dredo import config
from dredo import engine
from dredo import render

GRAPH = grounding.load_graph()

### Helpers
def grounding_ids():
    """Return stable QA and concept ids from the committed graph."""
    qa_id = grounding.qa_grounding(GRAPH, ["topic:optimism"], per_topic=1)[0]["id"]
    concept_rows = grounding.concept_grounding(GRAPH, ["knowledge creation"], limit=1)
    if not concept_rows:
        raise AssertionError("no knowledge creation concept grounding")
    return qa_id, concept_rows[0]["id"]
def fixture_text():
    """Three-paragraph source with correction, reframe, and no-position cases."""
    return """Knowledge comes from induction over many observations, and the safest ideas are the ones confirmed again and again by data.

Children learn best when adults set the correct curriculum, enforce it firmly, and ask students to accept what established authorities already validated.

The fictional Northbridge goalkeeper was unbeatable in the 1987 neighborhood cup, which is the deepest sports truth in the town."""
def chat_sequence(responses):
    """LLM stub that returns JSON responses in order."""
    calls = []
    def fake_chat(messages, model=None, temperature=None):
        calls.append(messages)
        if not responses:
            raise AssertionError("unexpected chat call: " + messages[0]["content"][:120])
        return responses.pop(0)
    fake_chat.calls = calls
    return fake_chat
def pipeline_responses():
    """Responses for segment -> route -> judge -> plan -> rewrite."""
    qa_id, concept_id = grounding_ids()
    claims_json = {"claims": [
        {"text": "Knowledge comes from induction over many observations.", "turn_index": 0, "quote": "induction over many observations"},
        {"text": "Children learn best when adults enforce authority.", "turn_index": 1, "quote": "adults set the correct curriculum"},
        {"text": "The fictional Northbridge goalkeeper was unbeatable in 1987.", "turn_index": 2, "quote": "Northbridge goalkeeper was unbeatable"},
    ]}
    routes_json = {"routes": [
        {"id": "clm:001", "topics": ["optimism"], "concept_needles": ["knowledge creation"]},
        {"id": "clm:002", "topics": ["optimism"], "concept_needles": ["knowledge creation"]},
        {"id": "clm:003", "topics": [], "concept_needles": []},
    ]}
    judge_json = {"judgments": [
        {"id": "clm:001", "verdict": "diverge", "deutsch_position": "Deutsch rejects induction as the source of knowledge.", "citations": [qa_id, concept_id], "confidence": 0.9, "note": ""},
        {"id": "clm:002", "verdict": "diverge", "deutsch_position": "Deutsch treats criticism rather than authority as central to knowledge growth.", "citations": [concept_id], "confidence": 0.8, "note": ""},
    ]}
    plan_json = {"changes": [
        {"turn_index": 0, "change_type": "correct", "instruction": "Replace induction with conjecture and criticism.", "claim_ids": ["clm:001"], "citations": [qa_id, "qa:outside"]},
        {"turn_index": 1, "change_type": "reframe", "instruction": "Recast authority as criticism-friendly learning.", "claim_ids": ["clm:002"], "citations": [concept_id]},
        {"turn_index": 1, "change_type": "add", "instruction": "Add a brief note that problems can be improved by creating knowledge.", "claim_ids": ["clm:002"], "citations": [qa_id]},
        {"turn_index": 2, "change_type": "correct", "instruction": "Correct the sports claim as if Deutsch addressed it.", "claim_ids": ["clm:003"], "citations": ["qa:outside"]},
    ]}
    rewrite_json = {"rewrites": [
        {"turn_index": 0, "text": "Knowledge grows through bold guesses, criticism, and better explanations, not by simply collecting many observations."},
        {"turn_index": 1, "text": "Children learn best when adults and children can question ideas, improve explanations, and stop treating authority as final.",
         "additions": [{"plan_id": "chg:003", "text": "Problems can become soluble when people create the right knowledge."}]},
    ]}
    return [json.dumps(claims_json), json.dumps(routes_json), json.dumps(judge_json),
            json.dumps(plan_json), json.dumps(rewrite_json)], qa_id, concept_id
def run_fixture(degree=2, reading_level="adult"):
    """Run the full fixture pipeline."""
    responses, qa_id, concept_id = pipeline_responses()
    chat = chat_sequence(responses)
    result = engine.run(fixture_text(), "fixture.md", tone=3, degree=degree, reading_level=reading_level,
                        chat=chat, graph=GRAPH, generated_at="2026-07-12T13:10:00Z")
    return result, chat, qa_id, concept_id

### Engine
class TestContentRedoEngine(unittest.TestCase):
    def test_web_default_matches_runtime_default(self):
        path = os.path.join(REDO_APP_DIR, "web", "content-redo.html")
        with open(path, encoding="utf-8") as f:
            html = f.read()
        self.assertIn('<option value="%s" selected>' % config.DEFAULT_DEGREE, html)
    def test_end_to_end_degree_2_applies_correct_and_reframe_and_drops_add(self):
        result, chat, qa_id, concept_id = run_fixture(degree=2)
        self.assertEqual(result["summary"]["claims"], 3)
        self.assertEqual(result["summary"]["diverge"], 2)
        self.assertEqual(result["summary"]["no-position"], 1)
        self.assertEqual([row["change_type"] for row in result["plan"]["applied"]], ["correct", "reframe"])
        self.assertEqual(result["summary"]["changes"], 2)
        dropped_reasons = [row["reason"] for row in result["plan"]["dropped"]]
        self.assertIn("change_type not allowed by degree 2", dropped_reasons)
        self.assertIn("correct changes require at least one diverge claim", dropped_reasons)
        self.assertEqual(result["plan"]["applied"][0]["citations"], [qa_id])
        self.assertNotIn("qa:outside", result["plan"]["applied"][0]["citations"])
        self.assertEqual(result["plan"]["applied"][1]["citations"], [concept_id])
        self.assertEqual(result["diff"][2]["rewritten_text"], result["turns"][2]["text"])
        self.assertFalse(result["diff"][2]["changed"])
        self.assertIn(render.DISCLOSURE, result["markdown"])
        self.assertIn("generated-at: 2026-07-12T13:10:00Z", result["markdown"])
        self.assertIn("chg:001", result["change_list_markdown"])
        self.assertEqual(len([c for c in chat.calls if "Rewrite ONLY" in c[0]["content"]]), 1)
    def test_degree_1_filters_to_corrections_only(self):
        result, _chat, _qa_id, _concept_id = run_fixture(degree=1)
        self.assertEqual([row["change_type"] for row in result["plan"]["applied"]], ["correct"])
        self.assertEqual(len(result["changes"]), 1)
        self.assertEqual(result["changes"][0]["change_type"], "correct")
        self.assertFalse(result["diff"][1]["changed"])
    def test_degree_3_includes_marked_additions(self):
        result, _chat, _qa_id, _concept_id = run_fixture(degree=3)
        self.assertEqual([row["change_type"] for row in result["plan"]["applied"]], ["correct", "reframe", "add"])
        self.assertEqual(len(result["changes"]), 3)
        self.assertEqual(result["changes"][2]["change_type"], "add")
        self.assertEqual(result["diff"][1]["additions"][0]["text"], "Problems can become soluble when people create the right knowledge.")
        self.assertIn("> [added] Problems can become soluble", result["markdown"])
    def test_unchanged_turns_are_byte_identical_in_sidecar_and_markdown(self):
        result, _chat, _qa_id, _concept_id = run_fixture(degree=2)
        unchanged = result["diff"][2]
        self.assertEqual(unchanged["original_text"], unchanged["rewritten_text"])
        self.assertIn(unchanged["original_text"], result["markdown"])
    def test_length_guard_retries_once_then_skips_rewrite(self):
        turns = [{"speaker": None, "text": "One two three four five six seven eight nine ten.", "index": 0, "timestamp": None}]
        claims = [{"id": "clm:001", "turn_index": 0, "text": "Claim.", "verdict": "diverge",
                   "deutsch_position": "Position.", "citations": ["qa:ok"],
                   "grounding": [{"id": "qa:ok", "type": "qa", "brief": "Grounding."}]}]
        plan = [{"id": "chg:001", "turn_index": 0, "change_type": "correct", "instruction": "Correct it.",
                 "claim_ids": ["clm:001"], "citations": ["qa:ok"], "citation_details": [{"id": "qa:ok"}]}]
        overlong = " ".join(["too-long"] * 30)
        chat = chat_sequence([json.dumps({"rewrites": [{"turn_index": 0, "text": overlong}]}),
                              json.dumps({"rewrites": [{"turn_index": 0, "text": overlong}]})])
        diff, changes, skipped = engine.apply_rewrites(turns, claims, plan, 3, "adult", chat=chat)
        self.assertEqual(diff[0]["rewritten_text"], turns[0]["text"])
        self.assertEqual(changes, [])
        self.assertEqual(len(skipped), 1)
        self.assertIn("length guard", skipped[0]["reason"])
        self.assertEqual(len(chat.calls), 2)
    def test_citation_filtering_drops_outside_ids_in_plan(self):
        qa_id, _concept_id = grounding_ids()
        turns = [{"speaker": None, "text": "Source text.", "index": 0, "timestamp": None}]
        claims = [{"id": "clm:001", "turn_index": 0, "text": "Claim.", "verdict": "diverge",
                   "deutsch_position": "Position.", "citations": [qa_id],
                   "grounding": [{"id": qa_id, "type": "qa", "brief": "Grounding."}]}]
        rows = [{"turn_index": 0, "change_type": "correct", "instruction": "Correct it.",
                 "claim_ids": ["clm:001"], "citations": ["qa:outside", qa_id]}]
        plan = engine._sanitize_plan_rows(rows, turns, claims, 2, grounding.citation_index(GRAPH))
        self.assertEqual(plan["applied"][0]["citations"], [qa_id])
    def test_child_reading_level_passes_concept_definitions_into_rewrite_prompt(self):
        _result, chat, _qa_id, _concept_id = run_fixture(degree=2, reading_level="child")
        prompts = [call[0]["content"] for call in chat.calls]
        rewrite_prompt = [prompt for prompt in prompts if "Rewrite ONLY" in prompt][0]
        self.assertIn("CHILD CONCEPT DEFINITIONS JSON", rewrite_prompt)
        self.assertIn("Knowledge creation", rewrite_prompt)
        self.assertIn("kid-friendly", rewrite_prompt)
    def test_sidecar_diff_data_is_complete(self):
        result, _chat, _qa_id, _concept_id = run_fixture(degree=3)
        sidecar = result["sidecar"]
        for key in ("turns", "claims", "plan", "diff", "changes", "skipped_notes", "provenance", "knobs", "disclosure"):
            self.assertIn(key, sidecar)
        self.assertEqual(len(sidecar["diff"]), len(sidecar["turns"]))
        for row in sidecar["diff"]:
            self.assertIn("original_text", row)
            self.assertIn("rewritten_text", row)
            self.assertIn("changed", row)
            self.assertIn("change_ids", row)
        self.assertTrue(sidecar["changes"][0]["citation_details"])
    def test_run_from_request_happy_path_loads_sample(self):
        responses, _qa_id, _concept_id = pipeline_responses()
        responses[0] = json.dumps({"claims": [
            {"text": "Science works by collecting observations and inducing laws.", "turn_index": 0,
             "quote": "patiently collect observations, induce the laws from them"},
            {"text": "Serious theories should be treated as tentative.", "turn_index": 1,
             "quote": "Every serious theory should be treated as tentative"},
            {"text": "Milo Vance was the best fictional Northbridge goalkeeper.", "turn_index": 8,
             "quote": "the best fictional goalkeeper in the Northbridge amateur league was Milo Vance"},
        ]})
        responses.append(json.dumps({"rewrites": [{"turn_index": 0, "text": "Knowledge grows through bold guesses, criticism, and better explanations, not by simply collecting many observations and trusting repeated patterns."}]}))
        chat = chat_sequence(responses)
        old_chat = engine.llm_util.chat
        try:
            engine.llm_util.chat = chat
            state = {"graph": GRAPH, "citation_index": grounding.citation_index(GRAPH),
                     "repo_root": REPO_ROOT, "generated_at": "2026-07-12T13:10:00Z"}
            result = engine.run_from_request({"sample": "sample-discussion.md", "tone": 3, "degree": 2, "reading_level": "adult"}, state)
        finally:
            engine.llm_util.chat = old_chat
        self.assertEqual(result["source_name"], "sample-discussion.md")
        self.assertEqual(result["summary"]["changes"], 2)
        self.assertIn("markdown", result)
        self.assertIn("change_list_markdown", result)

if __name__ == "__main__":
    unittest.main()
