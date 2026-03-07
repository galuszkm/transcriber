"""Tests for transcriber.pipeline.diarization - re-segmentation pure functions."""

from transcriber.pipeline.diarization import (
    _group_words_by_speaker,
    _split_segment,
    _word_group_to_segment,
    resegment_by_speaker,
)

# ---------------------------------------------------------------------------
# _word_group_to_segment
# ---------------------------------------------------------------------------


class TestWordGroupToSegment:
    """Convert a word group into a segment dict."""

    def test_basic_conversion(self) -> None:
        group = {
            "speaker": "SPEAKER_00",
            "start": 0.0,
            "words": [
                {"word": "Hello", "start": 0.0, "end": 0.5},
                {"word": "world", "start": 0.6, "end": 1.0},
            ],
        }
        seg = _word_group_to_segment(group)
        assert seg is not None
        assert seg["text"] == "Hello world"
        assert seg["start"] == 0.0
        assert seg["end"] == 1.0
        assert seg["speaker"] == "SPEAKER_00"

    def test_empty_words_returns_none(self) -> None:
        group = {"speaker": "SPEAKER_00", "start": 0.0, "words": [{"word": ""}]}
        assert _word_group_to_segment(group) is None

    def test_word_missing_end_uses_start_fallback(self) -> None:
        group = {
            "speaker": "S0",
            "start": 5.0,
            "words": [{"word": "test"}],
        }
        seg = _word_group_to_segment(group)
        assert seg is not None
        assert seg["end"] == 5.0  # falls back to group start


# ---------------------------------------------------------------------------
# _group_words_by_speaker
# ---------------------------------------------------------------------------


class TestGroupWordsBySpeaker:
    """Group consecutive words sharing the same speaker."""

    def test_single_speaker(self) -> None:
        words = [
            {"word": "Hi", "speaker": "A", "start": 0.0},
            {"word": "there", "speaker": "A", "start": 0.5},
        ]
        groups = _group_words_by_speaker(words, 0.0)
        assert len(groups) == 1
        assert groups[0]["speaker"] == "A"
        assert len(groups[0]["words"]) == 2

    def test_speaker_change(self) -> None:
        words = [
            {"word": "Hi", "speaker": "A", "start": 0.0},
            {"word": "Hey", "speaker": "B", "start": 1.0},
        ]
        groups = _group_words_by_speaker(words, 0.0)
        assert len(groups) == 2
        assert groups[0]["speaker"] == "A"
        assert groups[1]["speaker"] == "B"

    def test_alternating_speakers(self) -> None:
        words = [
            {"word": "a", "speaker": "A", "start": 0.0},
            {"word": "b", "speaker": "B", "start": 1.0},
            {"word": "c", "speaker": "A", "start": 2.0},
        ]
        groups = _group_words_by_speaker(words, 0.0)
        assert len(groups) == 3

    def test_word_without_speaker_inherits_previous(self) -> None:
        words = [
            {"word": "a", "speaker": "A", "start": 0.0},
            {"word": "b", "start": 1.0},  # no speaker key
        ]
        groups = _group_words_by_speaker(words, 0.0)
        # "b" inherits "A" → still one group
        assert len(groups) == 1
        assert len(groups[0]["words"]) == 2


# ---------------------------------------------------------------------------
# _split_segment
# ---------------------------------------------------------------------------


class TestSplitSegment:
    """Split a single segment at speaker boundaries."""

    def test_no_words_returns_as_is(self) -> None:
        seg = {"start": 0, "end": 5, "text": "Hello", "speaker": "X"}
        assert _split_segment(seg) == [seg]

    def test_words_without_speaker_returns_as_is(self) -> None:
        seg = {"start": 0, "end": 5, "text": "Hi", "words": [{"word": "Hi"}]}
        assert _split_segment(seg) == [seg]

    def test_single_speaker_produces_one_segment(self) -> None:
        seg = {
            "start": 0,
            "end": 2,
            "text": "Hi there",
            "words": [
                {"word": "Hi", "speaker": "A", "start": 0, "end": 0.5},
                {"word": "there", "speaker": "A", "start": 0.6, "end": 1.0},
            ],
        }
        result = _split_segment(seg)
        assert len(result) == 1
        assert result[0]["speaker"] == "A"

    def test_two_speakers_produces_two_segments(self) -> None:
        seg = {
            "start": 0,
            "end": 3,
            "text": "Hi Hey",
            "words": [
                {"word": "Hi", "speaker": "A", "start": 0, "end": 0.5},
                {"word": "Hey", "speaker": "B", "start": 1, "end": 1.5},
            ],
        }
        result = _split_segment(seg)
        assert len(result) == 2
        assert result[0]["speaker"] == "A"
        assert result[1]["speaker"] == "B"


# ---------------------------------------------------------------------------
# resegment_by_speaker
# ---------------------------------------------------------------------------


class TestResegmentBySpeaker:
    """End-to-end re-segmentation across multiple segments."""

    def test_empty_segments(self) -> None:
        assert resegment_by_speaker([]) == []

    def test_preserves_segments_without_word_speaker(self) -> None:
        segs = [{"start": 0, "end": 5, "text": "Hello"}]
        assert resegment_by_speaker(segs) == segs

    def test_multi_segment_resegmentation(self) -> None:
        segs = [
            {
                "start": 0,
                "end": 2,
                "text": "Hello world",
                "words": [
                    {"word": "Hello", "speaker": "A", "start": 0, "end": 0.5},
                    {"word": "world", "speaker": "B", "start": 0.6, "end": 1.0},
                ],
            },
            {
                "start": 2,
                "end": 4,
                "text": "Goodbye",
                "words": [
                    {"word": "Goodbye", "speaker": "B", "start": 2, "end": 3},
                ],
            },
        ]
        result = resegment_by_speaker(segs)
        assert len(result) == 3  # A:Hello, B:world, B:Goodbye
        assert result[0]["speaker"] == "A"
        assert result[1]["speaker"] == "B"
        assert result[2]["speaker"] == "B"
