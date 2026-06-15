"""Tests for worker reliability: retry policy, exponential backoff, dead-letter state."""
import uuid
from unittest.mock import MagicMock, patch

import pytest


# ── Exponential backoff ───────────────────────────────────────────────────────

def test_exponential_backoff_attempt_0():
    from app.workers.transcription_tasks import _exponential_backoff
    assert _exponential_backoff(0) == 60


def test_exponential_backoff_attempt_1():
    from app.workers.transcription_tasks import _exponential_backoff
    assert _exponential_backoff(1) == 120


def test_exponential_backoff_attempt_2():
    from app.workers.transcription_tasks import _exponential_backoff
    assert _exponential_backoff(2) == 240


def test_exponential_backoff_increases():
    from app.workers.transcription_tasks import _exponential_backoff
    delays = [_exponential_backoff(i) for i in range(3)]
    assert delays == sorted(delays)


# ── MAX_RETRIES constant ──────────────────────────────────────────────────────

def test_max_retries_is_three():
    from app.workers.transcription_tasks import MAX_RETRIES
    assert MAX_RETRIES == 3


# ── Dead-letter state ─────────────────────────────────────────────────────────

def test_fail_job_sets_is_dead_letter_on_dead_letter_action():
    """When action=job_dead_letter, is_dead_letter must be True on the job."""
    job_uuid = uuid.uuid4()
    mock_job = MagicMock()
    mock_job.retry_count = 3

    with patch("app.workers.transcription_tasks._get_session") as mock_ctx:
        mock_db = MagicMock()
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job

        from app.workers.transcription_tasks import _fail_job
        _fail_job(job_uuid, "all retries exhausted", action="job_dead_letter")

    assert mock_job.is_dead_letter is True


def test_fail_job_does_not_set_dead_letter_on_normal_failure():
    """Normal failures must NOT set is_dead_letter."""
    job_uuid = uuid.uuid4()
    mock_job = MagicMock()
    mock_job.is_dead_letter = False
    mock_job.retry_count = 0

    with patch("app.workers.transcription_tasks._get_session") as mock_ctx:
        mock_db = MagicMock()
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job

        from app.workers.transcription_tasks import _fail_job
        _fail_job(job_uuid, "first failure", action="job_failed")

    assert mock_job.is_dead_letter is False


# ── Retry trigger ─────────────────────────────────────────────────────────────

def _task_func():
    """Return the raw unbound function for process_transcription_job."""
    from app.workers.transcription_tasks import process_transcription_job
    return process_transcription_job.run.__func__


def _make_db_ctx(mock_job):
    """Build a _get_session context manager that returns a mock DB with mock_job."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_job

    class _Ctx:
        def __enter__(self):
            return mock_db
        def __exit__(self, *a):
            return False

    return _Ctx, mock_db


def test_process_transcription_job_retries_on_failure():
    """On first failure (attempt=0 < MAX_RETRIES), task must call self.retry."""
    job_uuid = uuid.uuid4()
    mock_job = MagicMock()
    mock_job.id = job_uuid
    mock_job.retry_count = 0

    mock_task = MagicMock()
    mock_task.request.retries = 0  # first attempt

    retry_exc = RuntimeError("celery retry sentinel")
    mock_task.retry.side_effect = retry_exc

    _Ctx, _db = _make_db_ctx(mock_job)

    with patch("app.workers.transcription_tasks._get_session", return_value=_Ctx()), \
         patch("app.workers.transcription_tasks.TempManager") as mock_tm, \
         patch("app.workers.transcription_tasks._run_transcription", side_effect=RuntimeError("boom")), \
         patch("app.workers.transcription_tasks._log_retry_audit"):

        mock_tm.create_job_dir.return_value = MagicMock()

        with pytest.raises(RuntimeError, match="celery retry sentinel"):
            _task_func()(mock_task, str(job_uuid))

    mock_task.retry.assert_called_once()


def test_process_transcription_job_dead_letters_after_max_retries():
    """After MAX_RETRIES attempts, task must NOT retry and must mark dead-letter."""
    job_uuid = uuid.uuid4()
    mock_job = MagicMock()
    mock_job.id = job_uuid
    mock_job.retry_count = 3

    mock_task = MagicMock()
    mock_task.request.retries = 3  # last attempt

    _Ctx, _db = _make_db_ctx(mock_job)

    with patch("app.workers.transcription_tasks._get_session", return_value=_Ctx()), \
         patch("app.workers.transcription_tasks.TempManager") as mock_tm, \
         patch("app.workers.transcription_tasks._run_transcription", side_effect=RuntimeError("boom")), \
         patch("app.workers.transcription_tasks._fail_job") as mock_fail:

        mock_tm.create_job_dir.return_value = MagicMock()
        result = _task_func()(mock_task, str(job_uuid))

    mock_task.retry.assert_not_called()
    mock_fail.assert_called_once()
    _, kwargs = mock_fail.call_args
    assert kwargs.get("action") == "job_dead_letter"
    assert result["status"] == "failed"


# ── Retry count tracking ──────────────────────────────────────────────────────

def test_retry_count_stored_on_job():
    """retry_count on the job should reflect the current attempt number."""
    job_uuid = uuid.uuid4()
    mock_job = MagicMock()
    mock_job.id = job_uuid
    mock_job.retry_count = 0

    mock_task = MagicMock()
    mock_task.request.retries = 2  # third attempt
    mock_task.retry.side_effect = RuntimeError("stop retry")

    _Ctx, _db = _make_db_ctx(mock_job)

    with patch("app.workers.transcription_tasks._get_session", return_value=_Ctx()), \
         patch("app.workers.transcription_tasks.TempManager") as mock_tm, \
         patch("app.workers.transcription_tasks._run_transcription", side_effect=RuntimeError("x")), \
         patch("app.workers.transcription_tasks._log_retry_audit"):

        mock_tm.create_job_dir.return_value = MagicMock()
        with pytest.raises(RuntimeError, match="stop retry"):
            _task_func()(mock_task, str(job_uuid))

    assert mock_job.retry_count == 2
