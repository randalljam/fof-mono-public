# Run with: .venv/bin/python3 -m pytest tests/test_deutsch_graph.py -q
# (or: python -m unittest tests.test_deutsch_graph)
# Self-contained: builds a tiny fixture corpus in a temp dir; no S3 or real data needed.

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "apps", "deutsch", "deutsch-graph"))
from dgraph import build, export_vis, ids, inventory, parse_books, parse_corpus, parse_terms, parse_well, query, validate

### Fixture corpus text
QAFIXED = """## metadata
last updated: 01-01-2025 by test
link youtube: https://www.youtube.com/watch?v=abc123
transcript source: whspmerge
length: 10:00


## content

### qa

QUESTION: What is optimism?
TIMESTAMP: [0:34](https://www.youtube.com/watch?v=abc123&t=34)
ANSWER: All evils are caused by insufficient knowledge.
EDITS:
TOPICS: optimism, epistemology
STARS: 3

QUESTION: Why are problems soluble?
TIMESTAMP: [2:10](https://www.youtube.com/watch?v=abc123&t=130)
ANSWER: Because the right knowledge would solve them.
EDITS:
TOPICS: optimism, problems
STARS:
"""
QA_MULTI = QAFIXED.replace(
    "QUESTION: What is optimism?",
    "QUESTION 1: What is optimism?\nQUESTION 2: What does deep optimism claim?"
)
TOPSTARS = """## metadata
link youtube: https://www.youtube.com/watch?v=abc123


## content

### qa

QUESTION: What is optimism?
TIMESTAMP: [0:34](https://www.youtube.com/watch?v=abc123&t=34)
ANSWER: All evils are caused by insufficient knowledge.
TOPICS: optimism, epistemology
STARS: 3
"""
CHAPTER = """## INTRO
> quote

## BODY
Body text here.

## TERMINOLOGY

**Wealth** The repertoire of physical transformations that one is capable of causing.

**_Explanation_** Statement about what is there, what it does, and how and why.

## SUMMARY

Optimism is the theory that all failures are due to insufficient knowledge.
"""
BASE = "2020-05-05_Test Interview - Deep Optimism"

### Helpers
def make_fixture_repo(root):
    """Minimal fake monorepo with one interview (qafixed/qa-multi/vrb), topstars, a book chapter, an essay."""
    dd = os.path.join(root, "data", "deutsch")
    paths = {
        "data/deutsch/f8_done_qafixed_and_vrb/%s_qafixed.md" % BASE: QAFIXED,
        "data/deutsch/f8_done_qafixed_and_vrb/%s_qa-multi.md" % BASE: QA_MULTI,
        "data/deutsch/f8_done_qafixed_and_vrb/%s_vrb.md" % BASE: "## metadata\n\n## content\n\n### transcript\n\ntext\n",
        "data/deutsch/dd_top-stars_qa-multi/%s_qa-topstars.md" % BASE: TOPSTARS,
        "data/deutsch/books/boi.md": "# Chapter 1 - The Reach of Explanations\n\ntext\n",
        "data/deutsch/books/BOI chapters/Chapter 1 - The Reach of Explanations.md": CHAPTER,
        "data/deutsch/books/BOI - all terms.md": "**_Reach_** The ability of some explanations to solve problems beyond those that they were created to solve.\n",
        "data/deutsch/essays/2019-07-15_Beyond Reward and Punishment.md": "Publication: Possible Minds\nTitle: Beyond Reward and Punishment\nOriginal Link: https://example.org/essay.pdf\n\nBody.\n",
        "data/deutsch/essays/tcs/dd/1997-08-01_TCS Site_Fallibilism.md": "## metadata\nlast updated: 1997-08-01\nlink: https://takingchildrenseriously.com/x/\n\n\n## content\n\n### article\n\nBody.\n",
        # raw-stage file with a drifted name that should fuzzy-join the same work
        "data/deutsch/f9_raw/2020-05-05_Test Interview about Deep Optimism_yt.md": "raw captions\n",
        # archived copy that must be excluded entirely
        "data/deutsch/fx_archive/%s_qafixed.md" % BASE: QAFIXED,
        # Deutsch Well vault: category -> claim -> excerpts (one book-chapter source, one renamed interview source)
        "data/deutsch/deutsch-well_2023/Problems/Problems.md": "# Problems\n#L1",
        "data/deutsch/deutsch-well_2023/Problems/are soluble/are soluble.md": "# Problems\nare soluble\n#L2",
        "data/deutsch/deutsch-well_2023/Problems/are soluble/ excerpt one.md":
            "Chapter 1 - The Reach of Explanations.md : Problems are soluble with the right knowledge.\n#L3",
        "data/deutsch/deutsch-well_2023/Problems/are soluble/ excerpt two.md":
            "2020-05-05_Test Interview on Deep Optimism.md : All evils are due to insufficient knowledge.\n#L3",
        "data/deutsch/deutsch-well_2023/Problems/are soluble/ image junk mathpix.md":
            "!(https or cdn.mathpix.com or cropped)figure\n#L3",
        # terms collection
        "data/deutsch/terms/Terms - BOI/Wealth.md": "## Wealth\nBOI-terms wealth definition.\n\nChapter 1: The Reach of Explanations",
        "data/deutsch/terms/Terms - BOI/Fungible.md": "## Fungible\nIdentical in every way.\n\nChapter 11: The Multiverse",
        "data/deutsch/terms/Terms - FOR/Kick_back.md": "## Kick back\nIf it can kick back, it exists.\nThe Fabric of Reality - Chapter 4",
        "data/deutsch/terms/Terms - BOIxyz/Qualia.md": "# Qualia\n\nThe subjective aspect of a sensation.",
        "data/deutsch/terms/Topics - Important/Problems.md": "Conflicts between ideas; the growth of knowledge starts from them.",
        "data/deutsch/terms/Topics - Important/Program.md": "A set of instructions for a computer.",
    }
    manifest_rows = []
    for rel, content in paths.items():
        full = os.path.join(root, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        manifest_rows.append({"repo_path": rel, "size_bytes": len(content.encode()), "sha256": "x" * 64,
                              "s3_bucket": "[S3-FILES-BUCKET]", "s3_key": rel, "s3_uri": "s3://[S3-FILES-BUCKET]/" + rel,
                              "status": "verified"})
    os.makedirs(os.path.join(root, "manifests"), exist_ok=True)
    with open(os.path.join(root, "manifests", "deutsch.manifest.jsonl"), "w") as f:
        for row in manifest_rows:
            f.write(json.dumps(row) + "\n")

### Tests: ids
class TestIds(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(ids.slugify("Joe Boswell - Constructor Theory"), "joe-boswell-constructor-theory")
        self.assertEqual(ids.slugify("What's  up—now?"), "whats-up-now")
    def test_split_base_name(self):
        self.assertEqual(ids.split_base_name("%s_qafixed.md" % BASE), (BASE, "qafixed"))
        self.assertEqual(ids.split_base_name("%s_qa-multi.md" % BASE), (BASE, "qa-multi"))
        self.assertEqual(ids.split_base_name("X_vrb_propernames.md"), ("X", "vrb_propernames"))
        # unknown trailing word stays part of the title
        self.assertEqual(ids.split_base_name("1994-03-01_Evolution of Culture.md"), ("1994-03-01_Evolution of Culture", ""))
    def test_work_slug_keeps_date(self):
        self.assertEqual(ids.work_slug(BASE), "2020-05-05_test-interview-deep-optimism")
    def test_qa_and_topic_ids(self):
        self.assertEqual(ids.qa_id("w", 3), "qa:w:003")
        self.assertEqual(ids.topic_id("Constructor Theory"), "topic:constructor-theory")

### Tests: corpus parsing
class TestParseCorpus(unittest.TestCase):
    def test_parse_qa_file(self):
        meta, blocks = parse_corpus.parse_qa_file(QAFIXED)
        self.assertEqual(meta["link youtube"], "https://www.youtube.com/watch?v=abc123")
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0]["ordinal"], 0)
        self.assertEqual(blocks[0]["questions"], ["What is optimism?"])
        self.assertEqual(blocks[0]["timestamp_sec"], 34)
        self.assertEqual(blocks[0]["topics"], ["optimism", "epistemology"])
        self.assertEqual(blocks[0]["stars"], 3)
        self.assertEqual(blocks[1]["stars"], 0)
    def test_qa_multi_numbered_questions(self):
        _, blocks = parse_corpus.parse_qa_file(QA_MULTI)
        self.assertEqual(blocks[0]["questions"],
                         ["What is optimism?", "What does deep optimism claim?"])
    def test_duplicate_question_quirk(self):
        broken = QAFIXED.replace("STARS: 3", "STARS: 3\nQUESTION: A stray merged question?")
        quirks = []
        _, blocks = parse_corpus.parse_qa_file(broken, quirks)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(len(quirks), 1)
        self.assertIn("duplicate QUESTION", quirks[0])
    def test_parse_essay_both_shapes(self):
        info = parse_corpus.parse_essay("Publication: X\nOriginal Link: https://a.b/c\n\nBody.")
        self.assertEqual(info["link"], "https://a.b/c")
        info2 = parse_corpus.parse_essay("## metadata\nlink: https://tcs.example/\n\n\n## content\n\n### article\n\nBody.")
        self.assertEqual(info2["link"], "https://tcs.example/")

### Tests: books
class TestParseBooks(unittest.TestCase):
    def test_chapter_summary_and_terms(self):
        self.assertTrue(parse_books.chapter_summary(CHAPTER).startswith("Optimism is the theory"))
        terms = parse_books.chapter_terms(CHAPTER)
        self.assertEqual([t[0] for t in terms], ["Wealth", "Explanation"])
        self.assertTrue(terms[0][1].startswith("The repertoire"))

### Tests: inventory
class TestInventory(unittest.TestCase):
    def test_classify_excludes_archives(self):
        self.assertIsNone(inventory.classify_path("data/deutsch/fx_archive/x_qafixed.md"))
        self.assertIsNone(inventory.classify_path("data/deutsch/f7_no-link-copy/x_qafixed.md"))
        self.assertEqual(inventory.classify_path("data/deutsch/f8_done_qafixed_and_vrb/x_qafixed.md"),
                         ("f8_done", "interview", 3))

### Tests: Deutsch Well and terms parsing
class TestParseWell(unittest.TestCase):
    def test_image_artifact_detection(self):
        self.assertTrue(parse_well.is_image_artifact("x mathpix y.md", "text"))
        self.assertTrue(parse_well.is_image_artifact("z.md", "!(https...)"))
        self.assertFalse(parse_well.is_image_artifact("normal.md", "Chapter 1 - X.md : quote"))
    def test_clean_excerpt_text(self):
        self.assertEqual(parse_well.clean_excerpt_text("some  text\n#L3"), "some text")
class TestParseTerms(unittest.TestCase):
    def test_term_from_file_heading_and_stem(self):
        self.assertEqual(parse_terms.term_from_file("X.md", "## Reach\nDef"), "Reach")
        self.assertEqual(parse_terms.term_from_file("Kick_back.md", "no heading"), "Kick back")
    def test_definition_strips_chapter_ref(self):
        d = parse_terms.definition_from_text("## Wealth\nDef here.\n\nChapter 1: The Reach", parse_terms.CHAPTER_REF_BOI_RE)
        self.assertEqual(d, "Def here.")

### Tests: end-to-end build on the fixture repo
class TestBuildEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        make_fixture_repo(cls.tmp)
        cls.result = build.build_graph(root=cls.tmp, verbose=False)
        cls.out_dir = os.path.join(cls.tmp, "graph_out")
        build.write_graph(cls.result, out_dir=cls.out_dir, root=cls.tmp)
        cls.graph = query.load_graph(cls.out_dir)
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)
    def test_work_node_and_formats(self):
        wid = ids.work_id(BASE)
        work = self.graph["nodes"][wid]
        self.assertEqual(work["qa_count"], 2)
        self.assertEqual(work["starred_count"], 1)
        self.assertEqual(work["link_youtube"], "https://www.youtube.com/watch?v=abc123")
        self.assertIn("qafixed", work["formats"])
        self.assertIn("qa-topstars", work["formats"])
        # drifted raw file fuzzy-joined the same work instead of creating a duplicate
        self.assertIn("yt", work["formats"])
        # archived copy excluded
        self.assertFalse(any("fx_archive" in p for p in work["formats"].values()))
    def test_qa_nodes(self):
        wslug = ids.work_slug(BASE)
        q0 = self.graph["nodes"]["qa:%s:000" % wslug]
        self.assertTrue(q0["starred"])
        self.assertEqual(q0["topics"], ["topic:optimism", "topic:epistemology"])
        self.assertEqual(q0["questions_alt"], ["What does deep optimism claim?"])
        self.assertEqual(q0["vector_id_base"],
                         ("%s_qa-multi_0" % BASE).replace(" ", "_"))
        q1 = self.graph["nodes"]["qa:%s:001" % wslug]
        self.assertFalse(q1["starred"])
    def test_topic_and_edges(self):
        topic = self.graph["nodes"]["topic:optimism"]
        self.assertEqual(topic["qa_count"], 2)
        weights = {(e["src"], e["dst"]): e.get("weight") for e in self.graph["edges"] if e["type"] == "work_topic"}
        self.assertEqual(weights[(ids.work_id(BASE), "topic:optimism")], 2)
        self.assertEqual(weights[(ids.work_id(BASE), "topic:epistemology")], 1)
    def test_books_and_concepts(self):
        self.assertIn("chapter:boi/01", self.graph["nodes"])
        self.assertTrue(self.graph["nodes"]["chapter:boi/01"]["summary"].startswith("Optimism is the theory"))
        self.assertIn("concept:boi/wealth", self.graph["nodes"])
        self.assertEqual(self.graph["nodes"]["concept:boi/wealth"]["chapter"], "chapter:boi/01")
        # all-terms entry not defined in a chapter still lands, without a chapter ref
        self.assertIn("concept:boi/reach", self.graph["nodes"])
        self.assertIsNone(self.graph["nodes"]["concept:boi/reach"]["chapter"])
    def test_essays(self):
        essay = self.graph["nodes"][ids.work_id("2019-07-15_Beyond Reward and Punishment")]
        self.assertEqual(essay["kind"], "essay")
        self.assertEqual(essay["link"], "https://example.org/essay.pdf")
        tcs = self.graph["nodes"][ids.work_id("1997-08-01_TCS Site_Fallibilism")]
        self.assertEqual(tcs["kind"], "tcs_post")
        self.assertTrue(tcs["by_deutsch"])
    def test_binary_paper_is_inventoried_without_text_decoding(self):
        with tempfile.TemporaryDirectory() as root:
            rel = "data/deutsch/papers/Deutsch.law.without.law.pdf"
            path = os.path.join(root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(b"%PDF-1.4\n\xe2\xe3\xcf\xd3")
            works = build.essay_work_nodes(root, [{"repo_path": rel}], [])
        self.assertEqual(len(works), 1)
        self.assertEqual(works[0]["kind"], "paper")
        self.assertEqual(works[0]["formats"], {"text": rel})
    def test_queries(self):
        top = query.top_qa_for_topic(self.graph, "topic:optimism", limit=1)
        self.assertTrue(top[0]["starred"])
        hits = query.search_questions(self.graph, "soluble")
        self.assertEqual(len(hits), 1)
        s = query.stats(self.graph)
        self.assertEqual(s["nodes"]["qa"], 2)
    def test_validation_passes(self):
        errors = validate.validate_graph(self.out_dir)
        self.assertEqual(errors, [])
    def test_validation_catches_broken_edge(self):
        broken_dir = os.path.join(self.tmp, "graph_broken")
        build.write_graph(self.result, out_dir=broken_dir, root=self.tmp)
        with open(os.path.join(broken_dir, "edges", "work_topic.jsonl"), "a") as f:
            f.write(json.dumps({"src": "work:nope", "dst": "topic:nope", "type": "work_topic", "weight": 1}) + "\n")
        errors = validate.validate_graph(broken_dir)
        self.assertTrue(any("unresolved" in e for e in errors))
    def test_well_categories_claims_excerpts(self):
        cat = self.graph["nodes"]["category:problems"]
        self.assertEqual(cat["origin"], "deutsch-well-2023")
        self.assertEqual(cat["claim_count"], 1)
        self.assertEqual(cat["excerpt_count"], 2)
        self.assertEqual(cat["definition"], "Conflicts between ideas; the growth of knowledge starts from them.")
        self.assertIn("topic:problems", cat["topics"])
        claim = self.graph["nodes"]["claim:problems/00"]
        self.assertEqual(claim["text"], "are soluble")
        excerpts = [self.graph["nodes"][nid] for nid in self.graph["by_type"]["excerpt"]]
        self.assertEqual(len(excerpts), 2)
        by_ref = {e["source_ref"]: e for e in excerpts}
        chap = by_ref["Chapter 1 - The Reach of Explanations.md"]
        self.assertEqual(chap["source_chapter"], "chapter:boi/01")
        self.assertEqual(chap["source_work"], "work:boi")
        fuzzy = by_ref["2020-05-05_Test Interview on Deep Optimism.md"]
        self.assertEqual(fuzzy["source_work"], ids.work_id(BASE))
    def test_extra_categories_from_overlay(self):
        self.assertIn("category:morality", self.graph["nodes"])
        self.assertEqual(self.graph["nodes"]["category:morality"]["origin"], "v0.2-addition")
    def test_terms_enrich_concepts(self):
        # chapter TERMINOLOGY wins over Terms - BOI for Wealth
        wealth = self.graph["nodes"]["concept:boi/wealth"]
        self.assertEqual(wealth["source"], "chapter-terminology")
        self.assertTrue(wealth["definition"].startswith("The repertoire"))
        fungible = self.graph["nodes"]["concept:boi/fungible"]
        self.assertEqual(fungible["source"], "terms-boi")
        self.assertEqual(fungible["chapter"], "chapter:boi/11")
        self.assertEqual(self.graph["nodes"]["concept:for/kick-back"]["source"], "terms-for")
        self.assertEqual(self.graph["nodes"]["concept:boi/qualia"]["source"], "terms-boixyz")
    def test_viewer_data_export(self):
        out = os.path.join(self.tmp, "webdata")
        shards = export_vis.export_viewer_data(self.out_dir, out)
        index = open(os.path.join(out, "index.js")).read()
        self.assertIn("window.DGRAPH_SHARDS", index)
        sections = set()
        for fname in shards:
            path = os.path.join(out, fname)
            self.assertLess(os.path.getsize(path), 512 * 1024)
            content = open(path, encoding="utf-8").read()
            self.assertTrue(content.startswith('window.DGRAPH_PARTS.push(["'))
            sections.add(fname.split("-", 2)[2].rsplit(".", 1)[0])
        for expected in ("categories", "claims", "topics", "works", "qa", "excerpts", "work_topic", "category_topic"):
            self.assertIn(expected, sections, "missing viewer section " + expected)
        # qa rows carry what the panel needs
        qa_shard = [f for f in shards if f.endswith("-qa.js")][0]
        body = open(os.path.join(out, qa_shard), encoding="utf-8").read()
        for field in ('"q":', '"work":', '"topics":', '"starred":', '"path":'):
            self.assertIn(field, body)
    def test_deterministic_rebuild(self):
        result2 = build.build_graph(root=self.tmp, verbose=False)
        out2 = os.path.join(self.tmp, "graph_out2")
        build.write_graph(result2, out_dir=out2, root=self.tmp)
        for sub in ("nodes/sources.jsonl", "nodes/topics.jsonl", "edges/work_topic.jsonl", "build-manifest.json"):
            with open(os.path.join(self.out_dir, sub)) as f1, open(os.path.join(out2, sub)) as f2:
                self.assertEqual(f1.read(), f2.read(), "non-deterministic output: " + sub)

if __name__ == "__main__":
    unittest.main()
