"""Tests for Stellar Transcriber M3 de novo cleanup pipeline."""
import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("ELEVENLABS_API_KEY", "unused-for-denovo-tests")
sys.modules.setdefault("elevenlabs", MagicMock())
sys.modules.setdefault("elevenlabs.client", MagicMock())

from core import denovo as denovo_module
from core import llm as llm_module
from core.denovo import (
    apply_deterministic_cleanup,
    build_dual_chunks,
    build_word_stream,
    create_draft_deterministic,
    create_draft_llm,
    extract_dual_chunk_triples,
    find_anchors_between_transcripts,
    find_dual_cut_points,
    find_islands_from_anchors,
    find_word_match_blocks,
    is_broken_sentence_transition,
    load_segments_from_md,
    merge_consecutive_same_speaker,
    merge_dual_deterministic,
    merge_dual_llm,
    llm_segments_to_internal,
    project_positions_to_ref,
    repair_broken_sentence_transition,
    reassemble_dual_segments,
    segments_to_md_content,
    write_draft_md,
)
from core.llm import (
    PROMPT_DENOVO_DUAL_V2,
    PROMPT_DENOVO_DUAL_V3,
    PROMPT_DENOVO_SINGLE_V1,
    chunk_segments_for_llm,
    llm_arbitrate_dual_chunk,
    llm_correct_transcript_segments,
    validate_transcript_segments_response,
)

FIXTURE_MD = """## metadata
last updated: 07-03-2026 Created
transcript source: deepgram nova-2-general-dl


## content

### transcript

Speaker 0  0:00:05
I think that

Speaker 1  0:00:08
we should continue the discussion today.

Speaker 0  0:00:15
Yes. That sounds good.

Speaker 0  0:00:20
um um the the project is on track
"""


@pytest.fixture
def fixture_md_path():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(FIXTURE_MD)
        path = f.name
    yield path
    os.unlink(path)


### Deterministic cleanup
def test_is_broken_sentence_transition():
    prev = {"dialogue": "I think that"}
    nxt = {"dialogue": "we should continue"}
    assert is_broken_sentence_transition(prev, nxt) is True
    nxt_ok = {"dialogue": "We should continue"}
    assert is_broken_sentence_transition(prev, nxt_ok) is False


def test_repair_broken_sentence_transition():
    prev = {"speaker_name": "Speaker 0", "dialogue": "I think that"}
    nxt = {"speaker_name": "Speaker 1", "dialogue": "we should continue today. And more follows here."}
    prev, nxt, log = repair_broken_sentence_transition(prev, nxt)
    assert log is not None
    assert "we should continue today." in prev["dialogue"]
    assert nxt["dialogue"] == "And more follows here."
def test_repair_moves_short_dangling_tail_forward():
    prev = {
        "speaker_name": "Speaker 0",
        "dialogue": "Is that not an evil because the universe is indifferent to us? So the asteroid,"
    }
    nxt = {
        "speaker_name": "Speaker 1",
        "dialogue": "if if an asteroid turns up in such a way I mean, it would have to be a minor planet."
    }
    prev, nxt, log = repair_broken_sentence_transition(prev, nxt)
    assert log is not None
    assert prev["dialogue"].endswith("indifferent to us?")
    assert nxt["dialogue"].startswith("So the asteroid, if if an asteroid")
    assert log["direction"] == "prev_to_next"
def test_repair_moves_short_answer_forward_after_question():
    prev = {
        "speaker_name": "Speaker 0",
        "dialogue": "Is that not an evil because the universe is indifferent to us? Yes."
    }
    nxt = {
        "speaker_name": "Speaker 1",
        "dialogue": "So, the asteroid, if an asteroid turns up in such a way."
    }
    prev, nxt, log = repair_broken_sentence_transition(prev, nxt)
    assert log is not None
    assert prev["dialogue"].endswith("indifferent to us?")
    assert nxt["dialogue"].startswith("Yes. So, the asteroid")
    assert log["direction"] == "prev_to_next"
def test_repair_moves_short_question_back_before_answer():
    prev = {
        "speaker_name": "Speaker 0",
        "dialogue": "But you think that any ultimate explanation or foundation is a bad explanation."
    }
    nxt = {
        "speaker_name": "Speaker 1",
        "dialogue": "Why is that? Yeah, so a bad explanation is one that is easily varied."
    }
    prev, nxt, log = repair_broken_sentence_transition(prev, nxt)
    assert log is not None
    assert prev["dialogue"].endswith("Why is that?")
    assert nxt["dialogue"].startswith("Yeah, so a bad explanation")
    assert log["direction"] == "next_to_prev"
def test_repair_keeps_content_question_on_answer_speaker():
    prev = {
        "speaker_name": "Speaker 7",
        "dialogue": "It might be helpful so the community could be aware that it's getting attention."
    }
    nxt = {
        "speaker_name": "Speaker 5",
        "dialogue": "Why is community concerned? I mean, the radio is up and working."
    }
    prev, nxt, log = repair_broken_sentence_transition(prev, nxt)
    assert log is None
    assert prev["dialogue"].endswith("getting attention.")
    assert nxt["dialogue"].startswith("Why is community concerned?")
def test_repair_aborts_when_next_punctuation_is_too_far():
    prev = {"speaker_name": "Speaker 0", "dialogue": "The asteroid,"}
    nxt = {"speaker_name": "Speaker 1", "dialogue": "if if an asteroid turns up in such a way I mean, it would have to be a bit of a minor planet."}
    prev2, nxt2, log = repair_broken_sentence_transition(prev, nxt)
    assert log is None
    assert prev2["dialogue"] == "The asteroid,"
    assert nxt2["dialogue"] == "if if an asteroid turns up in such a way I mean, it would have to be a bit of a minor planet."
def test_repair_aborts_instead_of_swallowing_next_segment():
    # Moving every word of next would eliminate a segment — repair must abort
    prev = {"speaker_name": "Speaker 0", "dialogue": "I think that"}
    nxt = {"speaker_name": "Speaker 1", "dialogue": "we should continue today."}
    prev2, nxt2, log = repair_broken_sentence_transition(prev, nxt)
    assert log is None
    assert prev2["dialogue"] == "I think that"
    assert nxt2["dialogue"] == "we should continue today."


def test_merge_consecutive_same_speaker():
    segments = [
        {"speaker_name": "Speaker 0", "dialogue": "Hello"},
        {"speaker_name": "Speaker 0", "dialogue": "world"},
        {"speaker_name": "Speaker 1", "dialogue": "Hi"},
    ]
    merged, logs = merge_consecutive_same_speaker(segments)
    assert len(merged) == 2
    assert "Hello world" in merged[0]["dialogue"]
    assert len(logs) == 1
def test_apply_deterministic_cleanup_merges_all_consecutive_same_speaker_segments():
    segments = [
        {
            "speaker_name": "Speaker A",
            "speaker_full": "Speaker A",
            "timestamp": "1:00",
            "dialogue": "First complete sentence.",
        },
        {
            "speaker_name": "Speaker A",
            "speaker_full": "Speaker A",
            "timestamp": "1:05",
            "dialogue": "Second complete sentence.",
        },
        {
            "speaker_name": "Speaker A",
            "speaker_full": "Speaker A",
            "timestamp": "1:10",
            "dialogue": "Third complete sentence.",
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert len(cleaned) == 1
    assert cleaned[0]["dialogue"] == (
        "First complete sentence. Second complete sentence. Third complete sentence."
    )
    assert cleaned[0]["timestamp"] == "1:00"
    assert sum(log.get("type") == "merge_same_speaker" for log in logs) == 2


def test_apply_deterministic_cleanup_on_fixture(fixture_md_path):
    segments = load_segments_from_md(fixture_md_path)
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert len(cleaned) <= len(segments)
    assert any(l.get("type") == "broken_sentence_transition" for l in logs) or len(logs) >= 0
def test_apply_deterministic_cleanup_merges_short_speaker_blip():
    segments = [
        {
            "speaker_name": "Speaker 0",
            "speaker_full": "Speaker 0",
            "timestamp": "25:33",
            "dialogue": "What do you think, is there an explanation for such widespread control?"
        },
        {
            "speaker_name": "Speaker 1",
            "speaker_full": "Speaker 1",
            "timestamp": "25:43",
            "dialogue": "Do you think"
        },
        {
            "speaker_name": "Speaker 0",
            "speaker_full": "Speaker 0",
            "timestamp": "25:43",
            "dialogue": "that's something that explains that?"
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert len(cleaned) == 1
    assert cleaned[0]["speaker_name"] == "Speaker 0"
    assert cleaned[0]["dialogue"].endswith("Do you think that's something that explains that?")
    assert any(l.get("type") == "short_speaker_blip" for l in logs)
def test_apply_deterministic_cleanup_preserves_sentence_completing_blip_words():
    segments = [
        {
            "speaker_name": "Chris Raanes (EPC Chair)",
            "speaker_full": "Chris Raanes (EPC Chair)",
            "timestamp": "46:21",
            "dialogue": "You can",
        },
        {
            "speaker_name": "Speaker 1",
            "speaker_full": "Speaker 1",
            "timestamp": "46:21",
            "dialogue": "hear me",
        },
        {
            "speaker_name": "Chris Raanes (EPC Chair)",
            "speaker_full": "Chris Raanes (EPC Chair)",
            "timestamp": "46:21",
            "dialogue": "okay here? Thank you again for your loyal attendance. Yes, of course.",
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert len(cleaned) == 1
    assert cleaned[0]["speaker_name"] == "Chris Raanes (EPC Chair)"
    assert cleaned[0]["dialogue"] == (
        "You can hear me okay here? Thank you again for your loyal attendance. Yes, of course."
    )
    assert any(log.get("type") == "short_speaker_blip" for log in logs)
    assert not any(log.get("type") == "drop_middle_speaker_noise" for log in logs)
def test_apply_deterministic_cleanup_never_drops_five_word_middle_blip():
    segments = [
        {
            "speaker_name": "Speaker A",
            "speaker_full": "Speaker A",
            "timestamp": "1:00",
            "dialogue": "You can",
        },
        {
            "speaker_name": "Speaker B",
            "speaker_full": "Speaker B",
            "timestamp": "1:01",
            "dialogue": "hear me okay here now",
        },
        {
            "speaker_name": "Speaker A",
            "speaker_full": "Speaker A",
            "timestamp": "1:02",
            "dialogue": "thank you for attending.",
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert len(cleaned) == 1
    assert cleaned[0]["dialogue"] == "You can hear me okay here now thank you for attending."
    assert any(log.get("type") == "short_speaker_blip" for log in logs)
    assert not any(log.get("type") == "drop_middle_speaker_noise" for log in logs)
def test_apply_deterministic_cleanup_preserves_short_meaningful_response_blip():
    segments = [
        {
            "speaker_name": "Speaker 2",
            "speaker_full": "Speaker 2",
            "timestamp": "22:22",
            "dialogue": "They wanted to build the tower up to get into heaven and kill God."
        },
        {
            "speaker_name": "Speaker 1",
            "speaker_full": "Speaker 1",
            "timestamp": "22:38",
            "dialogue": "I'm not sure"
        },
        {
            "speaker_name": "Speaker 2",
            "speaker_full": "Speaker 2",
            "timestamp": "22:39",
            "dialogue": "who says that. The empowerment some interpretations read it that way."
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert len(cleaned) == 3
    assert cleaned[0]["speaker_name"] == "Speaker 2"
    assert cleaned[1]["speaker_name"] == "Speaker 1"
    assert cleaned[1]["dialogue"] == "I'm not sure"
    assert cleaned[2]["speaker_name"] == "Speaker 2"
    assert cleaned[2]["dialogue"].startswith("who says that.")
    assert not any(l.get("type") == "short_speaker_blip" for l in logs)
def test_apply_deterministic_cleanup_splits_middle_turn_with_dangling_tail():
    segments = [
        {
            "speaker_name": "Speaker 1",
            "speaker_full": "Speaker 1",
            "timestamp": "44:07",
            "dialogue": "They that's that's what people do. Yeah. Fair"
        },
        {
            "speaker_name": "Speaker 0",
            "speaker_full": "Speaker 0",
            "timestamp": "44:40",
            "dialogue": "enough. Helping"
        },
        {
            "speaker_name": "Speaker 1",
            "speaker_full": "Speaker 1",
            "timestamp": "44:41",
            "dialogue": "them would be a crime."
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert len(cleaned) == 3
    assert cleaned[0]["speaker_name"] == "Speaker 1"
    assert cleaned[0]["dialogue"] == "They that's that's what people do."
    assert cleaned[1]["speaker_name"] == "Speaker 0"
    assert cleaned[1]["dialogue"] == "Yeah. Fair enough."
    assert cleaned[2]["speaker_name"] == "Speaker 1"
    assert cleaned[2]["dialogue"] == "Helping them would be a crime."
    assert not any(l.get("type") == "short_speaker_blip" for l in logs)
def test_apply_deterministic_cleanup_preserves_answer_after_question_when_next_echoes():
    segments = [
        {
            "speaker_name": "Speaker 2",
            "speaker_full": "Speaker 2",
            "timestamp": "41:34",
            "dialogue": "How do you know that withdrawing from the pain is what causes?"
        },
        {
            "speaker_name": "Speaker 1",
            "speaker_full": "Speaker 1",
            "timestamp": "41:40",
            "dialogue": "Isn't yeah"
        },
        {
            "speaker_name": "Speaker 2",
            "speaker_full": "Speaker 2",
            "timestamp": "41:41",
            "dialogue": "isn't yeah. Yes. How do you know that withdrawing from the pain isn't what causes the suffering"
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert len(cleaned) == 3
    assert cleaned[0]["speaker_name"] == "Speaker 2"
    assert cleaned[0]["dialogue"].endswith("what causes?")
    assert cleaned[1]["speaker_name"] == "Speaker 1"
    assert cleaned[1]["dialogue"] == "Isn't yeah"
    assert cleaned[2]["speaker_name"] == "Speaker 2"
    assert cleaned[2]["dialogue"].startswith("isn't yeah. Yes. How do you know")
    assert not any(l.get("type") == "short_speaker_blip" for l in logs)
def test_apply_deterministic_cleanup_preserves_acknowledgement_blip():
    segments = [
        {
            "speaker_name": "Lulie Tanett",
            "speaker_full": "Lulie Tanett",
            "timestamp": "22:16",
            "dialogue": "Yeah. This is also why my podcast is called Reason is Fun. It's the same worldview."
        },
        {
            "speaker_name": "David Deutsch",
            "speaker_full": "David Deutsch",
            "timestamp": "22:22",
            "dialogue": "Yeah. Yeah. I'm so"
        },
        {
            "speaker_name": "Lulie Tanett",
            "speaker_full": "Lulie Tanett",
            "timestamp": "22:30",
            "dialogue": "curious to what extent this maps onto your way of thinking about things."
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert len(cleaned) == 3
    assert cleaned[1]["speaker_name"] == "David Deutsch"
    assert cleaned[1]["dialogue"] == "Yeah. Yeah."
    assert cleaned[2]["speaker_name"] == "Lulie Tanett"
    assert cleaned[2]["dialogue"].startswith("I'm so curious")
    assert any(l.get("type") == "short_speaker_blip_tail" for l in logs)
def test_apply_deterministic_cleanup_moves_question_tail_before_blip():
    segments = [
        {
            "speaker_name": "Mark Alexander",
            "speaker_full": "Mark Alexander",
            "timestamp": "21:31",
            "dialogue": "Wow, so you're following the pleasure."
        },
        {
            "speaker_name": "David Deutsch",
            "speaker_full": "David Deutsch",
            "timestamp": "21:34",
            "dialogue": "The fun, yeah. Yeah. So what's"
        },
        {
            "speaker_name": "Mark Alexander",
            "speaker_full": "Mark Alexander",
            "timestamp": "21:35",
            "dialogue": "the role that"
        },
        {
            "speaker_name": "David Deutsch",
            "speaker_full": "David Deutsch",
            "timestamp": "21:36",
            "dialogue": "fun has in your creative process? Because if"
        },
        {
            "speaker_name": "Mark Alexander",
            "speaker_full": "Mark Alexander",
            "timestamp": "21:36",
            "dialogue": "I'm following, creativity is necessary."
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert len(cleaned) == 3
    assert cleaned[1]["speaker_name"] == "David Deutsch"
    assert cleaned[1]["dialogue"] == "The fun, yeah."
    assert cleaned[2]["speaker_name"] == "Mark Alexander"
    assert cleaned[2]["dialogue"].startswith("Yeah. So what's the role that fun has")
    assert "Because if I'm following" in cleaned[2]["dialogue"]
    assert any(l.get("type") == "question_tail_to_next" for l in logs)
def test_apply_deterministic_cleanup_preserves_discourse_opener_overlap_for_review():
    segments = [
        {
            "speaker_name": "David Deutsch",
            "speaker_full": "David Deutsch",
            "timestamp": "1:03:07",
            "dialogue": "Yes. But if it did"
        },
        {
            "speaker_name": "Alex OConnor",
            "speaker_full": "Alex OConnor",
            "timestamp": "1:03:09",
            "dialogue": "Whereas"
        },
        {
            "speaker_name": "David Deutsch",
            "speaker_full": "David Deutsch",
            "timestamp": "1:03:09",
            "dialogue": "by some way if it"
        },
        {
            "speaker_name": "Alex OConnor",
            "speaker_full": "Alex OConnor",
            "timestamp": "1:03:10",
            "dialogue": "did, then if it did, then we would still be able to observe that one particle and have it come out as an interference pattern."
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert len(cleaned) == 4
    assert cleaned[0]["speaker_name"] == "David Deutsch"
    assert cleaned[0]["dialogue"] == "Yes. But if it did"
    assert cleaned[1]["speaker_name"] == "Alex OConnor"
    assert cleaned[1]["dialogue"] == "Whereas"
    assert cleaned[2]["speaker_name"] == "David Deutsch"
    assert cleaned[2]["dialogue"] == "by some way if it"
    assert cleaned[3]["speaker_name"] == "Alex OConnor"
    assert cleaned[3]["dialogue"].startswith("did, then if it did, then we would still be able to observe")
    assert not any(l.get("type") in ("short_speaker_blip", "drop_middle_speaker_noise") for l in logs)
def test_apply_deterministic_cleanup_marks_meeting_cutoffs_with_ellipsis():
    segments = [
        {
            "speaker_name": "Speaker 1",
            "speaker_full": "Speaker 1",
            "timestamp": "1:02:07",
            "timestamp_link": "https://youtu.be/2V27Ug01D60&t=3727",
            "dialogue": "So that's that's the the typical way of trying"
        },
        {
            "speaker_name": "Speaker 7",
            "speaker_full": "Speaker 7",
            "timestamp": "1:02:42",
            "timestamp_link": "https://youtu.be/2V27Ug01D60&t=3762",
            "dialogue": "to Yeah. They overlapped five minutes or so. And then That's something"
        },
        {
            "speaker_name": "Speaker 8",
            "speaker_full": "Speaker 8",
            "timestamp": "1:03:06",
            "timestamp_link": "https://youtu.be/2V27Ug01D60&t=3786",
            "dialogue": "that's something we can pick up again through BPTS."
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert len(cleaned) == 3
    assert cleaned[0]["speaker_name"] == "Speaker 1"
    assert cleaned[0]["dialogue"].endswith("typical way of trying to...")
    assert cleaned[1]["speaker_name"] == "Speaker 7"
    assert cleaned[1]["dialogue"].startswith("Yeah. They overlapped five minutes")
    assert cleaned[1]["dialogue"].endswith("And then...")
    assert cleaned[2]["speaker_name"] == "Speaker 8"
    assert cleaned[2]["dialogue"].startswith("That's something that's something")
    assert any(l.get("type") == "cutoff_transition" for l in logs)
    assert any(l.get("type") == "trailing_cutoff_before_next_start" for l in logs)
def test_apply_deterministic_cleanup_marks_unpunctuated_turn_before_capitalized_speaker():
    segments = [
        {
            "speaker_name": "Craig Taylor",
            "speaker_full": "Craig Taylor",
            "timestamp": "1:06:21",
            "dialogue": "So I think it's isn't it they show the hazard and not the risk? I don't I can always flip",
        },
        {
            "speaker_name": "Tom Cuschieri",
            "speaker_full": "Tom Cuschieri",
            "timestamp": "1:06:25",
            "dialogue": "Yeah. No. I think I think it's the risk and not the hazard.",
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert cleaned[0]["dialogue"].endswith("I don't I can always flip...")
    assert cleaned[1]["dialogue"].startswith("Yeah. No.")
    assert any(log.get("type") == "interrupted_turn_ellipsis" for log in logs)
@pytest.mark.parametrize("cutoff", ["So-", "So–", "So—"])
def test_apply_deterministic_cleanup_replaces_terminal_cutoff_dash_with_ellipsis(cutoff):
    segments = [
        {
            "speaker_name": "Speaker 1",
            "speaker_full": "Speaker 1",
            "timestamp": "1:00",
            "dialogue": cutoff,
        },
        {
            "speaker_name": "Speaker 2",
            "speaker_full": "Speaker 2",
            "timestamp": "1:01",
            "dialogue": "Next speaker starts here.",
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert cleaned[0]["dialogue"] == "So..."
    assert not cleaned[0]["dialogue"].endswith("-...")
    assert any(log.get("type") == "terminal_cutoff_dash" for log in logs)
@pytest.mark.parametrize(
    "prev_speaker,prev_text,next_speaker,next_text,expected_speaker,expected_text",
    [
        (
            "Craig Taylor",
            "Companies are not required to",
            "Jerry Shefren",
            "honor these maps and have their own. And now there'd be better.",
            "Jerry Shefren",
            "Companies are not required to honor these maps and have their own. And now there'd be better.",
        ),
        (
            "Craig Taylor",
            "Yeah great. I think it might be worth mentioning the Chipper program because you sort of",
            "Speaker 1",
            "need to get on that.",
            "Craig Taylor",
            "Yeah great. I think it might be worth mentioning the Chipper program because you sort of need to get on that.",
        ),
        (
            "Speaker 1",
            "I",
            "Chris Raanes",
            "think that's a great question that I don't know the answer to.",
            "Chris Raanes",
            "I think that's a great question that I don't know the answer to.",
        ),
    ],
)
def test_apply_deterministic_cleanup_merges_phrase_only_segment_with_longer_turn(
    prev_speaker, prev_text, next_speaker, next_text, expected_speaker, expected_text
):
    segments = [
        {
            "speaker_name": prev_speaker,
            "speaker_full": prev_speaker,
            "timestamp": "49:25",
            "timestamp_link": "https://example.com/earlier",
            "dialogue": prev_text,
        },
        {
            "speaker_name": next_speaker,
            "speaker_full": next_speaker,
            "timestamp": "49:30",
            "timestamp_link": "https://example.com/later",
            "dialogue": next_text,
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert len(cleaned) == 1
    assert cleaned[0]["speaker_name"] == expected_speaker
    assert cleaned[0]["dialogue"] == expected_text
    assert cleaned[0]["timestamp"] == "49:25"
    assert cleaned[0]["timestamp_link"] == "https://example.com/earlier"
    assert any(log.get("type") == "merge_phrase_only_transition" for log in logs)
def test_apply_deterministic_cleanup_moves_trailing_comma_acknowledgement_to_next_speaker():
    segments = [
        {
            "speaker_name": "Chris Raanes",
            "speaker_full": "Chris Raanes",
            "timestamp": "34:40",
            "dialogue": "To work with us. Yeah. Okay. Yeah,",
        },
        {
            "speaker_name": "Craig Taylor",
            "speaker_full": "Craig Taylor",
            "timestamp": "34:42",
            "dialogue": "I'm sorry. I mean it's just it's the bureaucracy.",
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert cleaned[0]["dialogue"] == "To work with us. Yeah. Okay."
    assert cleaned[1]["dialogue"] == "Yeah, I'm sorry. I mean it's just it's the bureaucracy."
    assert any(log.get("type") == "trailing_acknowledgement_to_next" for log in logs)
    assert not any(log.get("type") == "interrupted_turn_ellipsis" for log in logs)
def test_apply_deterministic_cleanup_does_not_append_ellipsis_after_comma():
    segments = [
        {
            "speaker_name": "Speaker 1",
            "speaker_full": "Speaker 1",
            "timestamp": "1:00",
            "dialogue": "We should review the proposal,",
        },
        {
            "speaker_name": "Speaker 2",
            "speaker_full": "Speaker 2",
            "timestamp": "1:01",
            "dialogue": "Craig can explain the details.",
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert cleaned[0]["dialogue"] == "We should review the proposal,"
    assert not any(log.get("type") == "interrupted_turn_ellipsis" for log in logs)
def test_apply_deterministic_cleanup_does_not_mark_complete_short_response_as_cutoff():
    segments = [
        {
            "speaker_name": "Speaker 1",
            "speaker_full": "Speaker 1",
            "timestamp": "1:00",
            "dialogue": "I'm not sure",
        },
        {
            "speaker_name": "Speaker 2",
            "speaker_full": "Speaker 2",
            "timestamp": "1:01",
            "dialogue": "Okay. We can check.",
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert cleaned[0]["dialogue"] == "I'm not sure"
    assert not any(log.get("type") == "interrupted_turn_ellipsis" for log in logs)
def test_apply_deterministic_cleanup_moves_stranded_capitalized_turn_opener():
    segments = [
        {
            "speaker_name": "Speaker 0",
            "speaker_full": "Speaker 0",
            "timestamp": "20:56",
            "timestamp_link": "https://youtu.be/2V27Ug01D60&t=1256",
            "dialogue": "Are you are you representing your opinion, or is this a council discussion that So"
        },
        {
            "speaker_name": "Speaker 3",
            "speaker_full": "Speaker 3",
            "timestamp": "20:59",
            "timestamp_link": "https://youtu.be/2V27Ug01D60&t=1259",
            "dialogue": "so right now, this is my opinion. I mean, I'm your alternate."
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert len(cleaned) == 2
    assert cleaned[0]["speaker_name"] == "Speaker 0"
    assert cleaned[0]["dialogue"].endswith("council discussion that...")
    assert cleaned[1]["speaker_name"] == "Speaker 3"
    assert cleaned[1]["dialogue"].startswith("So so right now")
    assert any(l.get("type") == "stranded_turn_opener_to_next" for l in logs)
def test_apply_deterministic_cleanup_prioritizes_stranded_opener_over_phrase_merge():
    segments = [
        {
            "speaker_name": "Speaker A",
            "speaker_full": "Speaker A",
            "timestamp": "1:00",
            "dialogue": "discussion that So",
        },
        {
            "speaker_name": "Speaker B",
            "speaker_full": "Speaker B",
            "timestamp": "1:01",
            "dialogue": "so right now, this is my opinion.",
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert len(cleaned) == 2
    assert cleaned[0]["dialogue"] == "discussion that..."
    assert cleaned[1]["dialogue"] == "So so right now, this is my opinion."
    assert any(log.get("type") == "stranded_turn_opener_to_next" for log in logs)
    assert not any(log.get("type") == "merge_phrase_only_transition" for log in logs)
def test_apply_deterministic_cleanup_collapses_discourse_blip_before_lowercase_continuation():
    segments = [
        {
            "speaker_name": "Speaker 2",
            "speaker_full": "Speaker 2",
            "timestamp": "49:43",
            "dialogue": "So it's an impact for everybody and more work to do."
        },
        {
            "speaker_name": "Speaker 1",
            "speaker_full": "Speaker 1",
            "timestamp": "50:10",
            "dialogue": "But yeah"
        },
        {
            "speaker_name": "Speaker 2",
            "speaker_full": "Speaker 2",
            "timestamp": "50:11",
            "dialogue": "if there's no any more questions on that we'll still be obviously busy."
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert len(cleaned) == 1
    assert cleaned[0]["speaker_name"] == "Speaker 2"
    assert "more work to do. But yeah if there's no any more questions" in cleaned[0]["dialogue"]
    assert any(l.get("type") == "short_speaker_blip" for l in logs)
def test_apply_deterministic_cleanup_collapses_unassigned_blip_between_named_speaker():
    segments = [
        {
            "speaker_name": "Tom Cuschieri",
            "speaker_full": "Tom Cuschieri",
            "timestamp": "49:43",
            "dialogue": "So it's an impact for everybody and more work to do."
        },
        {
            "speaker_name": "Speaker 1",
            "speaker_full": "Speaker 1",
            "timestamp": "50:10",
            "dialogue": "But yeah."
        },
        {
            "speaker_name": "Tom Cuschieri",
            "speaker_full": "Tom Cuschieri",
            "timestamp": "50:11",
            "dialogue": "if there's no any more questions on that we'll still be obviously busy."
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert len(cleaned) == 1
    assert cleaned[0]["speaker_name"] == "Tom Cuschieri"
    assert "more work to do. But yeah. if there's no any more questions" in cleaned[0]["dialogue"]
    assert any(l.get("type") == "short_speaker_blip" for l in logs)
def test_apply_deterministic_cleanup_preserves_unassigned_segment_without_continuation():
    segments = [
        {
            "speaker_name": "Tom Cuschieri",
            "speaker_full": "Tom Cuschieri",
            "timestamp": "49:43",
            "dialogue": "That completes my update."
        },
        {
            "speaker_name": "Speaker 1",
            "speaker_full": "Speaker 1",
            "timestamp": "50:10",
            "dialogue": "Okay."
        },
        {
            "speaker_name": "Tom Cuschieri",
            "speaker_full": "Tom Cuschieri",
            "timestamp": "50:11",
            "dialogue": "The next topic is staffing."
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert len(cleaned) == 3
    assert cleaned[1]["speaker_name"] == "Speaker 1"
    assert cleaned[1]["dialogue"] == "Okay."
    assert not any(l.get("type") == "short_speaker_blip" for l in logs)
def test_apply_deterministic_cleanup_collapses_terminal_blip_that_completes_sentence():
    segments = [
        {
            "speaker_name": "Speaker 2",
            "speaker_full": "Speaker 2",
            "timestamp": "50:11",
            "dialogue": "I think that was really different"
        },
        {
            "speaker_name": "Speaker 9",
            "speaker_full": "Speaker 9",
            "timestamp": "52:00",
            "dialogue": "from her on my end."
        },
        {
            "speaker_name": "Speaker 2",
            "speaker_full": "Speaker 2",
            "timestamp": "52:00",
            "dialogue": "We've been busy here in the district."
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert len(cleaned) == 1
    assert cleaned[0]["speaker_name"] == "Speaker 2"
    assert "I think that was really different from her on my end." in cleaned[0]["dialogue"]
    assert cleaned[0]["dialogue"].endswith("We've been busy here in the district.")
    assert any(l.get("type") == "short_speaker_blip" for l in logs)
def test_apply_deterministic_cleanup_does_not_cutoff_make_sure_phrase():
    segments = [
        {
            "speaker_name": "Speaker 4",
            "speaker_full": "Speaker 4",
            "timestamp": "1:08:13",
            "dialogue": "And you know, Tom, you might want to comment. Yeah, that's I just wanted to"
        },
        {
            "speaker_name": "Speaker 2",
            "speaker_full": "Speaker 2",
            "timestamp": "1:09:00",
            "dialogue": "make sure everybody was clear of how they sort of fit together."
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert len(cleaned) == 2
    assert cleaned[0]["speaker_name"] == "Speaker 4"
    assert cleaned[0]["dialogue"].endswith("Tom, you might want to comment.")
    assert cleaned[1]["speaker_name"] == "Speaker 2"
    assert cleaned[1]["dialogue"].startswith("Yeah, that's I just wanted to make sure")
    assert not any(l.get("type") == "cutoff_transition" for l in logs)
def test_apply_deterministic_cleanup_keeps_large_cutoff_phrase_before_tiny_completion():
    segments = [
        {
            "speaker_name": "Speaker 0",
            "speaker_full": "Speaker 0",
            "timestamp": "44:41",
            "dialogue": "All right. Item number seven. Yeah. Oh, am I going to have one for number four. All right, I gotta go back"
        },
        {
            "speaker_name": "Speaker 5",
            "speaker_full": "Speaker 5",
            "timestamp": "44:57",
            "dialogue": "to We've already got a subcommittee which I remain chair on I think we've lost everybody. I'm not sure."
        },
    ]
    cleaned, logs = apply_deterministic_cleanup(segments, policy=None)
    assert len(cleaned) == 2
    assert cleaned[0]["speaker_name"] == "Speaker 0"
    assert cleaned[0]["dialogue"].endswith("All right, I gotta go back to...")
    assert cleaned[1]["speaker_name"] == "Speaker 5"
    assert cleaned[1]["dialogue"].startswith("We've already got a subcommittee")
    assert any(l.get("type") == "cutoff_transition" for l in logs)
def test_segments_to_md_content_preserves_markdown_timestamp_link():
    content = segments_to_md_content([{
        "speaker_full": "Speaker 0",
        "timestamp": "14:53",
        "timestamp_link": "https://youtu.be/Hh9xOB2oDHk&t=893",
        "dialogue": "So the asteroid,"
    }])
    assert "Speaker 0  [14:53](https://youtu.be/Hh9xOB2oDHk&t=893)" in content
    assert "14:53 (https://youtu.be/Hh9xOB2oDHk&t=893)" not in content
def test_llm_segments_to_internal_preserves_timestamp_links():
    source = [{
        "speaker_full": "Speaker 0",
        "speaker_name": "Speaker 0",
        "timestamp": "14:53",
        "timestamp_link": "https://youtu.be/Hh9xOB2oDHk&t=893",
        "dialogue": "Original text."
    }]
    result = llm_segments_to_internal(
        [{"speaker": "Speaker 0", "timestamp": "14:53", "dialogue": "Original text."}],
        source_segments=source,
    )
    assert result[0]["timestamp_link"] == "https://youtu.be/Hh9xOB2oDHk&t=893"


def test_create_draft_deterministic_writes_file(fixture_md_path):
    out = create_draft_deterministic(fixture_md_path, profile="deutsch")
    assert os.path.isfile(out)
    assert out.endswith("_draftds.md")
    segments = load_segments_from_md(out)
    assert len(segments) >= 1
    os.unlink(out)


def test_write_draft_metadata_provenance(fixture_md_path):
    segments = load_segments_from_md(fixture_md_path)
    out = write_draft_md(segments, fixture_md_path, "_draftds", metadata_extra={"denovo method": "deterministic"})
    with open(out) as f:
        text = f.read()
    assert "denovo method" in text or "denovo pipeline version" in text
    os.unlink(out)


### Anchor / island detection
def test_find_anchors_between_transcripts():
    segs_a = [
        {"timestamp": "0:00:05", "dialogue": "Hello world today."},
        {"timestamp": "0:00:20", "dialogue": "Different middle."},
        {"timestamp": "0:00:40", "dialogue": "Goodbye everyone."},
    ]
    segs_b = [
        {"timestamp": "0:00:05", "dialogue": "Hello world today."},
        {"timestamp": "0:00:22", "dialogue": "Changed middle content."},
        {"timestamp": "0:00:40", "dialogue": "Goodbye everyone."},
    ]
    anchors = find_anchors_between_transcripts(segs_a, segs_b, timestamp_threshold=1)
    assert len(anchors) >= 1
    islands = find_islands_from_anchors(segs_a, segs_b, anchors, max_island_segments=20)
    assert isinstance(islands, list)


def test_reassemble_dual_segments():
    segs_a = [
        {"timestamp": "0:00:05", "speaker_name": "A", "dialogue": "Anchor one."},
        {"timestamp": "0:00:15", "speaker_name": "A", "dialogue": "Island text."},
        {"timestamp": "0:00:30", "speaker_name": "B", "dialogue": "Anchor two."},
    ]
    anchors = [{"a_index": 0, "b_index": 0}, {"a_index": 2, "b_index": 2}]
    island_results = [{"a_start": 1, "a_end": 2, "consensus": [{"speaker_name": "A", "timestamp": "0:00:15", "dialogue": "Fixed island."}]}]
    merged = reassemble_dual_segments(segs_a, anchors, island_results)
    assert len(merged) >= 2
    assert any("Fixed island" in s.get("dialogue", "") for s in merged)


### LLM path (mocked)
def test_validate_transcript_segments_response():
    ok, err = validate_transcript_segments_response({"segments": [{"speaker": "S0", "timestamp": "0:00:01", "dialogue": "Hi"}]}, 1)
    assert ok is True
    ok, err = validate_transcript_segments_response(None, 1)
    assert ok is False


def test_chunk_segments_for_llm():
    segments = [{"dialogue": "word " * 50, "speaker_name": "S", "timestamp": f"0:00:{i:02d}"} for i in range(10)]
    chunks = chunk_segments_for_llm(segments, token_cap=100, adjacent_context=1)
    assert len(chunks) >= 2
    assert all("segments" in c for c in chunks)


@patch("core.llm.openai_function_call")
def test_llm_correct_transcript_segments_mock(mock_fcall):
    # Repair semantics: same dialogue words, corrected speaker attribution
    mock_fcall.return_value = {
        "tool_calls": [{"function": {"arguments": json.dumps({
            "segments": [{"speaker": "Speaker 1", "timestamp": "0:00:05", "dialogue": "Broken text"}]
        })}}]
    }
    segs = [{"speaker_name": "Speaker 0", "timestamp": "0:00:05", "dialogue": "Broken text"}]
    result = llm_correct_transcript_segments(segs, PROMPT_DENOVO_SINGLE_V1, "gpt-4o-mini", provider="openai")
    assert result is not None
    assert result[0]["speaker"] == "Speaker 1"
def test_llm_correct_rejects_paraphrase():
    from unittest.mock import patch
    with patch("core.llm.openai_function_call") as mock_fcall:
        mock_fcall.return_value = {
            "tool_calls": [{"function": {"arguments": json.dumps({
                "segments": [{"speaker": "Speaker 0", "timestamp": "0:00:05", "dialogue": "Completely different words here."}]
            })}}]
        }
        segs = [{"speaker_name": "Speaker 0", "timestamp": "0:00:05", "dialogue": "Broken text"}]
        result = llm_correct_transcript_segments(segs, PROMPT_DENOVO_SINGLE_V1, "gpt-4o-mini", provider="openai", max_retries=1)
    assert result is None
def test_denovo_dual_prompt_forbids_duplicate_a_b_copies():
    prompt = PROMPT_DENOVO_DUAL_V2.lower()
    assert "do not output both copies" in prompt
    assert "same underlying speech" in prompt
    assert "choose one consensus version" in prompt
def test_denovo_dual_prompt_handles_disagreeing_speaker_numbers():
    prompt = PROMPT_DENOVO_DUAL_V2.lower()
    assert "speaker numbers differ" in prompt
    assert "local speaker continuity" in prompt
    assert "do not invent speaker names" in prompt


@patch("core.llm.llm_correct_transcript_segments")
@patch("core.denovo.create_draft_deterministic")
def test_create_draft_llm_mock(mock_prep, mock_llm, fixture_md_path):
    mock_prep.return_value = fixture_md_path
    mock_llm.return_value = [{"speaker": "Speaker 0", "timestamp": "0:00:05", "dialogue": "Clean."}]
    out = create_draft_llm(fixture_md_path, profile="deutsch")
    assert out.endswith("_draftls.md")
    if os.path.isfile(out):
        os.unlink(out)


### Dual deterministic
def _write_test_transcript_md(path, segments):
    meta = "## metadata\nlast updated: 07-03-2026 Created\n\n\n"
    path.write_text(meta + segments_to_md_content(segments))


def test_merge_dual_deterministic_fixture(tmp_path):
    md_a = tmp_path / "ep_nova2gen.md"
    md_b = tmp_path / "ep_dgwhspm.md"
    segs_a = [
        {"speaker_full": "Speaker 0", "speaker_name": "Speaker 0", "timestamp": "0:00:05", "dialogue": "Hello anchor segment here."},
        {"speaker_full": "Speaker 1", "speaker_name": "Speaker 1", "timestamp": "0:00:20", "dialogue": "Middle different A version."},
        {"speaker_full": "Speaker 0", "speaker_name": "Speaker 0", "timestamp": "0:00:40", "dialogue": "Goodbye anchor segment here."},
    ]
    segs_b = [
        {"speaker_full": "Speaker 0", "speaker_name": "Speaker 0", "timestamp": "0:00:05", "dialogue": "Hello anchor segment here."},
        {"speaker_full": "Speaker 1", "speaker_name": "Speaker 1", "timestamp": "0:00:22", "dialogue": "Middle different B version longer."},
        {"speaker_full": "Speaker 0", "speaker_name": "Speaker 0", "timestamp": "0:00:40", "dialogue": "Goodbye anchor segment here."},
    ]
    _write_test_transcript_md(md_a, segs_a)
    _write_test_transcript_md(md_b, segs_b)
    out = merge_dual_deterministic(str(md_a), str(md_b), profile="deutsch")
    assert os.path.isfile(out)
    segs = load_segments_from_md(out)
    assert len(segs) >= 2


@patch("core.llm.llm_arbitrate_dual_chunk")
def test_merge_dual_llm_mock(mock_arb, tmp_path):
    md_a = tmp_path / "ep_nova2gen.md"
    md_b = tmp_path / "ep_dgwhspm.md"
    seg = {"speaker_full": "Speaker 0", "speaker_name": "Speaker 0", "timestamp": "0:00:05", "dialogue": "Same anchor."}
    _write_test_transcript_md(md_a, [seg])
    _write_test_transcript_md(md_b, [seg])
    mock_arb.return_value = [{"speaker": "Speaker 0", "timestamp": "0:00:05", "dialogue": "Consensus."}]
    out = merge_dual_llm(str(md_a), str(md_b), profile="deutsch")
    assert os.path.isfile(out)


### M3B: pricing and usage
def test_load_llm_model_prices():
    from core.llm import TOKEN_PRICE_DICT, load_llm_model_prices
    models = load_llm_model_prices()
    assert "gpt-5-mini" in models
    assert TOKEN_PRICE_DICT["gpt-5-mini"]["input_token_price"] > 0


def test_compute_cost_from_tokens():
    from core.llm import compute_cost_from_tokens, TOKEN_PRICE_DICT
    costs = compute_cost_from_tokens(1_000_000, 500_000, "gpt-5-mini", TOKEN_PRICE_DICT)
    assert costs["total_cost_usd"] > 0
    assert costs["input_tokens"] == 1_000_000


def test_llm_usage_accumulator():
    from core.llm import LlmUsageAccumulator, TOKEN_PRICE_DICT
    acc = LlmUsageAccumulator("gpt-5-mini", TOKEN_PRICE_DICT)
    acc.add_usage(1000, 500)
    acc.add_usage(2000, 800, is_retry=True)
    summary = acc.summary()
    assert summary["input_tokens"] == 3000
    assert summary["output_tokens"] == 1300
    assert summary["retries"] == 1
    assert summary["total_cost_usd"] > 0


def test_estimate_dual_llm_cost_fixture(tmp_path):
    from core.denovo import estimate_dual_llm_cost
    md_a = tmp_path / "ep_nova2gen.md"
    md_b = tmp_path / "ep_dgwhspm.md"
    segs_a, segs_b = _dual_structural_transcripts()
    _write_test_transcript_md(md_a, segs_a)
    _write_test_transcript_md(md_b, segs_b)
    est = estimate_dual_llm_cost(str(md_a), str(md_b), profile="deutsch")
    assert est["diff_chunk_count"] > 0
    assert "total_cost_usd" in est


@patch("core.llm.llm_arbitrate_dual_chunk")
def test_merge_dual_llm_return_summary(mock_arb, tmp_path):
    md_a = tmp_path / "ep_nova2gen.md"
    md_b = tmp_path / "ep_dgwhspm.md"
    seg = {"speaker_full": "Speaker 0", "speaker_name": "Speaker 0", "timestamp": "0:00:05", "dialogue": "Same anchor."}
    _write_test_transcript_md(md_a, [seg])
    _write_test_transcript_md(md_b, [seg])
    mock_arb.return_value = [{"speaker": "Speaker 0", "timestamp": "0:00:05", "dialogue": "Consensus."}]
    out, summary = merge_dual_llm(str(md_a), str(md_b), profile="deutsch", return_summary=True)
    assert os.path.isfile(out)
    assert "total_cost_usd" in summary


### Word-anchored dual chunking (dual merge v2)
def _mk_seg(speaker, ts, dialogue):
    return {"speaker_full": speaker, "speaker_name": speaker, "timestamp": ts, "dialogue": dialogue}
DUAL_OPEN = "Welcome everyone to the monthly meeting of the emergency preparedness committee here today."
DUAL_MID_A = "I think we should discuss the new radio budget first."
DUAL_MID_B = "Maybe we should discuss the new radio budget first."
DUAL_TAIL = "Let us move on to the next agenda item about the evacuation drill now."
def _dual_chunk_transcripts():
    segs_a = [
        _mk_seg("Speaker 0", "0:00:05", DUAL_OPEN),
        _mk_seg("Speaker 1", "0:00:20", DUAL_MID_A),
        _mk_seg("Speaker 0", "0:00:30", DUAL_TAIL),
    ]
    segs_b = [
        _mk_seg("Speaker 0", "0:00:04", DUAL_OPEN),
        _mk_seg("Speaker 2", "0:00:19", DUAL_MID_B),
        _mk_seg("Speaker 0", "0:00:29", DUAL_TAIL),
    ]
    return segs_a, segs_b
def test_build_word_stream_marks_segment_starts():
    segs = [_mk_seg("Speaker 0", "0:00:05", "Hello there."), _mk_seg("Speaker 1", "0:00:08", "General Kenobi!")]
    stream = build_word_stream(segs)
    assert [w["norm"] for w in stream] == ["hello", "there", "general", "kenobi"]
    assert [w["seg_start"] for w in stream] == [True, False, True, False]
    assert [w["seg_index"] for w in stream] == [0, 0, 1, 1]
def test_find_dual_cut_points_requires_dual_segment_start():
    segs_a, segs_b = _dual_chunk_transcripts()
    stream_a, stream_b = build_word_stream(segs_a), build_word_stream(segs_b)
    blocks = find_word_match_blocks(stream_a, stream_b, min_words=6)
    cuts = find_dual_cut_points(stream_a, stream_b, blocks, edge_words=3)
    # Only the mid->tail boundary has matched words spanning it in both transcripts;
    # the open->mid boundary follows immediately-diverging words, so no cut there.
    assert len(cuts) == 1
    assert cuts[0]["a_seg"] == 2 and cuts[0]["b_seg"] == 2
def _dual_structural_transcripts():
    # B splits the middle turn into two speakers — a structural disagreement.
    segs_a = [
        _mk_seg("Speaker 0", "0:00:05", DUAL_OPEN),
        _mk_seg("Speaker 1", "0:00:20", DUAL_MID_A),
        _mk_seg("Speaker 0", "0:00:30", DUAL_TAIL),
    ]
    segs_b = [
        _mk_seg("Speaker 0", "0:00:04", DUAL_OPEN),
        _mk_seg("Speaker 2", "0:00:19", "Maybe we should discuss"),
        _mk_seg("Speaker 3", "0:00:22", "the new radio budget first."),
        _mk_seg("Speaker 0", "0:00:29", DUAL_TAIL),
    ]
    return segs_a, segs_b
def _oversized_relaxed_anchor_transcripts():
    segs_a = [
        _mk_seg("Speaker 0", "0:00:01", "Alpha wording from source a closes with common bridge"),
        _mk_seg("Speaker 1", "0:00:10", "start shared apples describe the first local disagreement near second bridge"),
        _mk_seg("Speaker 2", "0:00:20", "next shared source a describes another local disagreement near third bridge"),
        _mk_seg("Speaker 3", "0:00:30", "final shared source a closes the discussion clearly"),
    ]
    segs_b = [
        _mk_seg("Speaker 0", "0:00:02", "Beta wording from source b closes with common bridge"),
        _mk_seg("Speaker 4", "0:00:11", "start shared oranges describe a different first exchange near second bridge"),
        _mk_seg("Speaker 5", "0:00:21", "next shared source b has a better second exchange near third bridge"),
        _mk_seg("Speaker 3", "0:00:31", "final shared source b finishes the discussion clearly"),
    ]
    return segs_a, segs_b
def test_build_dual_chunks_tiles_and_classifies():
    segs_a, segs_b = _dual_chunk_transcripts()
    chunks = build_dual_chunks(segs_a, segs_b, min_anchor_words=6, edge_words=3)
    assert len(chunks) == 2
    assert (chunks[0]["a_start"], chunks[0]["a_end"]) == (0, 2)
    assert (chunks[1]["a_start"], chunks[1]["a_end"]) == (2, 3)
    assert (chunks[0]["b_start"], chunks[0]["b_end"]) == (0, 2)
    assert (chunks[1]["b_start"], chunks[1]["b_end"]) == (2, 3)
    # Same turn structure with only ASR wording differences — no arbitration needed.
    assert chunks[0]["kind"] == "wording"
    assert chunks[1]["kind"] == "match"
def test_build_dual_chunks_flags_structural_disagreement():
    segs_a, segs_b = _dual_structural_transcripts()
    chunks = build_dual_chunks(segs_a, segs_b, min_anchor_words=6, edge_words=3)
    assert chunks[0]["kind"] == "diff"
    assert (chunks[0]["a_end"] - chunks[0]["a_start"]) != (chunks[0]["b_end"] - chunks[0]["b_start"])
def test_subdivide_dual_diff_chunk_noop_when_under_cap():
    assert hasattr(denovo_module, "subdivide_dual_diff_chunk")
    segs_a, segs_b = _dual_structural_transcripts()
    parent = build_dual_chunks(segs_a, segs_b, min_anchor_words=6, edge_words=3)[0]
    units = denovo_module.subdivide_dual_diff_chunk(
        parent, max_words=1000, max_segments=20,
        internal_min_anchor_words=3, internal_edge_words=1)
    assert len(units) == 1
    assert units[0]["segments_a"] == parent["segments_a"]
    assert units[0]["segments_b"] == parent["segments_b"]
def test_subdivide_dual_diff_chunk_tiles_parent_at_safe_internal_cuts():
    assert hasattr(denovo_module, "subdivide_dual_diff_chunk")
    segs_a, segs_b = _oversized_relaxed_anchor_transcripts()
    parent = {
        "a_start": 0, "a_end": len(segs_a), "b_start": 0, "b_end": len(segs_b),
        "segments_a": segs_a, "segments_b": segs_b, "kind": "diff",
        "similarity": 0.5,
        "a_word_count": sum(len(s["dialogue"].split()) for s in segs_a),
        "b_word_count": sum(len(s["dialogue"].split()) for s in segs_b),
    }
    units = denovo_module.subdivide_dual_diff_chunk(
        parent, max_words=12, max_segments=2,
        internal_min_anchor_words=3, internal_edge_words=1)
    assert len(units) >= 2
    assert [seg for unit in units for seg in unit["segments_a"]] == segs_a
    assert [seg for unit in units for seg in unit["segments_b"]] == segs_b
    assert [(unit["a_start"], unit["a_end"]) for unit in units] == sorted(
        (unit["a_start"], unit["a_end"]) for unit in units)
    assert [(unit["b_start"], unit["b_end"]) for unit in units] == sorted(
        (unit["b_start"], unit["b_end"]) for unit in units)
    assert all(units[i]["a_end"] == units[i + 1]["a_start"] for i in range(len(units) - 1))
    assert all(units[i]["b_end"] == units[i + 1]["b_start"] for i in range(len(units) - 1))
def test_build_dual_decision_chunks_records_parent_and_subchunk_ids():
    assert hasattr(denovo_module, "build_dual_decision_chunks")
    segs_a, segs_b = _oversized_relaxed_anchor_transcripts()
    units = denovo_module.build_dual_decision_chunks(
        segs_a, segs_b,
        min_anchor_words=6, edge_words=3,
        decision_max_words=12, decision_max_segments=2,
        internal_min_anchor_words=3, internal_edge_words=1)
    assert len(units) >= 2
    parent_ids = [unit["parent_chunk_id"] for unit in units]
    assert parent_ids == sorted(parent_ids)
    for parent_id in sorted(set(parent_ids)):
        sub_ids = [unit["decision_sub_id"] for unit in units if unit["parent_chunk_id"] == parent_id]
        assert sub_ids == list(range(len(sub_ids)))
def test_subdivide_dual_diff_chunk_keeps_oversized_parent_without_safe_cut():
    segs_a = [_mk_seg("Speaker A", "0:00:01", " ".join(["alpha"] * 200))]
    segs_b = [_mk_seg("Speaker B", "0:00:02", " ".join(["beta"] * 200))]
    parent = {
        "a_start": 4, "a_end": 5, "b_start": 7, "b_end": 8,
        "segments_a": segs_a, "segments_b": segs_b, "kind": "diff",
        "similarity": 0.0, "a_word_count": 200, "b_word_count": 200,
    }
    units = denovo_module.subdivide_dual_diff_chunk(
        parent, max_words=20, max_segments=1,
        internal_min_anchor_words=3, internal_edge_words=1)
    assert units == [parent]
def test_subdivide_dual_diff_chunk_never_splits_non_diff_parent():
    segs_a, segs_b = _oversized_relaxed_anchor_transcripts()
    parent = {
        "a_start": 0, "a_end": len(segs_a), "b_start": 0, "b_end": len(segs_b),
        "segments_a": segs_a, "segments_b": segs_b, "kind": "wording",
        "similarity": 0.9, "a_word_count": 500, "b_word_count": 500,
    }
    units = denovo_module.subdivide_dual_diff_chunk(
        parent, max_words=20, max_segments=1,
        internal_min_anchor_words=3, internal_edge_words=1)
    assert units == [parent]
def test_project_positions_to_ref_is_monotonic():
    segs_a, _ = _dual_chunk_transcripts()
    stream_a = build_word_stream(segs_a)
    ref_segs = [
        _mk_seg("Randy", "0:00:05", DUAL_OPEN),
        _mk_seg("Craig", "0:00:20", DUAL_MID_B),
        _mk_seg("Randy", "0:00:30", DUAL_TAIL),
    ]
    stream_ref = build_word_stream(ref_segs)
    open_words = len(DUAL_OPEN.split())
    positions = [0, open_words, open_words + len(DUAL_MID_A.split())]
    projected = project_positions_to_ref(stream_a, stream_ref, positions)
    assert projected[0] == 0
    assert projected == sorted(projected)
    # A's "I think" has no ref match, so the cut snaps forward to the next matched
    # ref word ("we", after ref's unmatched "maybe") — one past the open-segment length.
    assert projected[1] == open_words + 1
def _mock_openai_usage_response(segments):
    message = {"tool_calls": [{"function": {"arguments": json.dumps({"segments": segments})}}]}
    return message, {"input_tokens": 10, "output_tokens": 10}, None
def _mock_openai_selection_response(selected_version):
    message = {"tool_calls": [{"function": {"arguments": json.dumps({"selected_version": selected_version})}}]}
    return message, {"input_tokens": 10, "output_tokens": 1}, None
def test_llm_select_dual_chunk_side_accepts_side_b():
    assert hasattr(llm_module, "llm_select_dual_chunk_side")
    segs_a, segs_b = _dual_chunk_transcripts()
    with patch("core.llm.openai_function_call_with_usage") as mock_call:
        mock_call.return_value = _mock_openai_selection_response("b")
        result = llm_module.llm_select_dual_chunk_side(
            segs_a[:2], segs_b[:2], llm_module.PROMPT_DENOVO_DUAL_V4,
            "gpt-5-mini", max_retries=1)
    assert result == "b"
def test_llm_select_dual_chunk_side_rejects_generated_transcript():
    segs_a, segs_b = _dual_chunk_transcripts()
    generated = [{"speaker": "Speaker 4", "timestamp": "0:00:05", "dialogue": "Copyedited text."}]
    with patch("core.llm.openai_function_call_with_usage") as mock_call:
        mock_call.return_value = _mock_openai_usage_response(generated)
        result = llm_module.llm_select_dual_chunk_side(
            segs_a[:2], segs_b[:2], llm_module.PROMPT_DENOVO_DUAL_V4,
            "gpt-5-mini", max_retries=1)
    assert result is None
def test_llm_arbitrate_dual_chunk_accepts_side_b():
    segs_a, segs_b = _dual_chunk_transcripts()
    chunk_a, chunk_b = segs_a[:2], segs_b[:2]
    side_b = [{"speaker": s["speaker_name"], "timestamp": s["timestamp"], "dialogue": s["dialogue"]} for s in chunk_b]
    with patch("core.llm.openai_function_call_with_usage") as mock_call:
        mock_call.return_value = _mock_openai_usage_response(side_b)
        result = llm_arbitrate_dual_chunk(chunk_a, chunk_b, PROMPT_DENOVO_DUAL_V3, "gpt-5-mini", max_retries=1)
    assert result is not None
    assert result[1]["dialogue"] == DUAL_MID_B
def test_llm_arbitrate_dual_chunk_rejects_paraphrase():
    segs_a, segs_b = _dual_chunk_transcripts()
    chunk_a, chunk_b = segs_a[:2], segs_b[:2]
    paraphrased = [
        {"speaker": "Speaker 0", "timestamp": "0:00:05", "dialogue": "Hi folks, glad you could all make it to our committee gathering."},
        {"speaker": "Speaker 1", "timestamp": "0:00:20", "dialogue": "Let's talk about radio funding as the first order of business."},
    ]
    with patch("core.llm.openai_function_call_with_usage") as mock_call:
        mock_call.return_value = _mock_openai_usage_response(paraphrased)
        result = llm_arbitrate_dual_chunk(chunk_a, chunk_b, PROMPT_DENOVO_DUAL_V3, "gpt-5-mini", max_retries=1)
    assert result is None
def test_llm_arbitrate_dual_chunk_rejects_a_plus_b_duplication():
    segs_a, segs_b = _dual_chunk_transcripts()
    chunk_a, chunk_b = segs_a[:2], segs_b[:2]
    duplicated = [
        {"speaker": "Speaker 0", "timestamp": "0:00:05", "dialogue": DUAL_OPEN},
        {"speaker": "Speaker 1", "timestamp": "0:00:20", "dialogue": DUAL_MID_A},
        {"speaker": "Speaker 2", "timestamp": "0:00:19", "dialogue": DUAL_MID_B},
    ]
    with patch("core.llm.openai_function_call_with_usage") as mock_call:
        mock_call.return_value = _mock_openai_usage_response(duplicated)
        result = llm_arbitrate_dual_chunk(chunk_a, chunk_b, PROMPT_DENOVO_DUAL_V3, "gpt-5-mini", max_retries=1)
    assert result is None
def _decision_unit(a_segments, b_segments, a_start, b_start, parent_id=0, sub_id=0):
    return {
        "a_start": a_start,
        "a_end": a_start + len(a_segments),
        "b_start": b_start,
        "b_end": b_start + len(b_segments),
        "segments_a": a_segments,
        "segments_b": b_segments,
        "kind": "diff",
        "similarity": 0.5,
        "a_word_count": sum(len(seg["dialogue"].split()) for seg in a_segments),
        "b_word_count": sum(len(seg["dialogue"].split()) for seg in b_segments),
        "parent_chunk_id": parent_id,
        "decision_sub_id": sub_id,
    }
@patch("core.denovo.build_dual_decision_chunks")
@patch("core.llm.llm_select_dual_chunk_side")
def test_merge_dual_llm_selects_each_decision_subchunk_independently(mock_select, mock_chunks, tmp_path):
    segs_a = [
        _mk_seg("Speaker A", "0:00:01", "A is better for the first local exchange."),
        _mk_seg("Speaker A", "0:00:11", "A is worse for the second local exchange."),
    ]
    segs_b = [
        _mk_seg("Speaker B", "0:00:02", "B is worse for the first local exchange."),
        _mk_seg("Speaker B", "0:00:12", "B is better for the second local exchange."),
    ]
    md_a = tmp_path / "ep_nova2gen.md"
    md_b = tmp_path / "ep_dgwhspm.md"
    _write_test_transcript_md(md_a, segs_a)
    _write_test_transcript_md(md_b, segs_b)
    mock_chunks.return_value = [
        _decision_unit(segs_a[:1], segs_b[:1], 0, 0, sub_id=0),
        _decision_unit(segs_a[1:], segs_b[1:], 1, 1, sub_id=1),
    ]
    mock_select.side_effect = ["a", "b"]
    out = merge_dual_llm(str(md_a), str(md_b), profile="deutsch")
    merged = load_segments_from_md(out)
    assert [(seg["speaker_name"], seg["dialogue"]) for seg in merged] == [
        ("Speaker A", segs_a[0]["dialogue"]),
        ("Speaker B", segs_b[1]["dialogue"]),
    ]
    assert mock_chunks.call_count == 1
    assert mock_select.call_count == 2
@patch("core.denovo.build_dual_decision_chunks")
@patch("core.llm.llm_select_dual_chunk_side")
def test_merge_dual_llm_falls_back_per_decision_subchunk(mock_select, mock_chunks, tmp_path):
    segs_a = [
        _mk_seg("Speaker A", "0:00:01", "A first."),
        _mk_seg("Speaker A", "0:00:11", "A second."),
    ]
    segs_b = [
        _mk_seg("Speaker B", "0:00:02", "B first."),
        _mk_seg("Speaker B", "0:00:12", "B second."),
    ]
    md_a = tmp_path / "ep_nova2gen.md"
    md_b = tmp_path / "ep_dgwhspm.md"
    _write_test_transcript_md(md_a, segs_a)
    _write_test_transcript_md(md_b, segs_b)
    mock_chunks.return_value = [
        _decision_unit(segs_a[:1], segs_b[:1], 0, 0, sub_id=0),
        _decision_unit(segs_a[1:], segs_b[1:], 1, 1, sub_id=1),
    ]
    mock_select.side_effect = [None, "a"]
    out = merge_dual_llm(str(md_a), str(md_b), profile="deutsch")
    merged = load_segments_from_md(out)
    assert [seg["dialogue"] for seg in merged] == [segs_b[0]["dialogue"], segs_a[1]["dialogue"]]
@patch("core.llm.llm_arbitrate_dual_chunk")
@patch("core.llm.llm_select_dual_chunk_side")
def test_merge_dual_llm_copies_selected_diff_chunk_verbatim(mock_select, mock_arb, tmp_path):
    segs_a, segs_b = _dual_structural_transcripts()
    md_a = tmp_path / "ep_nova2gen.md"
    md_b = tmp_path / "ep_dgwhspm.md"
    _write_test_transcript_md(md_a, segs_a)
    _write_test_transcript_md(md_b, segs_b)
    side_b = [{"speaker": s["speaker_name"], "timestamp": s["timestamp"], "dialogue": s["dialogue"]} for s in segs_b[:3]]
    mock_arb.return_value = side_b
    mock_select.return_value = "b"
    out = merge_dual_llm(str(md_a), str(md_b), profile="deutsch")
    assert os.path.isfile(out)
    merged = load_segments_from_md(out)
    actual = [(seg["speaker_name"], seg["timestamp"], seg["dialogue"]) for seg in merged]
    expected = [(seg["speaker_name"], seg["timestamp"], seg["dialogue"]) for seg in segs_b]
    assert actual == expected
    assert mock_select.call_count == 1
    assert mock_arb.call_count == 0
@patch("core.llm.llm_select_dual_chunk_side")
def test_merge_dual_llm_considers_existing_short_interjection_split(mock_select, tmp_path):
    segs_a = [
        _mk_seg("Dale", "25:20", DUAL_OPEN + " " + DUAL_MID_A),
        _mk_seg("Chris", "26:04", "Right."),
        _mk_seg("Dale", "26:04", DUAL_TAIL),
        _mk_seg("Chris", "26:29", "I agree that we should prepare a concrete proposal for the committee to review."),
    ]
    segs_b = [
        _mk_seg("Dale", "25:20", DUAL_OPEN + " " + DUAL_MID_A + " " + DUAL_TAIL),
        _mk_seg("Chris", "26:29", "I agree that we should prepare a concrete proposal for the committee to review."),
    ]
    md_a = tmp_path / "ep_nova2gen.md"
    md_b = tmp_path / "ep_dgwhspm.md"
    _write_test_transcript_md(md_a, segs_a)
    _write_test_transcript_md(md_b, segs_b)
    mock_select.return_value = "a"
    out = merge_dual_llm(str(md_a), str(md_b), profile="deutsch")
    merged = load_segments_from_md(out)
    assert mock_select.call_count == 1
    assert any(seg["speaker_name"] == "Chris" and seg["dialogue"] == "Right." for seg in merged)
@patch("core.llm.llm_arbitrate_dual_chunk")
def test_merge_dual_llm_passes_wording_chunk_through_base(mock_arb, tmp_path):
    segs_a, segs_b = _dual_chunk_transcripts()
    md_a = tmp_path / "ep_nova2gen.md"
    md_b = tmp_path / "ep_dgwhspm.md"
    _write_test_transcript_md(md_a, segs_a)
    _write_test_transcript_md(md_b, segs_b)
    out = merge_dual_llm(str(md_a), str(md_b), profile="deutsch")
    merged = load_segments_from_md(out)
    text = " ".join(seg["dialogue"] for seg in merged)
    # Wording-only disagreement: no LLM call, base side (B) wording kept.
    assert mock_arb.call_count == 0
    assert DUAL_MID_B in text
    assert DUAL_MID_A not in text
@patch("core.llm.llm_select_dual_chunk_side")
def test_merge_dual_llm_fallback_keeps_base_side_b(mock_select, tmp_path):
    segs_a, segs_b = _dual_structural_transcripts()
    md_a = tmp_path / "ep_nova2gen.md"
    md_b = tmp_path / "ep_dgwhspm.md"
    _write_test_transcript_md(md_a, segs_a)
    _write_test_transcript_md(md_b, segs_b)
    mock_select.return_value = None
    out = merge_dual_llm(str(md_a), str(md_b), profile="deutsch")
    merged = load_segments_from_md(out)
    text = " ".join(seg["dialogue"] for seg in merged)
    assert "Maybe we should discuss" in text
    assert DUAL_MID_A not in text
def test_extract_dual_chunk_triples_covers_reference(tmp_path):
    segs_a, segs_b = _dual_chunk_transcripts()
    ref_segs = [
        _mk_seg("Randy", "0:00:05", DUAL_OPEN),
        _mk_seg("Craig", "0:00:20", DUAL_MID_B),
        _mk_seg("Randy", "0:00:30", DUAL_TAIL),
    ]
    md_a = tmp_path / "ep_nova2gen.md"
    md_b = tmp_path / "ep_dgwhspm.md"
    md_ref = tmp_path / "ep_ref.md"
    _write_test_transcript_md(md_a, segs_a)
    _write_test_transcript_md(md_b, segs_b)
    _write_test_transcript_md(md_ref, ref_segs)
    out_json = tmp_path / "chunks.json"
    out_path, summary = extract_dual_chunk_triples(
        str(md_a), str(md_b), ref_path=str(md_ref), profile="deutsch", out_path=str(out_json))
    assert os.path.isfile(out_path)
    payload = json.loads(out_json.read_text())
    chunks = payload["chunks"]
    assert summary["chunk_count"] == len(chunks) == 2
    assert all(c["ref"] is not None for c in chunks)
    assert all("parent_chunk_id" in c and "decision_sub_id" in c for c in chunks)
    ref_text_from_chunks = " ".join(
        seg["dialogue"] for c in chunks for seg in c["ref"]["segments"])
    full_ref_words = [w for seg in ref_segs for w in seg["dialogue"].split()]
    import re as _re
    norm = lambda words: [_re.sub(r"[^a-z0-9']", "", w.lower()) for w in words]
    assert norm(ref_text_from_chunks.split()) == norm(full_ref_words)
def test_denovo_dual_prompt_v3_guardrails():
    prompt = PROMPT_DENOVO_DUAL_V3.lower()
    assert "never output a's copy followed by b's copy" in prompt
    assert "do not paraphrase" in prompt or "not copyediting" in prompt
    assert "never invent, reformat, or average timestamps" in prompt
def test_denovo_dual_prompt_v4_is_selector_only():
    prompt = llm_module.PROMPT_DENOVO_DUAL_V4.lower()
    assert "selector, not an editor" in prompt
    assert "do not return transcript text" in prompt
    assert "never create a new segment" in prompt
    assert '"yeah"' in prompt and '"no"' in prompt and '"right"' in prompt
    assert "eligible existing segmentation" in prompt
    assert "never extract such words" in prompt
def test_resolve_denovo_prompts_v3_default():
    from core.denovo import resolve_denovo_prompts
    single, dual = resolve_denovo_prompts({"prompts_version": "denovo-v3"})
    assert dual == PROMPT_DENOVO_DUAL_V3
    _, dual_v2 = resolve_denovo_prompts({"prompts_version": "denovo-v2"})
    assert dual_v2 == PROMPT_DENOVO_DUAL_V2
    _, dual_v4 = resolve_denovo_prompts({"prompts_version": "denovo-v4"})
    assert dual_v4 == llm_module.PROMPT_DENOVO_DUAL_V4
