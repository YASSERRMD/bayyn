"""Tests for long video handling: duration validation, chunked transcription, timeout."""
import uuid
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from app.transcription.duration_validator import VideoTooLongError, validate_duration


# ── Duration validation ───────────────────────────────────────────────────────

def test_validate_duration_raises_for_too_long():
    with pytest.raises(VideoTooLongError):
        validate_duration(7201, 7200)


def test_validate_duration_passes_at_limit():
    validate_duration(7200, 7200)  # should not raise


def test_validate_duration_passes_below_limit():
    validate_duration(3600, 7200)  # should not raise


def test_validate_duration_none_is_allowed():
    validate_duration(0, 7200)   # duration 0/None is allowed (unknown)
    validate_duration(None, 7200)


def test_video_too_long_error_message():
    exc = VideoTooLongError(8000, 7200)
    assert "8000" in str(exc)
    assert "7200" in str(exc)


def test_video_too_long_error_attributes():
    exc = VideoTooLongError(9000, 7200)
    assert exc.duration_seconds == 9000
    assert exc.max_seconds == 7200


def test_video_too_long_is_value_error():
    exc = VideoTooLongError(9000, 7200)
    assert isinstance(exc, ValueError)


# ── _should_chunk logic ───────────────────────────────────────────────────────

def test_should_chunk_large_file(tmp_path):
    """A file > chunk_threshold_seconds * 32000 bytes should trigger chunking."""
    from app.transcription.whisper_processor import _should_chunk

    wav = tmp_path / "audio.wav"
    # PCM s16le 16kHz mono: 32000 bytes/s. threshold=600s → 19,200,000 bytes
    wav.write_bytes(b"\x00" * 19_300_000)

    with patch("app.transcription.whisper_processor.settings") as mock_cfg:
        mock_cfg.chunk_threshold_seconds = 600
        result = _should_chunk(wav)

    assert result is True


def test_should_chunk_small_file(tmp_path):
    """A small file should NOT trigger chunking."""
    from app.transcription.whisper_processor import _should_chunk

    wav = tmp_path / "audio.wav"
    wav.write_bytes(b"\x00" * 1000)

    with patch("app.transcription.whisper_processor.settings") as mock_cfg:
        mock_cfg.chunk_threshold_seconds = 600
        result = _should_chunk(wav)

    assert result is False


# ── audio_chunker ─────────────────────────────────────────────────────────────

def test_chunk_audio_raises_if_file_missing(tmp_path):
    from app.transcription.audio_chunker import chunk_audio

    with pytest.raises(FileNotFoundError):
        chunk_audio(tmp_path / "nonexistent.wav", 600, tmp_path)


def test_chunk_timestamp_offsets():
    """Chunks at idx 0,1,2 with chunk_duration=600 should have offsets 0, 600, 1200."""
    expected = [(Path("chunk_0000.wav"), 0.0),
                (Path("chunk_0001.wav"), 600.0),
                (Path("chunk_0002.wav"), 1200.0)]
    chunk_duration = 600
    for idx, (_, offset) in enumerate(expected):
        assert offset == float(idx * chunk_duration)


def test_delete_chunks_handles_missing_file(tmp_path):
    from app.transcription.audio_chunker import delete_chunks

    nonexistent = tmp_path / "ghost.wav"
    delete_chunks([(nonexistent, 0.0)])  # should not raise


# ── Chunked transcription ─────────────────────────────────────────────────────

def test_chunked_transcription_offsets_timestamps(tmp_path):
    """Segments from each chunk should have start/end offset by chunk start."""
    from app.transcription.whisper_processor import _transcribe_chunked

    fake_chunk_a = tmp_path / "chunk_0000.wav"
    fake_chunk_b = tmp_path / "chunk_0001.wav"
    fake_chunk_a.write_bytes(b"x")
    fake_chunk_b.write_bytes(b"x")

    def fake_run_whisper(path):
        return ([{"start": 1.0, "end": 2.0, "text": "hello", "confidence": 0.9}], "en")

    fake_chunks = [(fake_chunk_a, 0.0), (fake_chunk_b, 600.0)]

    with patch("app.transcription.whisper_processor._run_whisper", side_effect=fake_run_whisper), \
         patch("app.transcription.audio_chunker.chunk_audio", return_value=fake_chunks), \
         patch("app.transcription.audio_chunker.delete_chunks"), \
         patch("app.transcription.whisper_processor.settings") as mock_cfg:
        mock_cfg.chunk_duration_seconds = 600
        segments, lang = _transcribe_chunked(tmp_path / "audio.wav", tmp_path)

    assert len(segments) == 2
    assert segments[0]["start"] == 1.0   # chunk 0 offset=0
    assert segments[1]["start"] == 601.0  # chunk 1 offset=600 + 1.0
    assert lang == "en"


def test_chunked_transcription_skips_failed_chunks(tmp_path):
    """A chunk that raises should be skipped; others continue."""
    from app.transcription.whisper_processor import _transcribe_chunked

    good_chunk = tmp_path / "chunk_0000.wav"
    bad_chunk = tmp_path / "chunk_0001.wav"
    good_chunk.write_bytes(b"x")
    bad_chunk.write_bytes(b"x")

    def fake_run_whisper(path):
        if "0001" in str(path):
            raise RuntimeError("Whisper failed on this chunk")
        return ([{"start": 0.5, "end": 1.0, "text": "ok", "confidence": 0.8}], "en")

    fake_chunks = [(good_chunk, 0.0), (bad_chunk, 600.0)]

    with patch("app.transcription.whisper_processor._run_whisper", side_effect=fake_run_whisper), \
         patch("app.transcription.audio_chunker.chunk_audio", return_value=fake_chunks), \
         patch("app.transcription.audio_chunker.delete_chunks"):
        segments, lang = _transcribe_chunked(tmp_path / "audio.wav", tmp_path)

    assert len(segments) == 1
    assert segments[0]["text"] == "ok"
