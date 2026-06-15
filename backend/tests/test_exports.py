import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.exports.srt_export import generate_srt, _to_srt_time
from app.exports.txt_export import generate_txt


def make_segment(seq, start, end, text):
    seg = MagicMock()
    seg.sequence_number = seq
    seg.start_seconds = start
    seg.end_seconds = end
    seg.text = text
    return seg


def make_doc(full_text, word_count=10, segment_count=2, average_confidence=None, low_confidence_count=0):
    doc = MagicMock()
    doc.full_text = full_text
    doc.word_count = word_count
    doc.segment_count = segment_count
    doc.average_confidence = average_confidence
    doc.low_confidence_count = low_confidence_count
    return doc


def make_job(title="Test Video", source_url="https://www.youtube.com/watch?v=test"):
    try:
        from app.models.transcription_job import JobStatus, ProcessingStrategy
        status = JobStatus.completed
        strategy = ProcessingStrategy.caption
    except Exception:
        status = "completed"
        strategy = "caption"
    job = MagicMock()
    job.id = uuid.uuid4()
    job.title = title
    job.source_url = source_url
    job.source_type = "youtube"
    job.duration_seconds = 120
    job.language = "en"
    job.status = status
    job.processing_strategy = strategy
    job.completed_at = datetime.now(timezone.utc)
    return job


# ── TXT export ────────────────────────────────────────────────────────────────

def test_txt_export_returns_full_text():
    doc = make_doc("Hello world this is a test transcript.")
    result = generate_txt(doc)
    assert result == "Hello world this is a test transcript."


def test_txt_export_no_timestamps_by_default():
    doc = make_doc("Plain text content here.")
    segments = [make_segment(1, 0.0, 5.0, "Plain text content here.")]
    result = generate_txt(doc, include_timestamps=False, segments=segments)
    assert "[" not in result


def test_txt_export_with_timestamps():
    doc = make_doc("Hello world.")
    segments = [
        make_segment(1, 0.0, 5.0, "Hello"),
        make_segment(2, 65.0, 70.0, "world"),
    ]
    result = generate_txt(doc, include_timestamps=True, segments=segments)
    assert "[00:00:00] Hello" in result
    assert "[00:01:05] world" in result


def test_txt_export_timestamps_skips_empty_segments():
    doc = make_doc("Hello.")
    segments = [
        make_segment(1, 0.0, 5.0, "Hello"),
        make_segment(2, 5.0, 6.0, "   "),  # whitespace-only
    ]
    result = generate_txt(doc, include_timestamps=True, segments=segments)
    lines = result.strip().split("\n")
    assert len(lines) == 1


def test_txt_export_timestamps_fallback_to_full_text_if_no_segments():
    doc = make_doc("Fallback text.")
    result = generate_txt(doc, include_timestamps=True, segments=None)
    assert result == "Fallback text."


# ── SRT export ────────────────────────────────────────────────────────────────

def test_srt_format_index_starts_at_one():
    segments = [make_segment(1, 0.0, 5.0, "First")]
    srt = generate_srt(segments)
    assert srt.startswith("1\n")


def test_srt_timestamps_correct_format():
    time_str = _to_srt_time(3661.5)
    assert time_str == "01:01:01,500"


def test_srt_zero_seconds():
    assert _to_srt_time(0.0) == "00:00:00,000"


def test_srt_two_segments():
    segments = [
        make_segment(1, 0.0, 5.0, "Hello"),
        make_segment(2, 5.5, 10.0, "World"),
    ]
    srt = generate_srt(segments)
    assert "1\n" in srt
    assert "2\n" in srt
    assert "Hello" in srt
    assert "World" in srt
    assert "-->" in srt


def test_srt_empty_segments():
    srt = generate_srt([])
    assert srt == ""


def test_srt_skips_empty_text_segments():
    segments = [
        make_segment(1, 0.0, 5.0, "Real text"),
        make_segment(2, 5.0, 6.0, ""),
        make_segment(3, 6.0, 7.0, "   "),
    ]
    srt = generate_srt(segments)
    # Only index 1 should appear
    assert "1\n" in srt
    assert "2\n" not in srt
    assert "3\n" not in srt


def test_srt_clamps_zero_duration_segment():
    segments = [make_segment(1, 5.0, 5.0, "Bad timing")]
    srt = generate_srt(segments)
    assert "00:00:05,000 --> 00:00:05,001" in srt


def test_srt_clamps_inverted_timestamps():
    segments = [make_segment(1, 10.0, 8.0, "Inverted")]
    srt = generate_srt(segments)
    # end should be nudged to start+0.001
    assert "00:00:10,000 -->" in srt
    assert "-" not in srt.split("-->")[1].split("\n")[0].strip()


# ── DOCX export ───────────────────────────────────────────────────────────────

def test_docx_export_returns_bytes():
    from app.exports.docx_export import generate_docx
    job = make_job()
    doc = make_doc("Test transcript full text.")
    segments = [make_segment(1, 0.0, 5.0, "Test transcript")]
    result = generate_docx(job, doc, segments)
    assert isinstance(result, bytes)
    assert len(result) > 0
    assert result[:4] == b"PK\x03\x04"


def test_docx_never_stores_file(tmp_path):
    """DOCX export is returned as bytes, not written to disk."""
    from app.exports.docx_export import generate_docx
    job = make_job()
    doc = make_doc("Test")
    result = generate_docx(job, doc, [])
    assert isinstance(result, bytes)
    docx_files = list(tmp_path.glob("*.docx"))
    assert len(docx_files) == 0


def test_docx_skips_empty_segment_rows():
    from app.exports.docx_export import generate_docx
    job = make_job()
    doc = make_doc("Hello world.")
    segments = [
        make_segment(1, 0.0, 5.0, "Hello world."),
        make_segment(2, 5.0, 6.0, "   "),  # should be skipped
    ]
    result = generate_docx(job, doc, segments)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_docx_with_confidence_data():
    from app.exports.docx_export import generate_docx
    job = make_job()
    doc = make_doc("Some text.", average_confidence=0.85, low_confidence_count=2)
    segments = [make_segment(1, 0.0, 5.0, "Some text.")]
    result = generate_docx(job, doc, segments)
    assert isinstance(result, bytes)
    assert len(result) > 0
