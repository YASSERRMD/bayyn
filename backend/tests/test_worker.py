import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

requires_db = pytest.mark.skipif(
    not __import__("importlib").util.find_spec("asyncpg"),
    reason="asyncpg not installed; tests run in Docker with Python 3.12"
)


def make_fake_job(job_id):
    from app.models.transcription_job import JobStatus, ProcessingStrategy
    job = MagicMock()
    job.id = job_id
    job.source_url = "https://www.youtube.com/watch?v=test"
    job.status = JobStatus.pending
    job.media_stored = False
    return job


@requires_db
def test_sanitize_error_redacts_url():
    from app.workers.transcription_tasks import _sanitize_error
    msg = "Failed to download https://secret.cloudfront.net/audio.m4a?token=abc123"
    result = _sanitize_error(msg)
    assert "https://" not in result
    assert "[URL_REDACTED]" in result


@requires_db
def test_sanitize_error_redacts_tmp_path():
    from app.workers.transcription_tasks import _sanitize_error
    job_id = uuid.uuid4()
    msg = f"File not found: /tmp/bayyn/{job_id}/audio.wav"
    result = _sanitize_error(msg)
    assert "/tmp/" not in result
    assert "[PATH_REDACTED]" in result


@requires_db
def test_sanitize_error_truncates_long_message():
    from app.workers.transcription_tasks import _sanitize_error
    long_msg = "x" * 1000
    result = _sanitize_error(long_msg)
    assert len(result) <= 512


def test_temp_dir_created_and_cleaned_on_success(tmp_path):
    from app.temp_manager import TempManager
    job_id = uuid.uuid4()

    with patch.object(TempManager, "_base_dir", return_value=tmp_path):
        job_dir = TempManager.create_job_dir(job_id)
        assert job_dir.exists()
        success = TempManager.cleanup_job_dir(job_id, reason="completed")
        assert success
        assert not job_dir.exists()


def test_temp_dir_cleaned_on_failure(tmp_path):
    from app.temp_manager import TempManager
    job_id = uuid.uuid4()

    with patch.object(TempManager, "_base_dir", return_value=tmp_path):
        job_dir = TempManager.create_job_dir(job_id)
        (job_dir / "audio.wav").write_bytes(b"fake audio")
        assert job_dir.exists()
        success = TempManager.cleanup_job_dir(job_id, reason="failure")
        assert success
        assert not job_dir.exists()


def test_no_temp_files_remain_after_job(tmp_path):
    from app.temp_manager import TempManager
    job_id = uuid.uuid4()

    with patch.object(TempManager, "_base_dir", return_value=tmp_path):
        TempManager.create_job_dir(job_id)
        TempManager.cleanup_job_dir(job_id)
        assert not (tmp_path / str(job_id)).exists()


@requires_db
def test_media_stored_never_true():
    """Worker must never set media_stored=True."""
    from app.workers.transcription_tasks import _store_transcript

    with patch("app.workers.transcription_tasks._get_session") as mock_session_ctx:
        mock_db = MagicMock()
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)

        mock_job = MagicMock()
        mock_job.media_stored = False
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job

        from app.models.transcription_job import ProcessingStrategy
        _store_transcript(uuid.uuid4(), [], ProcessingStrategy.caption)

        assert mock_job.media_stored is False
