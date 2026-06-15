"""Admin-only endpoints — requires is_admin=True in JWT."""
from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import RequiredAdmin
from app.database import get_session
from app.models.transcription_job import JobStatus, ProcessingStrategy, TranscriptionJob

router = APIRouter(prefix="/admin", tags=["admin"])

DbSession = Annotated[AsyncSession, Depends(get_session)]


class AdminJobEntry(BaseModel):
    job_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    source_url: str
    source_domain: Optional[str]
    status: str
    processing_strategy: str
    retry_count: int
    is_dead_letter: bool
    media_stored: bool
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]

    model_config = {"from_attributes": True}


class AdminJobListResponse(BaseModel):
    jobs: list[AdminJobEntry]
    total: int


@router.get("/jobs", response_model=AdminJobListResponse)
async def admin_list_jobs(
    db: DbSession,
    _admin: RequiredAdmin,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, description="Filter by job status"),
    user_id: Optional[uuid.UUID] = Query(None, description="Filter by owner user_id"),
) -> AdminJobListResponse:
    filters = [TranscriptionJob.deleted_at.is_(None)]
    if status is not None:
        try:
            filters.append(TranscriptionJob.status == JobStatus(status))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Unknown status value: {status!r}")
    if user_id is not None:
        filters.append(TranscriptionJob.user_id == user_id)

    count_result = await db.execute(
        select(func.count(TranscriptionJob.id)).where(*filters)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(TranscriptionJob)
        .where(*filters)
        .order_by(TranscriptionJob.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    jobs = list(result.scalars().all())

    return AdminJobListResponse(
        jobs=[_job_to_admin_entry(j) for j in jobs],
        total=total,
    )


@router.get("/jobs/{job_id}", response_model=AdminJobEntry)
async def admin_get_job(
    job_id: uuid.UUID,
    db: DbSession,
    _admin: RequiredAdmin,
) -> AdminJobEntry:
    result = await db.execute(
        select(TranscriptionJob).where(
            TranscriptionJob.id == job_id,
            TranscriptionJob.deleted_at.is_(None),
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return _job_to_admin_entry(job)


def _job_to_admin_entry(job: TranscriptionJob) -> AdminJobEntry:
    return AdminJobEntry(
        job_id=job.id,
        user_id=job.user_id,
        source_url=job.source_url,
        source_domain=job.source_domain,
        status=job.status.value if hasattr(job.status, "value") else str(job.status),
        processing_strategy=(
            job.processing_strategy.value
            if hasattr(job.processing_strategy, "value")
            else str(job.processing_strategy)
        ),
        retry_count=job.retry_count or 0,
        is_dead_letter=job.is_dead_letter or False,
        media_stored=job.media_stored,
        created_at=job.created_at.isoformat() if job.created_at else "",
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )
