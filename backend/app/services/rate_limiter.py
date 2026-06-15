"""Per-user rate-limit checks enforced at the DB layer.

Per-IP request-rate limiting is handled by slowapi on the POST route.
These checks enforce per-user business limits that require DB state.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.transcription_job import JobStatus, TranscriptionJob


class RateLimitError(Exception):
    """Raised when a per-user limit is exceeded.  Message is user-safe."""


async def check_user_limits(
    db: AsyncSession,
    user_id: Optional[uuid.UUID],
) -> None:
    """Raise RateLimitError if the user has hit their active-job or daily-job cap.

    Anonymous submissions (user_id=None) are not subject to DB limits;
    they are constrained only by the per-IP slowapi limiter on the route.
    """
    if user_id is None:
        return

    active = await _count_active_jobs(db, user_id)
    if active >= settings.max_active_jobs_per_user:
        raise RateLimitError(
            f"You already have {active} job(s) in progress. "
            f"Please wait for them to complete before submitting more."
        )

    daily = await _count_daily_jobs(db, user_id)
    if daily >= settings.max_daily_jobs_per_user:
        raise RateLimitError(
            f"You have reached the daily limit of {settings.max_daily_jobs_per_user} "
            "transcriptions. Please try again tomorrow."
        )


async def _count_active_jobs(db: AsyncSession, user_id: uuid.UUID) -> int:
    active_statuses = [JobStatus.pending, JobStatus.processing]
    result = await db.execute(
        select(func.count(TranscriptionJob.id)).where(
            TranscriptionJob.user_id == user_id,
            TranscriptionJob.status.in_(active_statuses),
            TranscriptionJob.deleted_at.is_(None),
        )
    )
    return result.scalar_one()


async def _count_daily_jobs(db: AsyncSession, user_id: uuid.UUID) -> int:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(TranscriptionJob.id)).where(
            TranscriptionJob.user_id == user_id,
            TranscriptionJob.created_at >= today_start,
            TranscriptionJob.deleted_at.is_(None),
        )
    )
    return result.scalar_one()
