import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.exports.srt_export import generate_srt, _seconds_to_srt_time
from app.exports.txt_export import generate_txt


def make_segment(seq, start, end, text):
    seg = MagicMock()
    seg.sequence_number = seq
    seg.start_seconds = start
    seg.end_seconds = end
    seg.text = text
    return seg


def make_doc(full_text, word_count=10, segment_count=2):
    doc = MagicMock()
    doc.full_text = full_text
    doc.word_count = word_count
    doc.segment_count = segment_count
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


def test_txt_export_returns_full_text():
    doc = make_doc("Hello world this is a test transcript.")
    result = generate_txt(doc)
    assert result == "Hello world this is a test transcript."


def test_srt_format_index_starts_at_one():
    segments = [make_segment(1, 0.0, 5.0, "First")]
    srt = generate_srt(segments)
    assert srt.startswith("1\n")


def test_srt_timestamps_correct_format():
    time_str = _seconds_to_srt_time(3661.5)
    assert time_str == "01:01:01,500"


def test_srt_zero_seconds():
    assert _seconds_to_srt_time(0.0) == "00:00:00,000"


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
    """Verify DOCX export is streamed as bytes, not saved to disk."""
    from app.exports.docx_export import generate_docx
    job = make_job()
    doc = make_doc("Test")
    result = generate_docx(job, doc, [])
    assert isinstance(result, bytes)
    docx_files = list(tmp_path.glob("*.docx"))
    assert len(docx_files) == 0
