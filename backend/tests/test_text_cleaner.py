import pytest
from app.transcription.text_cleaner import (
    apply_text_cleanup,
    clean_transcript_text,
    normalize_casing,
    normalize_punctuation,
    remove_filler_artifacts,
)


# ── remove_filler_artifacts ──────────────────────────────────────────────────

def test_removes_consecutive_repeated_words():
    assert remove_filler_artifacts("hello hello world") == "hello world"


def test_removes_three_consecutive_repeats():
    assert remove_filler_artifacts("the the the cat") == "the cat"


def test_removes_standalone_um():
    result = remove_filler_artifacts("um I think so")
    assert "um" not in result.lower()
    assert "think" in result


def test_removes_standalone_uh():
    result = remove_filler_artifacts("uh okay")
    assert result.strip() == "okay"


def test_removes_standalone_hmm():
    result = remove_filler_artifacts("hmm interesting")
    assert "hmm" not in result.lower()
    assert "interesting" in result


def test_preserves_non_filler_words():
    result = remove_filler_artifacts("umbrella is a word")
    assert "umbrella" in result


def test_empty_string_returns_empty():
    assert remove_filler_artifacts("") == ""


# ── normalize_punctuation ────────────────────────────────────────────────────

def test_collapses_double_exclamation():
    assert normalize_punctuation("wow!!") == "wow!"


def test_collapses_multiple_question_marks():
    assert normalize_punctuation("really???") == "really?"


def test_removes_space_before_comma():
    assert normalize_punctuation("yes , sir") == "yes, sir"


def test_removes_space_before_period():
    assert normalize_punctuation("hello .") == "hello."


def test_adds_space_after_period():
    result = normalize_punctuation("hello.world")
    assert "hello. world" == result


def test_punctuation_at_end_unchanged():
    result = normalize_punctuation("done.")
    assert result == "done."


# ── normalize_casing ─────────────────────────────────────────────────────────

def test_capitalizes_first_character():
    assert normalize_casing("hello world") == "Hello world"


def test_capitalizes_after_period():
    result = normalize_casing("first sentence. second sentence")
    assert "Second" in result


def test_capitalizes_after_question_mark():
    result = normalize_casing("how are you? fine thanks")
    assert "Fine" in result


def test_capitalizes_after_exclamation():
    result = normalize_casing("great! now what")
    assert "Now" in result


def test_already_capitalized_unchanged():
    result = normalize_casing("Hello World")
    assert result == "Hello World"


def test_empty_returns_empty():
    assert normalize_casing("") == ""


# ── clean_transcript_text ────────────────────────────────────────────────────

def test_full_pipeline():
    text = "um hello hello world. what what is this?? great"
    result = clean_transcript_text(text)
    assert "um" not in result.lower()
    assert "hello" in result.lower()
    assert "??" not in result
    assert result[0].isupper()


# ── apply_text_cleanup ───────────────────────────────────────────────────────

def test_preserves_timestamps():
    segments = [
        {"start": 1.5, "end": 3.2, "text": "um hello hello"},
        {"start": 3.5, "end": 6.0, "text": "world!!"},
    ]
    result = apply_text_cleanup(segments)
    assert result[0]["start"] == 1.5
    assert result[0]["end"] == 3.2
    assert result[1]["start"] == 3.5
    assert result[1]["end"] == 6.0


def test_preserves_confidence_field():
    segments = [{"start": 0.0, "end": 2.0, "text": "hello", "confidence": 0.95}]
    result = apply_text_cleanup(segments)
    assert result[0]["confidence"] == 0.95


def test_preserves_speaker_field():
    segments = [{"start": 0.0, "end": 2.0, "text": "hello", "speaker": "A"}]
    result = apply_text_cleanup(segments)
    assert result[0]["speaker"] == "A"


def test_drops_empty_segments_after_cleanup():
    segments = [
        {"start": 0.0, "end": 1.0, "text": "um"},
        {"start": 1.0, "end": 2.0, "text": "hello"},
    ]
    result = apply_text_cleanup(segments)
    texts = [s["text"] for s in result]
    assert "Hello" in texts


def test_empty_input_returns_empty():
    assert apply_text_cleanup([]) == []


def test_does_not_mutate_original_segments():
    segments = [{"start": 0.0, "end": 2.0, "text": "um hello hello world"}]
    original_text = segments[0]["text"]
    apply_text_cleanup(segments)
    assert segments[0]["text"] == original_text
