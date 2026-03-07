"""Tests for transcriber.pipeline.transcriber - pure helper functions."""

from transcriber.core.models import TranscriptSegment
from transcriber.pipeline.transcriber import _detect_language, build_segments

# ---------------------------------------------------------------------------
# build_segments
# ---------------------------------------------------------------------------


class TestBuildSegments:
    """Convert raw dicts to typed TranscriptSegment models."""

    def test_empty_list(self) -> None:
        assert build_segments([]) == []

    def test_minimal_segment(self) -> None:
        raw = [{"start": 1.0, "end": 2.5, "text": "Hi"}]
        result = build_segments(raw)
        assert len(result) == 1
        assert isinstance(result[0], TranscriptSegment)
        assert result[0].text == "Hi"
        assert result[0].start == 1.0
        assert result[0].end == 2.5

    def test_missing_keys_use_defaults(self) -> None:
        raw = [{}]
        result = build_segments(raw)
        assert result[0].start == 0.0
        assert result[0].end == 0.0
        assert result[0].text == ""
        assert result[0].speaker is None
        assert result[0].words == []

    def test_speaker_and_words_preserved(self) -> None:
        raw = [
            {
                "start": 0,
                "end": 1,
                "text": "Test",
                "speaker": "SPEAKER_01",
                "words": [{"word": "Test", "start": 0, "end": 1}],
            }
        ]
        result = build_segments(raw)
        assert result[0].speaker == "SPEAKER_01"
        assert len(result[0].words) == 1

    def test_multiple_segments_order_preserved(self) -> None:
        raw = [
            {"start": 0, "end": 1, "text": "A"},
            {"start": 1, "end": 2, "text": "B"},
            {"start": 2, "end": 3, "text": "C"},
        ]
        texts = [s.text for s in build_segments(raw)]
        assert texts == ["A", "B", "C"]


# ---------------------------------------------------------------------------
# _detect_language
# ---------------------------------------------------------------------------


class TestDetectLanguage:
    """Extract language from raw WhisperX result dict."""

    def test_present_key(self) -> None:
        assert _detect_language({"language": "de", "segments": []}) == "de"

    def test_missing_key_returns_unknown(self) -> None:
        assert _detect_language({}) == "unknown"
