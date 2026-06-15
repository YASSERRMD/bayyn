"""Tests for language detection foundation."""
import pytest
from app.transcription.language_detector import (
    DEFAULT_LANGUAGE,
    detect_from_caption_keys,
    detect_from_whisper_info,
    normalize_language_code,
)


# ── normalize_language_code ───────────────────────────────────────────────────

def test_normalize_bcp47_en_us():
    assert normalize_language_code("en-US") == "en"


def test_normalize_bcp47_en_gb():
    assert normalize_language_code("en-GB") == "en"


def test_normalize_already_short():
    assert normalize_language_code("fr") == "fr"


def test_normalize_underscore_variant():
    assert normalize_language_code("zh_CN") == "zh"


def test_normalize_empty_returns_default():
    assert normalize_language_code("") == DEFAULT_LANGUAGE


def test_normalize_none_like_returns_default():
    assert normalize_language_code(None or "") == DEFAULT_LANGUAGE


def test_normalize_uppercase():
    assert normalize_language_code("DE") == "de"


# ── detect_from_caption_keys ──────────────────────────────────────────────────

def test_detects_english_from_en_key():
    assert detect_from_caption_keys(["en"]) == "en"


def test_detects_from_en_us_key():
    assert detect_from_caption_keys(["en-US"]) == "en"


def test_detects_first_known_language():
    result = detect_from_caption_keys(["fr", "de", "en"])
    assert result == "fr"


def test_returns_default_for_empty_keys():
    assert detect_from_caption_keys([]) == DEFAULT_LANGUAGE


def test_returns_default_for_unknown_keys():
    assert detect_from_caption_keys(["xx", "zz"]) == DEFAULT_LANGUAGE


def test_detects_spanish():
    assert detect_from_caption_keys(["es"]) == "es"


# ── detect_from_whisper_info ──────────────────────────────────────────────────

def test_high_probability_returns_language():
    assert detect_from_whisper_info("en", 0.99) == "en"


def test_low_probability_returns_default():
    assert detect_from_whisper_info("fr", 0.3) == DEFAULT_LANGUAGE


def test_boundary_probability_returns_language():
    assert detect_from_whisper_info("de", 0.5) == "de"


def test_just_below_boundary_returns_default():
    assert detect_from_whisper_info("de", 0.49) == DEFAULT_LANGUAGE


def test_normalizes_bcp47_from_whisper():
    assert detect_from_whisper_info("zh-CN", 0.9) == "zh"


# ── Default language ──────────────────────────────────────────────────────────

def test_default_language_is_english():
    assert DEFAULT_LANGUAGE == "en"
