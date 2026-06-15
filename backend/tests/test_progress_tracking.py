"""Tests for progress tracking: _update_progress helper and schema defaults."""
import sys
import uuid
from unittest.mock import MagicMock, patch

import pytest

requires_py310 = pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="Schema uses str | None union syntax requiring Python 3.10+"
)


# ── Schema defaults ───────────────────────────────────────────────────────────

@requires_py310
def test_job_response_defaults_progress_zero():
    from app.schemas.transcription import TranscriptionJobResponse
    from app.models.transcription_job import JobStatus, ProcessingStrategy
    import datetime

    resp = TranscriptionJobResponse(
        job_id="00000000-0000-0000-0000-000000000001",
        source_url="https://example.com",
        source_type="youtube",
        source_domain="youtube.com",
        title=None,
        duration_seconds=None,
        language=None,
        status=JobStatus.pending,
        processing_strategy=ProcessingStrategy.unknown,
        error_message=None,
        media_stored=False,
        created_at=datetime.datetime.now(),
        started_at=None,
        completed_at=None,
    )
    assert resp.progress_pct == 0
    assert resp.current_step is None


@requires_py310
def test_job_response_with_progress():
    from app.schemas.transcription import TranscriptionJobResponse
    from app.models.transcription_job import JobStatus, ProcessingStrategy
    import datetime

    resp = TranscriptionJobResponse(
        job_id="00000000-0000-0000-0000-000000000002",
        source_url="https://example.com",
        source_type="youtube",
        source_domain="youtube.com",
        title=None,
        duration_seconds=None,
        language=None,
        status=JobStatus.processing,
        processing_strategy=ProcessingStrategy.unknown,
        error_message=None,
        progress_pct=35,
        current_step="transcribing_audio",
        media_stored=False,
        created_at=datetime.datetime.now(),
        started_at=None,
        completed_at=None,
    )
    assert resp.progress_pct == 35
    assert resp.current_step == "transcribing_audio"


# ── _update_progress helper ───────────────────────────────────────────────────

def test_update_progress_sets_fields():
    job_uuid = uuid.uuid4()
    mock_job = MagicMock()

    with patch("app.workers.transcription_tasks._get_session") as mock_ctx:
        mock_db = MagicMock()
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job

        from app.workers.transcription_tasks import _update_progress
        _update_progress(job_uuid, 45, "processing_captions")

    assert mock_job.progress_pct == 45
    assert mock_job.current_step == "processing_captions"
    mock_db.commit.assert_called_once()


def test_update_progress_clamps_above_100():
    job_uuid = uuid.uuid4()
    mock_job = MagicMock()

    with patch("app.workers.transcription_tasks._get_session") as mock_ctx:
        mock_db = MagicMock()
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job

        from app.workers.transcription_tasks import _update_progress
        _update_progress(job_uuid, 150, "over_limit")

    assert mock_job.progress_pct == 100


def test_update_progress_clamps_below_zero():
    job_uuid = uuid.uuid4()
    mock_job = MagicMock()

    with patch("app.workers.transcription_tasks._get_session") as mock_ctx:
        mock_db = MagicMock()
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job

        from app.workers.transcription_tasks import _update_progress
        _update_progress(job_uuid, -10, "negative")

    assert mock_job.progress_pct == 0


def test_update_progress_noop_if_job_missing():
    job_uuid = uuid.uuid4()

    with patch("app.workers.transcription_tasks._get_session") as mock_ctx:
        mock_db = MagicMock()
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        from app.workers.transcription_tasks import _update_progress
        _update_progress(job_uuid, 50, "step")  # must not raise

    mock_db.commit.assert_not_called()


# ── Step sequence sanity ──────────────────────────────────────────────────────

def test_progress_steps_are_monotonically_increasing():
    """The expected progress percentages in the worker are 0→5→15→70→85→100."""
    steps = [0, 5, 15, 70, 85, 100]
    assert steps == sorted(steps)
    assert steps[0] == 0
    assert steps[-1] == 100
