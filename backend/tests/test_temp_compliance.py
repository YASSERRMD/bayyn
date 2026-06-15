"""Phase 35: Temp file compliance — per-job directories cleaned in every exit path."""
import inspect
import os
import time
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ── TempManager: core lifecycle ───────────────────────────────────────────────

class TestTempManagerLifecycle:
    def test_create_makes_directory(self, tmp_path):
        from app.temp_manager import TempManager
        job_id = uuid.uuid4()
        with patch.object(TempManager, "_base_dir", return_value=tmp_path):
            job_dir = TempManager.create_job_dir(job_id)
        assert job_dir.exists() and job_dir.is_dir()

    def test_create_returns_path_under_base(self, tmp_path):
        from app.temp_manager import TempManager
        job_id = uuid.uuid4()
        with patch.object(TempManager, "_base_dir", return_value=tmp_path):
            job_dir = TempManager.create_job_dir(job_id)
        assert job_dir == tmp_path / str(job_id)

    def test_create_idempotent(self, tmp_path):
        from app.temp_manager import TempManager
        job_id = uuid.uuid4()
        with patch.object(TempManager, "_base_dir", return_value=tmp_path):
            d1 = TempManager.create_job_dir(job_id)
            d2 = TempManager.create_job_dir(job_id)
        assert d1 == d2
        assert d1.exists()

    def test_cleanup_removes_empty_dir(self, tmp_path):
        from app.temp_manager import TempManager
        job_id = uuid.uuid4()
        with patch.object(TempManager, "_base_dir", return_value=tmp_path):
            TempManager.create_job_dir(job_id)
            result = TempManager.cleanup_job_dir(job_id, reason="completed")
        assert result is True
        assert not (tmp_path / str(job_id)).exists()

    def test_cleanup_removes_nested_content(self, tmp_path):
        """Cleanup must recursively remove files and subdirectories."""
        from app.temp_manager import TempManager
        job_id = uuid.uuid4()
        with patch.object(TempManager, "_base_dir", return_value=tmp_path):
            job_dir = TempManager.create_job_dir(job_id)
            (job_dir / "audio.wav").write_bytes(b"\x00" * 1024)
            chunks = job_dir / "chunks"
            chunks.mkdir()
            (chunks / "chunk_001.wav").write_bytes(b"\x00" * 512)
            (chunks / "chunk_002.wav").write_bytes(b"\x00" * 512)
            result = TempManager.cleanup_job_dir(job_id, reason="completed")
        assert result is True
        assert not job_dir.exists()
        assert not (tmp_path / str(job_id)).exists()

    def test_cleanup_idempotent_when_dir_missing(self, tmp_path):
        from app.temp_manager import TempManager
        job_id = uuid.uuid4()
        with patch.object(TempManager, "_base_dir", return_value=tmp_path):
            result = TempManager.cleanup_job_dir(job_id, reason="completed")
        assert result is True

    def test_cleanup_idempotent_on_second_call(self, tmp_path):
        from app.temp_manager import TempManager
        job_id = uuid.uuid4()
        with patch.object(TempManager, "_base_dir", return_value=tmp_path):
            TempManager.create_job_dir(job_id)
            TempManager.cleanup_job_dir(job_id)
            result = TempManager.cleanup_job_dir(job_id)
        assert result is True

    def test_no_files_remain_after_cleanup(self, tmp_path):
        from app.temp_manager import TempManager
        job_id = uuid.uuid4()
        with patch.object(TempManager, "_base_dir", return_value=tmp_path):
            job_dir = TempManager.create_job_dir(job_id)
            for name in ("audio.m4a", "transcript.json", "model_cache.bin"):
                (job_dir / name).write_bytes(b"data")
            TempManager.cleanup_job_dir(job_id, reason="failure")
        assert not job_dir.exists()
        # Base dir itself still exists (other jobs may be there)
        assert tmp_path.exists()

    def test_get_job_dir_returns_expected_path(self, tmp_path):
        from app.temp_manager import TempManager
        job_id = uuid.uuid4()
        with patch.object(TempManager, "_base_dir", return_value=tmp_path):
            path = TempManager.get_job_dir(job_id)
        assert path == tmp_path / str(job_id)

    def test_log_does_not_expose_real_path(self, tmp_path, caplog):
        """Log lines must hash the path, never log it verbatim."""
        import logging
        from app.temp_manager import TempManager
        job_id = uuid.uuid4()
        with (
            patch.object(TempManager, "_base_dir", return_value=tmp_path),
            caplog.at_level(logging.DEBUG, logger="app.temp_manager"),
        ):
            TempManager.create_job_dir(job_id)
        # Real path must not appear in log output
        assert str(tmp_path) not in caplog.text
        assert str(job_id) not in caplog.text


# ── Startup cleanup ───────────────────────────────────────────────────────────

class TestStartupCleanup:
    def test_removes_stale_dir_older_than_one_hour(self, tmp_path):
        from app.temp_manager import TempManager
        stale = tmp_path / str(uuid.uuid4())
        stale.mkdir()
        old_time = time.time() - 7201
        os.utime(stale, (old_time, old_time))
        with patch.object(TempManager, "_base_dir", return_value=tmp_path):
            TempManager.startup_cleanup()
        assert not stale.exists()

    def test_preserves_recent_dir(self, tmp_path):
        from app.temp_manager import TempManager
        recent = tmp_path / str(uuid.uuid4())
        recent.mkdir()
        with patch.object(TempManager, "_base_dir", return_value=tmp_path):
            TempManager.startup_cleanup()
        assert recent.exists()

    def test_creates_base_dir_when_absent(self, tmp_path):
        from app.temp_manager import TempManager
        new_base = tmp_path / "never_existed"
        assert not new_base.exists()
        with patch.object(TempManager, "_base_dir", return_value=new_base):
            TempManager.startup_cleanup()
        assert new_base.exists()

    def test_removes_only_stale_keeps_recent(self, tmp_path):
        from app.temp_manager import TempManager
        stale = tmp_path / str(uuid.uuid4())
        stale.mkdir()
        os.utime(stale, (time.time() - 7200, time.time() - 7200))

        recent = tmp_path / str(uuid.uuid4())
        recent.mkdir()

        with patch.object(TempManager, "_base_dir", return_value=tmp_path):
            TempManager.startup_cleanup()

        assert not stale.exists()
        assert recent.exists()


# ── media_stored = False invariant ────────────────────────────────────────────

class TestMediaStoredInvariant:
    def test_store_transcript_never_sets_media_stored_true(self):
        from app.workers.transcription_tasks import _store_transcript
        from app.models.transcription_job import ProcessingStrategy

        mock_db = MagicMock()
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=mock_db)
        ctx.__exit__ = MagicMock(return_value=False)

        mock_job = MagicMock()
        mock_job.media_stored = False
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job

        with patch("app.workers.transcription_tasks._get_session", return_value=ctx):
            _store_transcript(uuid.uuid4(), [], ProcessingStrategy.caption)

        assert mock_job.media_stored is False

    def test_media_stored_never_assigned_true_in_source(self):
        from app.workers import transcription_tasks
        source = inspect.getsource(transcription_tasks)
        assert "media_stored = True" not in source
        assert "media_stored=True" not in source

    def test_temp_manager_never_copies_files_out(self):
        from app.temp_manager import TempManager
        source = inspect.getsource(TempManager)
        assert "shutil.copy" not in source
        assert "shutil.move" not in source

    def test_store_transcript_explicitly_sets_false(self):
        """_store_transcript must explicitly set media_stored=False (not just leave it unset)."""
        from app.workers import transcription_tasks
        source = inspect.getsource(transcription_tasks._store_transcript)
        assert "media_stored = False" in source or "media_stored=False" in source


# ── Worker task: cleanup called in all exit paths ─────────────────────────────

def _make_db_mock_with_job(job_uuid):
    from app.models.transcription_job import JobStatus
    job = MagicMock()
    job.id = job_uuid
    job.source_url = "https://www.youtube.com/watch?v=test"
    job.status = JobStatus.pending
    job.retry_count = 0
    job.media_stored = False
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = job
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=mock_db)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


class TestWorkerCleanupPaths:
    def test_cleanup_called_on_success_path(self, tmp_path):
        from app.workers.transcription_tasks import process_transcription_job
        from app.temp_manager import TempManager
        job_uuid = uuid.uuid4()
        ctx = _make_db_mock_with_job(job_uuid)

        cleanup_calls = []
        original_cleanup = TempManager.cleanup_job_dir.__func__ if hasattr(TempManager.cleanup_job_dir, "__func__") else TempManager.cleanup_job_dir

        with (
            patch("app.workers.transcription_tasks._get_session", return_value=ctx),
            patch("app.workers.transcription_tasks._run_transcription"),
            patch.object(TempManager, "_base_dir", return_value=tmp_path),
            patch.object(TempManager, "cleanup_job_dir", side_effect=lambda *a, **kw: cleanup_calls.append(kw.get("reason", a[1] if len(a) > 1 else "")) or True) as spy,
        ):
            result = process_transcription_job.run(str(job_uuid))

        assert spy.called, "cleanup_job_dir was not called on the success path"
        assert result["status"] == "completed"

    def test_cleanup_called_on_exception_path(self, tmp_path):
        from app.workers.transcription_tasks import process_transcription_job, MAX_RETRIES
        from app.temp_manager import TempManager
        job_uuid = uuid.uuid4()
        ctx = _make_db_mock_with_job(job_uuid)

        cleanup_spy = MagicMock(return_value=True)

        with (
            patch("app.workers.transcription_tasks._get_session", return_value=ctx),
            patch(
                "app.workers.transcription_tasks._run_transcription",
                side_effect=RuntimeError("boom"),
            ),
            patch.object(TempManager, "_base_dir", return_value=tmp_path),
            patch.object(TempManager, "cleanup_job_dir", cleanup_spy),
            patch("app.workers.transcription_tasks._fail_job"),
        ):
            # push_request sets retries=MAX_RETRIES so the dead-letter branch is taken
            process_transcription_job.push_request(retries=MAX_RETRIES)
            try:
                process_transcription_job.run(str(job_uuid))
            finally:
                process_transcription_job.pop_request()

        cleanup_spy.assert_called_once()

    def test_cleanup_reason_is_failure_on_exception(self, tmp_path):
        from app.workers.transcription_tasks import process_transcription_job, MAX_RETRIES
        from app.temp_manager import TempManager
        job_uuid = uuid.uuid4()
        ctx = _make_db_mock_with_job(job_uuid)

        cleanup_spy = MagicMock(return_value=True)

        with (
            patch("app.workers.transcription_tasks._get_session", return_value=ctx),
            patch(
                "app.workers.transcription_tasks._run_transcription",
                side_effect=RuntimeError("boom"),
            ),
            patch.object(TempManager, "_base_dir", return_value=tmp_path),
            patch.object(TempManager, "cleanup_job_dir", cleanup_spy),
            patch("app.workers.transcription_tasks._fail_job"),
        ):
            process_transcription_job.push_request(retries=MAX_RETRIES)
            try:
                process_transcription_job.run(str(job_uuid))
            finally:
                process_transcription_job.pop_request()

        _call_kwargs = cleanup_spy.call_args
        reason = _call_kwargs[1].get("reason") or (_call_kwargs[0][1] if len(_call_kwargs[0]) > 1 else None)
        assert reason == "failure"

    def test_cleanup_reason_is_completed_on_success(self, tmp_path):
        from app.workers.transcription_tasks import process_transcription_job
        from app.temp_manager import TempManager
        job_uuid = uuid.uuid4()
        ctx = _make_db_mock_with_job(job_uuid)

        cleanup_spy = MagicMock(return_value=True)

        with (
            patch("app.workers.transcription_tasks._get_session", return_value=ctx),
            patch("app.workers.transcription_tasks._run_transcription"),
            patch.object(TempManager, "_base_dir", return_value=tmp_path),
            patch.object(TempManager, "cleanup_job_dir", cleanup_spy),
        ):
            process_transcription_job.run(str(job_uuid))

        _call_kwargs = cleanup_spy.call_args
        reason = _call_kwargs[1].get("reason") or (_call_kwargs[0][1] if len(_call_kwargs[0]) > 1 else None)
        assert reason == "completed"

    def test_cleanup_is_not_skipped_on_exception(self):
        """Source-level check: cleanup must appear in the except block, not only in try."""
        from app.workers import transcription_tasks
        source = inspect.getsource(transcription_tasks.process_transcription_job)
        # cleanup_job_dir must be called at least twice in the function
        assert source.count("cleanup_job_dir") >= 2
