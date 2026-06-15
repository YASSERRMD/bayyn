import pytest
from app.transcription.caption_processor import normalize_segments, _clean_caption_text


def test_clean_removes_html_tags():
    result = _clean_caption_text("<c>Hello</c> <i>world</i>")
    assert "<" not in result
    assert "Hello" in result
    assert "world" in result


def test_clean_removes_bracket_annotations():
    result = _clean_caption_text("[Music] Hello there [Applause]")
    assert "[Music]" not in result
    assert "Hello there" in result


def test_clean_unescapes_html_entities():
    result = _clean_caption_text("Hello &amp; World")
    assert "&amp;" not in result
    assert "&" in result


def test_normalize_filters_empty_segments():
    segments = [
        {"start": 0.0, "end": 2.0, "text": "  "},
        {"start": 2.0, "end": 4.0, "text": "Hello"},
    ]
    result = normalize_segments(segments)
    assert len(result) == 1
    assert result[0]["text"] == "Hello"


def test_normalize_merges_consecutive_duplicates():
    segments = [
        {"start": 0.0, "end": 2.0, "text": "Hello"},
        {"start": 2.0, "end": 4.0, "text": "Hello"},
        {"start": 4.0, "end": 6.0, "text": "World"},
    ]
    result = normalize_segments(segments)
    assert len(result) == 2
    assert result[0]["text"] == "Hello"
    assert result[0]["end"] == 4.0
    assert result[1]["text"] == "World"


def test_normalize_preserves_timing():
    segments = [
        {"start": 1.5, "end": 3.2, "text": "First segment"},
        {"start": 3.5, "end": 6.0, "text": "Second segment"},
    ]
    result = normalize_segments(segments)
    assert result[0]["start"] == 1.5
    assert result[0]["end"] == 3.2
    assert result[1]["start"] == 3.5


def test_normalize_empty_input():
    assert normalize_segments([]) == []


def test_normalize_returns_sequence_numbers():
    segments = [
        {"start": 0.0, "end": 2.0, "text": "One"},
        {"start": 2.0, "end": 4.0, "text": "Two"},
    ]
    result = normalize_segments(segments)
    assert len(result) == 2
