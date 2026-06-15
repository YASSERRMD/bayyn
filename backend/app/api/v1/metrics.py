"""Metrics endpoint: aggregate DB stats in a Prometheus-style JSON shape."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import cast, case, extract, func, select, Float
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import RequiredAdmin
from app.database import get_session
from app.models.transcription_job import JobStatus, ProcessingStrategy, TranscriptionJob

router = APIRouter(prefix="/metrics", tags=["metrics"])

DbSession = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=None)
async def get_metrics(db: DbSession, _admin: RequiredAdmin) -> JSONResponse:
    """Return aggregate job metrics.  Admin-only.

    Shape mirrors Prometheus gauge/counter conventions but uses JSON.
    """
    base = [TranscriptionJob.deleted_at.is_(None)]

    # ── counts by status ──────────────────────────────────────────────────────
    status_rows = await db.execute(
        select(TranscriptionJob.status, func.count(TranscriptionJob.id).label("n"))
        .where(*base)
        .group_by(TranscriptionJob.status)
    )
    jobs_by_status: dict[str, int] = {}
    for row in status_rows:
        key = row.status.value if hasattr(row.status, "value") else str(row.status)
        jobs_by_status[key] = row.n
    jobs_total = sum(jobs_by_status.values())

    # ── counts by strategy ────────────────────────────────────────────────────
    strat_rows = await db.execute(
        select(TranscriptionJob.processing_strategy, func.count(TranscriptionJob.id).label("n"))
        .where(*base)
        .group_by(TranscriptionJob.processing_strategy)
    )
    jobs_by_strategy: dict[str, int] = {}
    for row in strat_rows:
        key = row.processing_strategy.value if hasattr(row.processing_strategy, "value") else str(row.processing_strategy)
        jobs_by_strategy[key] = row.n

    # ── success rate ──────────────────────────────────────────────────────────
    completed = jobs_by_status.get(JobStatus.completed.value, 0)
    failed = jobs_by_status.get(JobStatus.failed.value, 0)
    terminal = completed + failed
    success_rate = round(completed / terminal, 4) if terminal > 0 else None

    # ── dead letters ──────────────────────────────────────────────────────────
    dl_result = await db.execute(
        select(func.count(TranscriptionJob.id))
        .where(*base, TranscriptionJob.is_dead_letter.is_(True))
    )
    dead_letter_count = dl_result.scalar_one()

    # ── retry rate ────────────────────────────────────────────────────────────
    retried_result = await db.execute(
        select(func.count(TranscriptionJob.id))
        .where(*base, TranscriptionJob.retry_count > 0)
    )
    retried_count = retried_result.scalar_one()
    retry_rate = round(retried_count / jobs_total, 4) if jobs_total > 0 else None

    # ── average processing duration (completed jobs only) ─────────────────────
    dur_result = await db.execute(
        select(
            func.avg(
                extract("epoch", TranscriptionJob.completed_at) -
                extract("epoch", TranscriptionJob.started_at)
            )
        )
        .where(
            *base,
            TranscriptionJob.status == JobStatus.completed,
            TranscriptionJob.started_at.isnot(None),
            TranscriptionJob.completed_at.isnot(None),
        )
    )
    avg_duration_raw = dur_result.scalar_one()
    avg_duration_seconds = round(float(avg_duration_raw), 2) if avg_duration_raw is not None else None

    return JSONResponse({
        "jobs_total": jobs_total,
        "jobs_by_status": jobs_by_status,
        "jobs_by_strategy": jobs_by_strategy,
        "success_rate": success_rate,
        "retry_rate": retry_rate,
        "dead_letter_count": dead_letter_count,
        "avg_processing_duration_seconds": avg_duration_seconds,
    })
