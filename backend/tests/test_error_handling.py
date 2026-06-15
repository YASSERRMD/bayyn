"""Tests for error classification, sanitization, and audit detail building."""
import re

import pytest

from app.errors.error_mapper import (
    build_audit_detail,
    classify_error,
    sanitize_for_audit,
)


# ── classify_error ────────────────────────────────────────────────────────────

class FakeNetworkError(Exception):
    pass


class FakeAudioError(Exception):
    pass


class FakeTranscribeError(Exception):
    pass


class FakeDurationError(Exception):
    pass


def test_classify_network_error():
    exc = FakeNetworkError("yt-dlp returned HTTP error 403")
    msg = classify_error(exc)
    assert "fetch" in msg.lower() or "url" in msg.lower()


def test_classify_private_video():
    exc = FakeNetworkError("This video is unavailable")
    msg = classify_error(exc)
    assert "fetch" in msg.lower() or "url" in msg.lower()


def test_classify_audio_error():
    exc = FakeAudioError("ffmpeg exited with returncode 1")
    msg = classify_error(exc)
    assert "audio" in msg.lower()


def test_classify_transcribe_error():
    exc = FakeTranscribeError("faster_whisper: CUDA out of memory")
    msg = classify_error(exc)
    assert "speech" in msg.lower() or "recognition" in msg.lower()


def test_classify_duration_error():
    exc = FakeDurationError("Video exceeds max_seconds limit")
    msg = classify_error(exc)
    assert "length" in msg.lower() or "long" in msg.lower() or "exceed" in msg.lower()


def test_classify_unknown_error():
    exc = RuntimeError("something completely unexpected")
    msg = classify_error(exc)
    assert "unexpected" in msg.lower()


def test_classify_returns_string():
    exc = Exception("anything")
    assert isinstance(classify_error(exc), str)


# ── sanitize_for_audit ────────────────────────────────────────────────────────

def test_sanitize_redacts_urls():
    try:
        raise ValueError("download failed: https://secret.example.com/path?token=abc")
    except ValueError as exc:
        result = sanitize_for_audit(exc)
    assert "https://secret.example.com" not in result
    assert "[URL]" in result


def test_sanitize_redacts_paths():
    try:
        raise OSError("file not found: /tmp/bayyn-jobs/abc123/audio.wav")
    except OSError as exc:
        result = sanitize_for_audit(exc)
    assert "/tmp/" not in result
    assert "[PATH]" in result


def test_sanitize_respects_max_len():
    try:
        raise RuntimeError("x" * 10_000)
    except RuntimeError as exc:
        result = sanitize_for_audit(exc, max_len=100)
    assert len(result) <= 100


def test_sanitize_includes_exception_type():
    try:
        raise TypeError("bad type")
    except TypeError as exc:
        result = sanitize_for_audit(exc)
    assert "TypeError" in result


# ── build_audit_detail ────────────────────────────────────────────────────────

def test_build_audit_detail_has_required_keys():
    exc = RuntimeError("boom")
    detail = build_audit_detail(exc)
    assert "exc_type" in detail
    assert "exc_summary" in detail
    assert "user_message" in detail


def test_build_audit_detail_exc_type_matches():
    exc = ValueError("bad value")
    detail = build_audit_detail(exc)
    assert detail["exc_type"] == "ValueError"


def test_build_audit_detail_merges_context():
    exc = RuntimeError("oops")
    detail = build_audit_detail(exc, context={"job_id": "abc-123", "attempt": 2})
    assert detail["job_id"] == "abc-123"
    assert detail["attempt"] == 2


def test_build_audit_detail_user_message_is_safe():
    exc = OSError("ffmpeg: /tmp/bayyn/job-1/audio.wav: No such file")
    detail = build_audit_detail(exc)
    # user_message must not contain filesystem paths
    assert "/tmp/" not in detail["user_message"]
    assert "ffmpeg" not in detail["user_message"].lower() or "audio" in detail["user_message"].lower()
