from __future__ import annotations
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit_log import AuditLog
from app.models.transcript_document import TranscriptDocument
from app.models.transcript_segment import TranscriptSegment
from app.models.transcription_job import JobStatus, ProcessingStrategy, TranscriptionJob
from app.security.url_validator import URLValidationError, validate_url


async def create_transcription_job(
    db: AsyncSession,
    url: str,
) -> TranscriptionJob:
    source_type, source_domain = validate_url(url)

    job = TranscriptionJob(
        id=uuid.uuid4(),
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


async def get_job(db: AsyncSession, job_id: uuid.UUID) -> TranscriptionJob | None:
    result = await db.execute(
        select(TranscriptionJob).where(
            TranscriptionJob.id == job_id,
            TranscriptionJob.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def list_jobs(
    db: AsyncSession, offset: int = 0, limit: int = 50
) -> tuple[list[TranscriptionJob], int]:
    count_result = await db.execute(
        select(func.count(TranscriptionJob.id)).where(
            TranscriptionJob.deleted_at.is_(None)
        )
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(TranscriptionJob)
        .where(TranscriptionJob.deleted_at.is_(None))
        .order_by(TranscriptionJob.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def delete_job(db: AsyncSession, job_id: uuid.UUID) -> bool:
    job = await get_job(db, job_id)
    if not job:
        return False

    result = await db.execute(
        select(TranscriptDocument).where(TranscriptDocument.job_id == job_id)
    )
    doc = result.scalar_one_or_none()
    if doc:
        await db.delete(doc)

    await db.execute(
        select(TranscriptSegment).where(TranscriptSegment.job_id == job_id)
    )
    segs_result = await db.execute(
        select(TranscriptSegment).where(TranscriptSegment.job_id == job_id)
    )
    for seg in segs_result.scalars().all():
        await db.delete(seg)

    job.deleted_at = datetime.now(timezone.utc)
    db.add(job)

    audit = AuditLog(
        job_id=job.id,
        action="job_deleted",
        details={"hard_delete_transcript": True},
    )
    db.add(audit)
    await db.commit()
    return True


async def get_transcript(db: AsyncSession, job_id: uuid.UUID) -> tuple[TranscriptDocument | None, list[TranscriptSegment]]:
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
