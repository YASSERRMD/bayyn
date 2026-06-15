"""Tests for confidence score handling and low-confidence warnings."""
import pytest
from unittest.mock import MagicMock, patch

from app.schemas.transcript import LOW_CONFIDENCE_THRESHOLD, TranscriptResponse, TranscriptSegmentResponse


LOW = LOW_CONFIDENCE_THRESHOLD - 0.05   # 0.55
HIGH = LOW_CONFIDENCE_THRESHOLD + 0.15  # 0.75


# ── Schema behaviour ──────────────────────────────────────────────────────────

def test_low_confidence_threshold_value():
    assert LOW_CONFIDENCE_THRESHOLD == 0.6


def test_segment_response_low_confidence_flag_set():
    seg = TranscriptSegmentResponse(
        sequence_number=1,
        start=0.0,
        end=2.0,
        text="hello",
        confidence=LOW,
        low_confidence=True,
    )
    assert seg.low_confidence is True


def test_segment_response_low_confidence_flag_unset_for_high():
    seg = TranscriptSegmentResponse(
        sequence_number=1,
        start=0.0,
        end=2.0,
        text="hello",
        confidence=HIGH,
        low_confidence=False,
    )
    assert seg.low_confidence is False


def test_transcript_response_has_low_confidence_segments_true():
    resp = TranscriptResponse(
        job_id="00000000-0000-0000-0000-000000000001",
        full_text="hello world",
        word_count=2,
        segment_count=1,
        average_confidence=LOW,
        low_confidence_count=1,
        has_low_confidence_segments=True,
        accuracy_disclaimer="Low confidence detected.",
        segments=[],
        created_at="2025-01-01T00:00:00",
    )
    assert resp.has_low_confidence_segments is True
    assert resp.low_confidence_count == 1
    assert resp.accuracy_disclaimer is not None


def test_transcript_response_defaults_no_disclaimer():
    resp = TranscriptResponse(
        job_id="00000000-0000-0000-0000-000000000002",
        full_text="hello world",
        word_count=2,
        segment_count=1,
        segments=[],
        created_at="2025-01-01T00:00:00",
    )
    assert resp.has_low_confidence_segments is False
    assert resp.low_confidence_count == 0
    assert resp.accuracy_disclaimer is None
    assert resp.average_confidence is None


# ── Worker confidence computation helpers ─────────────────────────────────────

def _compute_metrics(confidences: list):
    """Mirror the worker logic for unit-testing without importing Celery."""
    threshold = 0.6
    confident_values = [float(c) for c in confidences if c is not None]
    average = sum(confident_values) / len(confident_values) if confident_values else None
    low_count = sum(1 for v in confident_values if v < threshold)
    return average, low_count


def test_average_confidence_all_high():
    avg, low = _compute_metrics([0.9, 0.8, 0.95])
    assert avg == pytest.approx(0.883, abs=0.01)
    assert low == 0


def test_average_confidence_mixed():
    avg, low = _compute_metrics([0.9, 0.5, 0.4])
    assert avg == pytest.approx(0.6, abs=0.01)
    assert low == 2


def test_average_confidence_all_none():
    avg, low = _compute_metrics([None, None])
    assert avg is None
    assert low == 0


def test_average_confidence_empty():
    avg, low = _compute_metrics([])
    assert avg is None
    assert low == 0


def test_low_confidence_count_boundary():
    avg, low = _compute_metrics([0.6, 0.59, 0.61])
    assert low == 1  # only 0.59 is below threshold


def test_all_segments_low_confidence():
    avg, low = _compute_metrics([0.1, 0.2, 0.3])
    assert low == 3
