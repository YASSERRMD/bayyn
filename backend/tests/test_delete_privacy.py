"""Tests for delete_job service: soft-delete vs hard-delete behavior."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest


def _make_job():
    from app.models.transcription_job import JobStatus
    job = MagicMock()
    job.id = uuid.uuid4()
    job.user_id = None  # anonymous job — accessible to any requester
    job.deleted_at = None
    job.status = JobStatus.completed
    return job


def _make_db(job, doc=None, segments=None, logs=None):
    """Return a mock AsyncSession that serves the given objects."""
    segments = segments or []
    logs = logs or []

    async def _execute(stmt):
        result = MagicMock()
        # Return different results based on what was queried
        obj = doc or MagicMock(spec=[])
        # We'll use call_count to distinguish queries
        result.scalar_one_or_none.return_value = doc
        result.scalars.return_value.all.return_value = segments
        return result

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=_execute)
    db.delete = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    return db


# ── Soft-delete (default) ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_soft_delete_sets_deleted_at():
    from app.services.transcription_service import delete_job

    job = _make_job()
    job_id = job.id
    db = AsyncMock()

    execute_results = [
        # get_job: returns job
        _scalar_result(job),
        # TranscriptDocument query: returns None
        _scalar_result(None),
        # TranscriptSegment query: returns []
        _scalars_result([]),
    ]
    db.execute = AsyncMock(side_effect=lambda s: execute_results.pop(0))
    db.delete = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    with patch("app.services.transcription_service.settings") as mock_settings:
        mock_settings.soft_delete_jobs = True
        result = await delete_job(db, job_id, hard_delete=False)

    assert result is True
    # job.deleted_at must have been set
    assert job.deleted_at is not None
    # job record must NOT have been hard-deleted
    for call_args in db.delete.call_args_list:
        assert call_args[0][0] is not job


@pytest.mark.asyncio
async def test_hard_delete_removes_job_record():
    from app.services.transcription_service import delete_job

    job = _make_job()
    job_id = job.id
    db = AsyncMock()

    execute_results = [
        _scalar_result(job),   # get_job
        _scalar_result(None),  # doc
        _scalars_result([]),   # segments
        _scalars_result([]),   # audit logs
    ]
    db.execute = AsyncMock(side_effect=lambda s: execute_results.pop(0))
    db.delete = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    with patch("app.services.transcription_service.settings") as mock_settings:
        mock_settings.soft_delete_jobs = True  # setting is True but caller passes hard_delete=True
        result = await delete_job(db, job_id, hard_delete=True)

    assert result is True
    # job must have been passed to db.delete
    deleted_objects = [c[0][0] for c in db.delete.call_args_list]
    assert job in deleted_objects
    # job.deleted_at must NOT have been set
    assert job.deleted_at is None


@pytest.mark.asyncio
async def test_soft_delete_false_config_always_hard_deletes():
    from app.services.transcription_service import delete_job

    job = _make_job()
    job_id = job.id
    db = AsyncMock()

    execute_results = [
        _scalar_result(job),
        _scalar_result(None),
        _scalars_result([]),
        _scalars_result([]),
    ]
    db.execute = AsyncMock(side_effect=lambda s: execute_results.pop(0))
    db.delete = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    with patch("app.services.transcription_service.settings") as mock_settings:
        mock_settings.soft_delete_jobs = False  # config forces hard delete
        result = await delete_job(db, job_id, hard_delete=False)  # caller did NOT request hard

    assert result is True
    deleted_objects = [c[0][0] for c in db.delete.call_args_list]
    assert job in deleted_objects


@pytest.mark.asyncio
async def test_delete_job_returns_false_for_missing_job():
    from app.services.transcription_service import delete_job

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalar_result(None))
    db.delete = AsyncMock()

    with patch("app.services.transcription_service.settings") as mock_settings:
        mock_settings.soft_delete_jobs = True
        result = await delete_job(db, uuid.uuid4())

    assert result is False
    db.delete.assert_not_called()


@pytest.mark.asyncio
async def test_soft_delete_writes_audit_log():
    from app.services.transcription_service import delete_job
    from app.models.audit_log import AuditLog

    job = _make_job()
    job_id = job.id
    db = AsyncMock()

    execute_results = [
        _scalar_result(job),
        _scalar_result(None),
        _scalars_result([]),
    ]
    db.execute = AsyncMock(side_effect=lambda s: execute_results.pop(0))
    db.delete = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    with patch("app.services.transcription_service.settings") as mock_settings:
        mock_settings.soft_delete_jobs = True
        await delete_job(db, job_id, hard_delete=False)

    added_objects = [c[0][0] for c in db.add.call_args_list]
    audit_entries = [o for o in added_objects if isinstance(o, AuditLog)]
    assert len(audit_entries) == 1
    assert audit_entries[0].action == "job_deleted"


# ── Config ────────────────────────────────────────────────────────────────────

def test_soft_delete_jobs_default_true():
    from app.config import Settings
    s = Settings()
    assert s.soft_delete_jobs is True


# ── Helpers ───────────────────────────────────────────────────────────────────

def _scalar_result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _scalars_result(values):
    r = MagicMock()
    r.scalars.return_value.all.return_value = values
    return r
