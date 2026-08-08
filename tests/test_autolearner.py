# Run tests with: .venv/bin/python3 -m unittest tests.test_autolearner -v
# Covers the autolearner pure logic (pacing metrics, mastery scheduling) and the
# Flask API end-to-end with the pipeline services patched out (no network, no keys).

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.autolearner import mastery, pacing

CONCEPTS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "apps", "autolearner", "content", "concepts.json")


### Helpers
def make_words(spec):
    """Build a word list from (word, start, end) tuples."""
    return [{"word": w, "start": s, "end": e} for w, s, e in spec]
def make_dg_response(words, transcript=None):
    """Build a minimal Deepgram-shaped response dict."""
    if transcript is None:
        transcript = " ".join(w["word"] for w in words)
    dg_words = [{"word": w["word"], "punctuated_word": w["word"], "start": w["start"], "end": w["end"]} for w in words]
    return {"results": {"channels": [{"alternatives": [{"transcript": transcript, "words": dg_words}]}]}}
def attempt(exercise_id, score, gaps=None):
    """Build an attempt dict for record_attempt."""
    return {"exercise_id": exercise_id, "mastery_score": score, "gaps": gaps or []}

class TestPacing(unittest.TestCase):
    def test_extract_words_and_transcript(self):
        dg = make_dg_response(make_words([("hello", 1.0, 1.4), ("world", 1.5, 1.9)]))
        words = pacing.extract_words(dg)
        self.assertEqual(len(words), 2)
        self.assertEqual(words[0]["word"], "hello")
        self.assertEqual(pacing.extract_transcript(dg), "hello world")
    def test_extract_words_malformed_response(self):
        self.assertEqual(pacing.extract_words({}), [])
        self.assertEqual(pacing.extract_words(None), [])
        self.assertEqual(pacing.extract_transcript({}), "")
    def test_metrics_empty(self):
        m = pacing.compute_pacing_metrics([])
        self.assertEqual(m["total_words"], 0)
        self.assertEqual(m["pause_count"], 0)
    def test_metrics_detects_pauses(self):
        words = make_words([("a", 1.0, 1.3), ("b", 1.5, 1.8), ("c", 7.0, 7.3), ("d", 7.5, 7.8)])
        m = pacing.compute_pacing_metrics(words, pause_threshold=3.0)
        self.assertEqual(m["pause_count"], 1)
        self.assertAlmostEqual(m["longest_pause_s"], 5.2, places=1)
        self.assertEqual(m["pauses"][0]["after_word"], "b")
        self.assertEqual(m["pauses"][0]["before_word"], "c")
        self.assertEqual(m["time_to_first_word_s"], 1.0)
        self.assertEqual(m["total_words"], 4)
    def test_metrics_counts_fillers(self):
        words = make_words([("um", 1.0, 1.2), ("the", 1.3, 1.5), ("uh,", 1.6, 1.8), ("slope", 1.9, 2.2)])
        m = pacing.compute_pacing_metrics(words)
        self.assertEqual(m["filler_count"], 2)
    def test_timeline_buckets_and_silence(self):
        words = make_words([("start", 1.0, 1.4), ("end", 32.0, 32.4)])
        lines = pacing.build_timeline(words, bucket_seconds=15)
        self.assertEqual(len(lines), 3)
        self.assertIn("start", lines[0])
        self.assertIn("(silence)", lines[1])
        self.assertIn("end", lines[2])
    def test_pacing_report_text(self):
        words = make_words([("a", 1.0, 1.3), ("b", 9.0, 9.3)])
        m = pacing.compute_pacing_metrics(words)
        text = pacing.pacing_report_text(m, pacing.build_timeline(words))
        self.assertIn("PACING METRICS", text)
        self.assertIn("TIMELINE", text)

class TestMastery(unittest.TestCase):
    def setUp(self):
        self.concepts = mastery.load_concepts(CONCEPTS_PATH)
        self.session = mastery.new_session("test unit")
        self.ids = [c["id"] for c in self.concepts["concepts"]]
    def test_catalog_shape(self):
        self.assertGreaterEqual(len(self.ids), 10)
        for c in self.concepts["concepts"]:
            self.assertGreaterEqual(len(c["exercises"]), 3)
            for ex in c["exercises"]:
                self.assertIn("prompt", ex)
                self.assertIn("reference_solution", ex)
    def test_record_attempt_and_scores(self):
        cid = self.ids[0]
        mastery.record_attempt(self.session, cid, attempt("x-1", 70, [{"description": "g1", "severity": "major"}]))
        self.assertEqual(mastery.latest_score(self.session, cid), 70)
        self.assertFalse(mastery.is_mastered(self.session, cid))
        mastery.record_attempt(self.session, cid, attempt("x-2", 90))
        self.assertEqual(mastery.latest_score(self.session, cid), 90)
        self.assertTrue(mastery.is_mastered(self.session, cid))
        self.assertEqual(mastery.open_gaps(self.session, cid), [])
    def test_round1_covers_all_concepts_in_order(self):
        seen = []
        for _ in self.ids:
            item = mastery.next_item(self.session, self.concepts)
            self.assertFalse(item["done"])
            self.assertEqual(item["round"], 1)
            seen.append(item["concept_id"])
            mastery.record_attempt(self.session, item["concept_id"], attempt(item["exercise"]["id"], 90))
        self.assertEqual(seen, self.ids)
    def test_round2_targets_only_weak_concepts(self):
        weak = {self.ids[1], self.ids[4]}
        for cid in self.ids:
            item = mastery.next_item(self.session, self.concepts)
            score = 60 if item["concept_id"] in weak else 95
            gaps = [{"description": "hole", "severity": "moderate"}] if score < 85 else []
            mastery.record_attempt(self.session, item["concept_id"], attempt(item["exercise"]["id"], score, gaps))
        item = mastery.next_item(self.session, self.concepts)
        self.assertEqual(self.session["round"], 2)
        self.assertIn(item["concept_id"], weak)
        self.assertTrue(item["needs_generation"])
        self.assertEqual(len(item["prior_gaps"]), 1)
    def test_all_mastered_returns_done(self):
        for cid in self.ids:
            item = mastery.next_item(self.session, self.concepts)
            mastery.record_attempt(self.session, item["concept_id"], attempt(item["exercise"]["id"], 100))
        self.assertTrue(mastery.next_item(self.session, self.concepts)["done"])
        summary = mastery.session_summary(self.session, self.concepts)
        self.assertTrue(summary["all_mastered"])
    def test_generated_exercise_preferred_on_repeat_round(self):
        cid = self.ids[0]
        concept = self.concepts["concepts"][0]
        mastery.record_attempt(self.session, cid, attempt(concept["exercises"][0]["id"], 50))
        gen = mastery.add_generated_exercise(self.session, cid, {"prompt": "targeted", "reference_solution": "sol"})
        self.assertEqual(gen["id"], f"{cid}-gen1")
        picked = mastery.pick_exercise(self.session, concept)
        self.assertEqual(picked["id"], gen["id"])
    def test_pick_exercise_recycles_when_exhausted(self):
        cid = self.ids[0]
        concept = self.concepts["concepts"][0]
        for ex in concept["exercises"]:
            mastery.record_attempt(self.session, cid, attempt(ex["id"], 50))
        picked = mastery.pick_exercise(self.session, concept)
        self.assertIn(picked["id"], [ex["id"] for ex in concept["exercises"]])
    def test_session_save_load_roundtrip(self):
        tmp = tempfile.mkdtemp()
        try:
            mastery.record_attempt(self.session, self.ids[0], attempt("x-1", 77))
            mastery.save_session(self.session, tmp)
            loaded = mastery.load_session(tmp, self.session["session_id"])
            self.assertEqual(loaded["session_id"], self.session["session_id"])
            self.assertEqual(mastery.latest_score(loaded, self.ids[0]), 77)
            self.assertEqual(mastery.latest_session(tmp)["session_id"], self.session["session_id"])
        finally:
            shutil.rmtree(tmp)

class TestServerApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        os.environ["AUTOLEARNER_DATA_DIR"] = cls.tmp
        from apps.autolearner import server
        cls.server = server
        server.DATA_DIR = cls.tmp
        server.app.config["TESTING"] = True
        cls.client = server.app.test_client()
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)
        os.environ.pop("AUTOLEARNER_DATA_DIR", None)
    def fake_dg(self):
        return make_dg_response(make_words([("okay", 1.0, 1.3), ("the", 1.4, 1.6), ("slope", 1.7, 2.0), ("is", 2.1, 2.3), ("three", 2.4, 2.8)]))
    def fake_assessment(self, score=90, gaps=None):
        return {
            "correctness": "correct", "correctness_notes": "clean work", "mastery_score": score,
            "reasoning_quality": "systematic", "pacing_assessment": "steady", "confusion_flags": [],
            "gaps": gaps or [], "strengths": ["checked the answer"], "overall_assessment": "solid",
            "recommendation": "keep going", "pacing_metrics": pacing.compute_pacing_metrics([]),
            "transcript": "okay the slope is three", "mode": "mock",
        }
    def test_state_endpoint(self):
        self.client.post("/api/reset")
        data = self.client.get("/api/state").get_json()
        self.assertIn("summary", data)
        self.assertIn("next", data)
        self.assertEqual(data["summary"]["round"], 1)
        self.assertFalse(data["next"]["done"])
        self.assertIn("modes", data)
    def test_submit_validation(self):
        self.client.post("/api/reset")
        resp = self.client.post("/api/submit", data={"concept_id": "nope", "exercise_id": "x"})
        self.assertEqual(resp.status_code, 400)
        resp = self.client.post("/api/submit", data={"concept_id": "covariation", "exercise_id": "covariation-1"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("audio", resp.get_json()["error"])
    def test_submit_records_attempt_and_advances(self):
        self.client.post("/api/reset")
        with patch.object(self.server.pipeline, "transcribe_audio", return_value=(self.fake_dg(), "mock")), \
             patch.object(self.server.pipeline, "assess_attempt", return_value=(self.fake_assessment(91), "mock")):
            resp = self.client.post("/api/submit", data={
                "concept_id": "covariation", "exercise_id": "covariation-1",
                "audio": (io.BytesIO(b"fake-webm-bytes"), "recording.webm"),
                "photo": (io.BytesIO(b"fake-jpg-bytes"), "work.jpg"),
            }, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["assessment"]["mastery_score"], 91)
        row = [c for c in data["summary"]["concepts"] if c["concept_id"] == "covariation"][0]
        self.assertTrue(row["mastered"])
        self.assertEqual(row["attempts"], 1)
        self.assertNotEqual(data["next"]["concept_id"], "covariation")
    def test_weak_concept_triggers_generation_on_round2(self):
        self.client.post("/api/reset")
        concepts = self.server.CONCEPTS["concepts"]
        generated = [{"prompt": "targeted problem", "reference_solution": "sol", "targets_gap": "slope sign errors"}]
        with patch.object(self.server.pipeline, "transcribe_audio", return_value=(self.fake_dg(), "mock")), \
             patch.object(self.server.pipeline, "generate_targeted_exercises",
                          return_value=(generated, "mock")) as gen_mock:
            for i, c in enumerate(concepts):
                score = 50 if i == 0 else 95
                gaps = [{"description": "slope sign errors", "severity": "major"}] if score < 85 else []
                with patch.object(self.server.pipeline, "assess_attempt",
                                  return_value=(self.fake_assessment(score, gaps), "mock")):
                    state = self.client.get("/api/state").get_json()
                    item = state["next"]
                    resp = self.client.post("/api/submit", data={
                        "concept_id": item["concept_id"], "exercise_id": item["exercise"]["id"],
                        "audio": (io.BytesIO(b"fake"), "recording.webm"),
                    }, content_type="multipart/form-data")
                    self.assertEqual(resp.status_code, 200)
            state = self.client.get("/api/state").get_json()
        item = state["next"]
        self.assertEqual(state["summary"]["round"], 2)
        self.assertEqual(item["concept_id"], concepts[0]["id"])
        self.assertTrue(item["exercise"].get("generated"))
        self.assertEqual(item["exercise"]["prompt"], "targeted problem")
        gen_mock.assert_called_once()
    def test_teach_me_endpoint(self):
        self.client.post("/api/reset")
        lesson = {"title": "Slope refresher", "lesson_html": "<p>rise over run</p>",
                  "key_points": ["m = dy/dx"], "audio_script": "rise over run"}
        with patch.object(self.server.pipeline, "generate_lesson", return_value=(lesson, "mock")), \
             patch.object(self.server.pipeline, "tts_lesson_audio", return_value=None):
            resp = self.client.post("/api/teach-me", json={
                "concept_id": "slope", "confusion_text": "I mix up the order of subtraction"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["lesson"]
        self.assertEqual(data["title"], "Slope refresher")
        self.assertIsNone(data["audio_url"])
    def test_pages_served(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/guide").status_code, 200)
    def test_attempt_review_endpoint(self):
        self.client.post("/api/reset")
        upload_dir = os.path.join(self.tmp, "uploads", self.server.get_session()["session_id"])
        os.makedirs(upload_dir, exist_ok=True)
        with open(os.path.join(upload_dir, "test.webm"), "wb") as f:
            f.write(b"fake-audio")
        with open(os.path.join(upload_dir, "test.jpg"), "wb") as f:
            f.write(b"fake-image")
        session = self.server.get_session()
        concept = self.server.CONCEPTS["concepts"][0]
        assessment = self.fake_assessment(88)
        mastery.record_attempt(session, concept["id"], {
            "exercise_id": concept["exercises"][0]["id"],
            "mastery_score": 88,
            "correctness": "correct",
            "gaps": [],
            "assessment": assessment,
            "audio_file": "test.webm",
            "image_file": "test.jpg",
            "transcription_mode": "mock",
            "assessment_mode": "mock",
        })
        mastery.save_session(session, self.tmp)
        resp = self.client.get("/api/attempt/" + concept["id"])
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["assessment"]["mastery_score"], 88)
        self.assertIn("test.webm", data["audio_url"])
        self.assertIn("test.jpg", data["image_url"])
        self.assertEqual(self.client.get(data["audio_url"]).status_code, 200)

class TestPipelineEnv(unittest.TestCase):
    def test_has_real_key_rejects_placeholder(self):
        from apps.autolearner import pipeline
        os.environ["TEST_AUTOLEARNER_KEY"] = pipeline.PLACEHOLDER
        self.assertFalse(pipeline._has_real_key("TEST_AUTOLEARNER_KEY"))
        os.environ["TEST_AUTOLEARNER_KEY"] = "sk-real-looking-key"
        self.assertTrue(pipeline._has_real_key("TEST_AUTOLEARNER_KEY"))
        os.environ.pop("TEST_AUTOLEARNER_KEY", None)
    def test_service_modes_detects_configured_keys(self):
        from apps.autolearner import pipeline
        saved = {k: os.environ.get(k) for k in [
            "DEEPGRAM_API_KEY", "ANTHROPIC_API_KEY_LOCAL", "OPENAI_API_KEY_LOCAL", "OPENAI_API_KEY_TTS"]}
        try:
            os.environ["DEEPGRAM_API_KEY"] = "dg-test-key"
            os.environ["ANTHROPIC_API_KEY_LOCAL"] = "anthropic-test-key"
            os.environ["OPENAI_API_KEY_LOCAL"] = "openai-test-key"
            modes = pipeline.service_modes()
            self.assertEqual(modes["transcription"], "deepgram")
            self.assertEqual(modes["assessment"], "anthropic")
            self.assertEqual(modes["tts"], "openai")
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
    def test_mock_assessment_score_is_deterministic(self):
        from apps.autolearner import pipeline
        concept = {"title": "Slope", "summary": "Compute slope from two points."}
        exercise = {"id": "covariation-1"}
        metrics = {"total_words": 152, "words_per_minute": 112.6, "pause_count": 2,
                   "longest_pause_s": 14.8}
        result = pipeline._mock_assessment(concept, exercise, "okay the slope is three", metrics,
                                           mock_reason="llm_no_tool_response")
        self.assertEqual(result["mastery_score"], 68)
        self.assertIn("placeholder", result["overall_assessment"].lower())
        self.assertEqual(result["mock_reason"], "llm_no_tool_response")
    def test_structured_llm_call_forces_anthropic_tool_choice(self):
        from apps.autolearner import pipeline
        captured = {}
        def fake_anthropic(**kwargs):
            captured.update(kwargs)
            return type("Resp", (), {"content": [type("Block", (), {"type": "tool_use", "input": {"ok": True}})()]})()
        with patch.object(pipeline, "service_modes", return_value={"assessment": "anthropic", "transcription": "mock", "tts": "mock"}), \
             patch.object(pipeline, "_import_core_llm") as import_mock:
            llm = import_mock.return_value
            llm.anthropic_chat_completion_request = fake_anthropic
            result, mode = pipeline._structured_llm_call("system", "content", pipeline.EXERCISE_TOOL)
        self.assertEqual(mode, "anthropic")
        self.assertTrue(result["ok"])
        self.assertEqual(captured["tool_choice"], {"type": "tool", "name": "create_targeted_exercises"})

if __name__ == "__main__":
    unittest.main()
