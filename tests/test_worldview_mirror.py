# Run with: .venv/bin/python3 -m pytest tests/test_worldview_mirror.py -q
# Self-contained: taxonomy tests validate against the committed deutsch-graph; engine and
# server tests stub the LLM call (no network or API keys needed). User-data tests use temp dirs.

import json
import os
import shutil
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(REPO_ROOT, "apps", "deutsch", "worldview-mirror"))
from wvmirror import atlas, compare, config, engine, graph_access, profile_store, threads

### Shared fixtures (committed graph + taxonomy load once)
GRAPH = graph_access.load_graph()
ATLAS = atlas.load_atlas()

### Taxonomy
class TestTaxonomy(unittest.TestCase):
    def test_axis_count_in_target_range(self):
        self.assertGreaterEqual(len(ATLAS["axes"]), 8)
        self.assertLessEqual(len(ATLAS["axes"]), 15)
    def test_atlas_valid_against_committed_graph(self):
        errors = atlas.validate_atlas(ATLAS, GRAPH["nodes"])
        self.assertEqual(errors, [])
    def test_deep_optimism_fully_graph_cited(self):
        profile = ATLAS["profiles"]["profile:deep-optimism"]
        self.assertTrue(profile["cited_from_graph"])
        self.assertEqual(len(profile["positions"]), len(ATLAS["axes"]))
        for pos in profile["positions"]:
            node_refs = [ev for ev in pos["evidence"] if ev.get("node")]
            self.assertTrue(node_refs, "axis %s has no graph-node evidence" % pos["axis"])
            for ev in node_refs:
                self.assertIn(ev["node"], GRAPH["nodes"])
    def test_validate_catches_bad_data(self):
        bad = {"axes": [{"id": "axis:x", "label": "X", "question": "?",
                         "pole_neg": {"label": "a", "definition": "d"}, "pole_pos": {"label": "b", "definition": "d"}}],
               "profiles": {"profile:p": {"id": "profile:p", "label": "P", "summary": "s", "positions": [
                   {"axis": "axis:unknown", "position": 1.0, "summary": "s"},
                   {"axis": "axis:x", "position": 9.0, "summary": "s"},
                   {"axis": "axis:x", "position": 1.0, "summary": ""},
                   {"axis": "axis:x", "position": 1.0, "summary": "s", "evidence": [{"node": "qa:nope:000"}]}]}}}
        errors = atlas.validate_atlas(bad, GRAPH["nodes"])
        joined = "\n".join(errors)
        self.assertIn("unknown axis", joined)
        self.assertIn("outside", joined)
        self.assertIn("missing summary", joined)
        self.assertIn("duplicate position", joined)
        self.assertIn("not in graph", joined)

### Profile store
class TestProfileStore(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
    def tearDown(self):
        shutil.rmtree(self.dir)
    def test_round_trip_and_markdown_mirror(self):
        profile = profile_store.new_profile()
        profile_store.add_observation(profile, "Progress is real", "axis:progress", 1.5, 0.8, quote="it works")
        profile_store.save_profile(profile, profiles_dir=self.dir, axes=ATLAS["axes"])
        loaded = profile_store.load_profile(profiles_dir=self.dir)
        self.assertEqual(len(loaded["observations"]), 1)
        with open(os.path.join(self.dir, "user.md"), encoding="utf-8") as f:
            md = f.read()
        self.assertIn("BELIEF: Progress is real", md)
        self.assertIn("QUOTE: it works", md)
    def test_aggregation_weighted_mean_and_override(self):
        profile = profile_store.new_profile()
        profile_store.add_observation(profile, "b1", "axis:progress", 2.0, 1.0)
        profile_store.add_observation(profile, "b2", "axis:progress", 0.0, 1.0)
        agg = profile_store.aggregate_positions(profile)
        self.assertEqual(agg["axis:progress"]["position"], 1.0)
        self.assertEqual(agg["axis:progress"]["count"], 2)
        profile_store.set_axis_override(profile, "axis:progress", -2.0)
        agg = profile_store.aggregate_positions(profile)
        self.assertEqual(agg["axis:progress"]["position"], -2.0)
        self.assertEqual(agg["axis:progress"]["basis"], "override")
        profile_store.clear_axis_override(profile, "axis:progress")
        self.assertEqual(profile_store.aggregate_positions(profile)["axis:progress"]["basis"], "observed")
    def test_delete_observation_and_profile(self):
        profile = profile_store.new_profile()
        obs = profile_store.add_observation(profile, "b", "axis:risk", 1.0, 0.5)
        self.assertTrue(profile_store.delete_observation(profile, obs["id"]))
        self.assertFalse(profile_store.delete_observation(profile, "obs-999"))
        profile_store.save_profile(profile, profiles_dir=self.dir, axes=[])
        profile_store.delete_profile(profiles_dir=self.dir)
        self.assertEqual(profile_store.load_profile(profiles_dir=self.dir)["observations"], [])

### Threads
class TestThreads(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
    def tearDown(self):
        shutil.rmtree(self.dir)
    def test_thread_lifecycle(self):
        thread = threads.create_thread(threads_dir=self.dir)
        threads.append_message(thread, "user", "What is optimism about, really?", threads_dir=self.dir)
        threads.append_message(thread, "assistant", "reply", meta={"citations": []}, threads_dir=self.dir)
        loaded = threads.load_thread(thread["id"], threads_dir=self.dir)
        self.assertEqual(len(loaded["messages"]), 2)
        self.assertTrue(loaded["title"].startswith("What is optimism"))
        listing = threads.list_threads(threads_dir=self.dir)
        self.assertEqual(listing[0]["id"], thread["id"])
        self.assertEqual(listing[0]["messages"], 2)
        self.assertTrue(threads.delete_thread(thread["id"], threads_dir=self.dir))
        self.assertFalse(threads.delete_thread(thread["id"], threads_dir=self.dir))

### Compare
class TestCompare(unittest.TestCase):
    def test_user_vs_lens_alignment_labels(self):
        profile = profile_store.new_profile()
        profile_store.add_observation(profile, "doom", "axis:progress", -1.8, 1.0)
        profile_store.add_observation(profile, "fallibilist", "axis:epistemology", 1.8, 1.0)
        rows = compare.compare_user_to_profile(profile, ATLAS["profiles"]["profile:deep-optimism"], ATLAS["axes"])
        by_axis = {r["axis"]: r for r in rows}
        self.assertEqual(by_axis["axis:progress"]["alignment"], "divergent")
        self.assertEqual(by_axis["axis:epistemology"]["alignment"], "aligned")
        self.assertEqual(rows[0]["alignment"], "divergent")
        lens_only = [r for r in rows if r["user_position"] is None]
        self.assertTrue(all(r["alignment"] == "unknown" for r in lens_only))
    def test_profile_vs_profile(self):
        rows = compare.compare_profiles(ATLAS["profiles"]["profile:deep-optimism"],
                                        ATLAS["profiles"]["profile:postmodern-relativism"], ATLAS["axes"])
        realism = [r for r in rows if r["axis"] == "axis:realism"][0]
        self.assertEqual(realism["delta"], 4.0)
        self.assertEqual(realism["alignment"], "divergent")

### Graph access
class TestGraphAccess(unittest.TestCase):
    def test_topic_catalog_shape(self):
        catalog = graph_access.topic_catalog(GRAPH)
        self.assertGreater(len(catalog["topics"]), 300)
        self.assertEqual(len(catalog["categories"]), 34)
    def test_trim_word_boundary(self):
        self.assertEqual(graph_access._trim("short", 100), "short")
        trimmed = graph_access._trim("word " * 100, 40)
        self.assertTrue(trimmed.endswith(" [...]"))
        self.assertLessEqual(len(trimmed), 46)
    def test_answer_text_from_fixture(self):
        tmp = tempfile.mkdtemp()
        rel = "data/fixture_qafixed.md"
        os.makedirs(os.path.join(tmp, "data"), exist_ok=True)
        with open(os.path.join(tmp, rel), "w", encoding="utf-8") as f:
            f.write("## content\n\n### qa\nQUESTION: Q0?\nANSWER: first answer\n\nQUESTION: Q1?\nANSWER: second answer\n")
        original = config.REPO_ROOT
        config.REPO_ROOT = tmp
        try:
            node = {"answer_pointer": {"path": rel, "block": 1}}
            self.assertEqual(graph_access.answer_text(node), "second answer")
            self.assertIsNone(graph_access.answer_text({"answer_pointer": {"path": "data/missing.md", "block": 0}}))
        finally:
            config.REPO_ROOT = original
            shutil.rmtree(tmp)
    def test_qa_grounding_uses_committed_graph(self):
        items = graph_access.qa_grounding(GRAPH, ["topic:optimism"], per_topic=2)
        self.assertTrue(items)
        self.assertTrue(all(i["id"].startswith("qa:") for i in items))

### Engine (LLM stubbed)
class TestEngine(unittest.TestCase):
    def setUp(self):
        self._chat_orig = engine._chat
    def tearDown(self):
        engine._chat = self._chat_orig
    def test_json_from_tolerates_fences_and_prose(self):
        self.assertEqual(engine._json_from('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(engine._json_from('Sure! {"a": 1} hope that helps'), {"a": 1})
    def test_route_and_extract_maps_and_clamps(self):
        catalog = graph_access.topic_catalog(GRAPH)
        topic_label = catalog["topics"][0]["label"]
        engine._chat = lambda messages, model=None, temperature=None: json.dumps({
            "topics": [topic_label, "not-a-real-topic"], "categories": [], "concept_needles": ["optimism"],
            "beliefs": [{"belief": "b1", "axis": "axis:progress", "position": 9, "confidence": 2, "quote": "q"},
                        {"belief": "b2", "axis": "axis:bogus", "position": 1, "confidence": 0.5, "quote": ""}]})
        result = engine.route_and_extract("msg", catalog, ATLAS["axes"])
        self.assertEqual(result["topics"], [catalog["topics"][0]["id"]])
        self.assertEqual(result["beliefs"][0]["position"], 2.0)
        self.assertEqual(result["beliefs"][0]["confidence"], 1.0)
        self.assertIsNone(result["beliefs"][1]["axis"])
    def test_system_prompt_contains_all_sections(self):
        profile = profile_store.new_profile()
        profile_store.add_observation(profile, "belief text", "axis:progress", 1.0, 0.9)
        grounding = graph_access.build_grounding(GRAPH, ["topic:optimism"], [])
        prompt = engine.build_system_prompt(ATLAS["profiles"]["profile:deep-optimism"], profile, grounding, 5, ATLAS["axes"])
        for needle in ("NOT a therapist", "MIRROR, not preach", "Critical", "LENS WORLDVIEW: Deep Optimism",
                       "USER PROFILE", "belief text", "SOURCE qa:"):
            self.assertIn(needle, prompt)
    def test_extract_citations_dedupes_and_resolves(self):
        cite_index = graph_access.citation_index(GRAPH)
        reply = "See [concept:boi/fallibilism] and again [concept:boi/fallibilism], plus [qa:bogus:000]."
        cites = engine.extract_citations(reply, cite_index)
        self.assertEqual(len(cites), 1)
        self.assertEqual(cites[0]["id"], "concept:boi/fallibilism")
    def test_answer_turn_full_flow(self):
        calls = []
        def fake_chat(messages, model=None, temperature=None):
            calls.append(messages)
            if len(calls) == 1:
                return json.dumps({"topics": [], "categories": [], "concept_needles": [],
                                   "beliefs": [{"belief": "doomer", "axis": "axis:progress", "position": -1.5, "confidence": 0.9, "quote": "we're doomed"}]})
            return "Deep optimism disagrees [concept:boi/the-principle-of-optimism]."
        engine._chat = fake_chat
        thread = {"id": "t", "settings": {"tone": 3, "lens": "profile:deep-optimism"}, "messages": []}
        profile = profile_store.new_profile()
        result = engine.answer_turn(GRAPH, ATLAS, graph_access.citation_index(GRAPH), thread, "we're doomed", profile)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[2 - 1][0]["role"], "system")
        self.assertEqual(result["citations"][0]["id"], "concept:boi/the-principle-of-optimism")
        self.assertEqual(len(result["observed"]), 1)
        self.assertEqual(result["mirror"][0]["axis"], "axis:progress")
        self.assertEqual(result["mirror"][0]["alignment"], "divergent")

### Server (LLM stubbed, data dirs redirected)
class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from wvmirror import server
        cls.server = server
        cls.tmp = tempfile.mkdtemp()
        cls._dirs = (config.PROFILES_DIR, config.THREADS_DIR)
        config.PROFILES_DIR = os.path.join(cls.tmp, "profiles")
        config.THREADS_DIR = os.path.join(cls.tmp, "threads")
        cls._token = server.SESSION_TOKEN
        server.SESSION_TOKEN = "test-token"
        cls.client = TestClient(server.app)
        cls.client.__enter__()
        cls.headers = {"X-WVM-Token": "test-token"}
    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        config.PROFILES_DIR, config.THREADS_DIR = cls._dirs
        cls.server.SESSION_TOKEN = cls._token
        shutil.rmtree(cls.tmp)
    def test_api_requires_token(self):
        self.assertEqual(self.client.get("/api/state").status_code, 401)
        self.assertEqual(self.client.get("/api/state", headers={"X-WVM-Token": "wrong"}).status_code, 401)
    def test_state_and_atlas(self):
        state = self.client.get("/api/state", headers=self.headers).json()
        self.assertEqual(len(state["axes"]), len(ATLAS["axes"]))
        self.assertEqual(len(state["profiles"]), len(ATLAS["profiles"]))
        self.assertEqual(len(state["tones"]), 5)
        full = self.client.get("/api/atlas", headers=self.headers).json()
        self.assertTrue(all("positions" in p for p in full["profiles"]))
    def test_page_injects_token(self):
        page = self.client.get("/").text
        self.assertIn("test-token", page)
        self.assertNotIn("__WVM_TOKEN__", page)
    def test_chat_flow_updates_thread_and_profile(self):
        calls = []
        def fake_chat(messages, model=None, temperature=None):
            calls.append(messages)
            if len(calls) == 1:
                return json.dumps({"topics": [], "categories": [], "concept_needles": [],
                                   "beliefs": [{"belief": "optimist", "axis": "axis:progress", "position": 1.5, "confidence": 0.8, "quote": "hopeful"}]})
            return "Reflected [concept:boi/optimism]."
        original = engine._chat
        engine._chat = fake_chat
        try:
            res = self.client.post("/api/chat", headers=self.headers,
                                   json={"message": "I am hopeful", "tone": 2, "lens": "profile:deep-optimism"})
        finally:
            engine._chat = original
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["thread"]["messages"]), 2)
        self.assertEqual(data["citations"][0]["id"], "concept:boi/optimism")
        self.assertEqual(len(data["profile"]["observations"]), 1)
        thread_id = data["thread"]["id"]
        listed = self.client.get("/api/threads", headers=self.headers).json()["threads"]
        self.assertIn(thread_id, [t["id"] for t in listed])
        self.assertEqual(self.client.delete("/api/threads/" + thread_id, headers=self.headers).status_code, 200)
    def test_thread_controls_reject_unknown_values(self):
        self.assertEqual(self.client.post("/api/threads", headers=self.headers,
                                          json={"tone": 99}).status_code, 400)
        self.assertEqual(self.client.post("/api/threads", headers=self.headers,
                                          json={"lens": "profile:unknown"}).status_code, 400)
        self.assertEqual(self.client.post("/api/chat", headers=self.headers,
                                          json={"message": "hello", "tone": "loud"}).status_code, 400)
        self.assertEqual(self.client.post("/api/chat", headers=self.headers,
                                          json={"message": "hello", "lens": "profile:unknown"}).status_code, 400)
    def test_profile_endpoints(self):
        res = self.client.post("/api/profile/observation", headers=self.headers,
                               json={"belief": "manual", "axis": "axis:risk", "position": -1.0})
        self.assertEqual(res.status_code, 200)
        obs_id = res.json()["observation"]["id"]
        self.assertEqual(self.client.post("/api/profile/observation", headers=self.headers,
                                          json={"belief": "x", "axis": "axis:bogus", "position": 0}).status_code, 400)
        res = self.client.post("/api/profile/axis", headers=self.headers, json={"axis": "axis:risk", "position": 2.0})
        self.assertEqual(res.json()["positions"]["axis:risk"]["basis"], "override")
        compare_res = self.client.get("/api/compare?lens=profile:deep-optimism", headers=self.headers).json()
        risk = [r for r in compare_res["rows"] if r["axis"] == "axis:risk"][0]
        self.assertEqual(risk["user_position"], 2.0)
        self.assertEqual(self.client.delete("/api/profile/observation/" + obs_id, headers=self.headers).status_code, 200)
        self.assertEqual(self.client.delete("/api/profile", headers=self.headers).status_code, 200)
        self.assertEqual(self.client.get("/api/profile", headers=self.headers).json()["profile"]["observations"], [])
    def test_profile_endpoints_reject_invalid_numeric_values(self):
        invalid_observations = [
            {"belief": "", "axis": "axis:risk", "position": 0},
            {"belief": "manual", "axis": "axis:risk", "position": 2.1},
            {"belief": "manual", "axis": "axis:risk", "position": "nan"},
            {"belief": "manual", "axis": "axis:risk", "position": 0, "confidence": -0.1},
        ]
        for payload in invalid_observations:
            self.assertEqual(self.client.post("/api/profile/observation", headers=self.headers,
                                              json=payload).status_code, 400)
        self.assertEqual(self.client.post("/api/profile/axis", headers=self.headers,
                                          json={"axis": "axis:risk", "position": -2.1}).status_code, 400)
    def test_atlas_compare_endpoint(self):
        res = self.client.get("/api/atlas/compare?a=profile:deep-optimism&b=profile:stoicism", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.client.get("/api/atlas/compare?a=profile:nope&b=profile:stoicism", headers=self.headers).status_code, 404)

if __name__ == "__main__":
    unittest.main()
