"""Tests for user ownership & authorization on transcription jobs."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _scalar_result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _make_job(user_id=None, deleted_at=None):
    from app.models.transcription_job import JobStatus, ProcessingStrategy
    job = MagicMock()
    job.id = uuid.uuid4()
    job.user_id = user_id
    job.deleted_at = deleted_at
    job.status = JobStatus.completed
    job.media_stored = False
    return job


# ── Service-level ownership ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_job_owner_can_access_own_job():
    from app.services.transcription_service import get_job

    owner_id = uuid.uuid4()
    job = _make_job(user_id=owner_id)
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalar_result(job))

    result = await get_job(db, job.id, requester_id=owner_id)
    assert result is job


@pytest.mark.asyncio
async def test_get_job_non_owner_returns_none():
    from app.services.transcription_service import get_job

    owner_id = uuid.uuid4()
    other_id = uuid.uuid4()
    job = _make_job(user_id=owner_id)
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalar_result(job))

    result = await get_job(db, job.id, requester_id=other_id)
    assert result is None


@pytest.mark.asyncio
async def test_get_job_anonymous_job_accessible_to_anyone():
    from app.services.transcription_service import get_job

    job = _make_job(user_id=None)  # anonymous job
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalar_result(job))

    # Any requester_id (or None) can access anonymous jobs
    result_no_user = await get_job(db, job.id, requester_id=None)
    assert result_no_user is job

    db.execute = AsyncMock(return_value=_scalar_result(job))
    result_with_user = await get_job(db, job.id, requester_id=uuid.uuid4())
    assert result_with_user is job


@pytest.mark.asyncio
async def test_get_job_unauthenticated_cannot_access_owned_job():
    from app.services.transcription_service import get_job

    owner_id = uuid.uuid4()
    job = _make_job(user_id=owner_id)
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalar_result(job))

    # requester_id=None means unauthenticated — should NOT see owned jobs
    result = await get_job(db, job.id, requester_id=None)
    assert result is None


@pytest.mark.asyncio
async def test_get_job_not_found_returns_none():
    from app.services.transcription_service import get_job

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalar_result(None))

    result = await get_job(db, uuid.uuid4(), requester_id=uuid.uuid4())
    assert result is None


# ── delete_job ownership ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_job_non_owner_cannot_delete():
    from app.services.transcription_service import delete_job

    owner_id = uuid.uuid4()
    other_id = uuid.uuid4()
    job = _make_job(user_id=owner_id)

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalar_result(job))
    db.delete = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    with patch("app.services.transcription_service.settings") as mock_settings:
        mock_settings.soft_delete_jobs = True
        result = await delete_job(db, job.id, requester_id=other_id)

    assert result is False
    db.delete.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_delete_job_owner_can_delete():
    from app.services.transcription_service import delete_job

    owner_id = uuid.uuid4()
    job = _make_job(user_id=owner_id)

    execute_results = [
        _scalar_result(job),  # get_job
        _scalar_result(None),  # TranscriptDocument
        _scalars_result([]),   # TranscriptSegment
    ]

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=lambda s: execute_results.pop(0))
    db.delete = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    with patch("app.services.transcription_service.settings") as mock_settings:
        mock_settings.soft_delete_jobs = True
        result = await delete_job(db, job.id, requester_id=owner_id)

    assert result is True


# ── Ownership prevents enumeration (404 for wrong user, not 403) ──────────────

@pytest.mark.asyncio
async def test_wrong_user_returns_same_as_not_found():
    """Ensures ownership errors and missing-job errors are indistinguishable."""
    from app.services.transcription_service import get_job

    owner_id = uuid.uuid4()
    wrong_id = uuid.uuid4()
    job = _make_job(user_id=owner_id)

    db_with_job = AsyncMock()
    db_with_job.execute = AsyncMock(return_value=_scalar_result(job))
    wrong_user_result = await get_job(db_with_job, job.id, requester_id=wrong_id)

    db_no_job = AsyncMock()
    db_no_job.execute = AsyncMock(return_value=_scalar_result(None))
    not_found_result = await get_job(db_no_job, uuid.uuid4(), requester_id=wrong_id)

    # Both should be None — callers raise 404 in both cases
    assert wrong_user_result is None
    assert not_found_result is None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _scalars_result(values):
    r = MagicMock()
    r.scalars.return_value.all.return_value = values
    return r
