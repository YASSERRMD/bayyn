from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.audit_log import AuditLog
from app.models.transcript_document import TranscriptDocument
from app.models.transcript_segment import TranscriptSegment
from app.models.transcription_job import JobStatus, ProcessingStrategy, TranscriptionJob
from app.security.url_validator import validate_url


async def create_transcription_job(
    db: AsyncSession,
    url: str,
    user_id: Optional[uuid.UUID] = None,
) -> TranscriptionJob:
    source_type, source_domain = validate_url(url)

    job = TranscriptionJob(
        id=uuid.uuid4(),
        user_id=user_id,
        source_url=url,
        source_type=source_type,
        source_domain=source_domain,
        status=JobStatus.pending,
        processing_strategy=ProcessingStrategy.unknown,
        media_stored=False,
    )
    db.add(job)
    await db.flush()

    audit = AuditLog(
        job_id=job.id,
        action="job_created",
        details={"source_type": source_type, "domain": source_domain},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job(
    db: AsyncSession,
    job_id: uuid.UUID,
    requester_id: Optional[uuid.UUID] = None,
) -> Optional[TranscriptionJob]:
    """Fetch a job by ID, applying ownership rules.

    - If the job has user_id=None (anonymous), anyone may access it.
    - If the job has a user_id, only that user (matched via requester_id) may access it.
    - Returns None if not found or not authorised (caller raises 404 to avoid enumeration).
    """
    result = await db.execute(
        select(TranscriptionJob).where(
            TranscriptionJob.id == job_id,
            TranscriptionJob.deleted_at.is_(None),
        )
    )
    job = result.scalar_one_or_none()
    if job is None:
        return None
    # Ownership check: anonymous jobs are public; owned jobs need matching requester
    if job.user_id is not None and job.user_id != requester_id:
        return None
    return job


async def list_jobs(
    db: AsyncSession,
    offset: int = 0,
    limit: int = 50,
    user_id: Optional[uuid.UUID] = None,
) -> tuple[list[TranscriptionJob], int]:
    base_filter = [TranscriptionJob.deleted_at.is_(None)]
    if user_id is not None:
        base_filter.append(TranscriptionJob.user_id == user_id)

    count_result = await db.execute(
        select(func.count(TranscriptionJob.id)).where(*base_filter)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(TranscriptionJob)
        .where(*base_filter)
        .order_by(TranscriptionJob.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def delete_job(
    db: AsyncSession,
    job_id: uuid.UUID,
    *,
    hard_delete: bool = False,
    requester_id: Optional[uuid.UUID] = None,
) -> bool:
    """Delete a job and all its transcript data.

    Transcript document and segments are always hard-deleted (privacy invariant:
    media_stored=False, no content is ever retained).

    The job record itself is soft-deleted by default (deleted_at tombstone) so
    the audit trail survives. Pass hard_delete=True, or set soft_delete_jobs=False
    in config, to permanently remove the job record too.
    """
    job = await get_job(db, job_id, requester_id=requester_id)
    if not job:
        return False

    # Always hard-delete transcript content
    doc_result = await db.execute(
        select(TranscriptDocument).where(TranscriptDocument.job_id == job_id)
    )
    doc = doc_result.scalar_one_or_none()
    if doc:
        await db.delete(doc)

    segs_result = await db.execute(
        select(TranscriptSegment).where(TranscriptSegment.job_id == job_id)
    )
    for seg in segs_result.scalars().all():
        await db.delete(seg)

    truly_hard = hard_delete or not settings.soft_delete_jobs

    if truly_hard:
        # Remove audit logs before deleting job (FK)
        logs_result = await db.execute(
            select(AuditLog).where(AuditLog.job_id == job_id)
        )
        for log in logs_result.scalars().all():
            await db.delete(log)
        await db.delete(job)
    else:
        job.deleted_at = datetime.now(timezone.utc)
        db.add(job)
        db.add(AuditLog(
            job_id=job.id,
            action="job_deleted",
            details={
                "hard_delete_transcript": True,
                "job_hard_deleted": False,
            },
        ))

    await db.commit()
    return True


async def get_transcript(
    db: AsyncSession, job_id: uuid.UUID
) -> tuple[TranscriptDocument | None, list[TranscriptSegment]]:
    doc_result = await db.execute(
        select(TranscriptDocument).where(TranscriptDocument.job_id == job_id)
    )
    doc = doc_result.scalar_one_or_none()

    segs_result = await db.execute(
        select(TranscriptSegment)
        .where(TranscriptSegment.job_id == job_id)
        .order_by(TranscriptSegment.sequence_number)
    )
    segments = list(segs_result.scalars().all())
    return doc, segments
