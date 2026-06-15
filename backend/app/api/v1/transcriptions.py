import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.main import limiter
from app.config import settings
from app.schemas.transcript import LOW_CONFIDENCE_THRESHOLD, PatchSegmentRequest, TranscriptResponse, TranscriptSegmentResponse
from app.schemas.transcription import (
    CreateTranscriptionRequest,
    CreateTranscriptionResponse,
    TranscriptionJobListResponse,
    TranscriptionJobResponse,
)
from app.security.url_validator import URLValidationError
from app.services.transcription_service import (
    create_transcription_job,
    delete_job,
    get_job,
    get_transcript,
    list_jobs,
)

router = APIRouter(prefix="/transcriptions", tags=["transcriptions"])

DbSession = Annotated[AsyncSession, Depends(get_session)]


@router.post("", response_model=CreateTranscriptionResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def create_transcription(
    request: Request,
    body: CreateTranscriptionRequest,
    db: DbSession,
) -> CreateTranscriptionResponse:
    try:
        job = await create_transcription_job(db, body.url)
    except URLValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    from app.workers.transcription_tasks import process_transcription_job
    process_transcription_job.delay(str(job.id))

    return CreateTranscriptionResponse(job_id=job.id, status=job.status)


@router.get("", response_model=TranscriptionJobListResponse)
async def list_transcriptions(
    db: DbSession,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> TranscriptionJobListResponse:
    jobs, total = await list_jobs(db, offset=offset, limit=limit)
    return TranscriptionJobListResponse(
        jobs=[_job_to_response(j) for j in jobs],
        total=total,
    )


@router.get("/{job_id}", response_model=TranscriptionJobResponse)
async def get_transcription(job_id: uuid.UUID, db: DbSession) -> TranscriptionJobResponse:
    job = await get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Transcription job not found.")
    return _job_to_response(job)


@router.get("/{job_id}/transcript", response_model=TranscriptResponse)
async def get_transcript_endpoint(job_id: uuid.UUID, db: DbSession) -> TranscriptResponse:
    job = await get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Transcription job not found.")

    doc, segments = await get_transcript(db, job_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Transcript not yet available.")

    avg_conf = float(doc.average_confidence) if doc.average_confidence is not None else None
    low_count = doc.low_confidence_count or 0
    has_low = low_count > 0

    disclaimer = None
    if has_low:
        disclaimer = (
            "This transcript contains segments with low confidence scores. "
            "Some words may be inaccurate. Please review carefully."
        )
    elif avg_conf is None:
        disclaimer = (
            "Transcript accuracy may vary. No confidence data is available for this source."
        )

    return TranscriptResponse(
        job_id=job_id,
        full_text=doc.full_text,
        word_count=doc.word_count,
        segment_count=doc.segment_count,
        average_confidence=avg_conf,
        low_confidence_count=low_count,
        has_low_confidence_segments=has_low,
        accuracy_disclaimer=disclaimer,
        segments=[_seg_to_response(s) for s in segments],
        created_at=doc.created_at,
    )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transcription(
    job_id: uuid.UUID,
    db: DbSession,
    hard_delete: bool = Query(False, description="Permanently delete the job record (default: soft-delete)"),
) -> None:
    deleted = await delete_job(db, job_id, hard_delete=hard_delete)
    if not deleted:
        raise HTTPException(status_code=404, detail="Transcription job not found.")


@router.get("/{job_id}/export/txt")
async def export_txt(
    job_id: uuid.UUID,
    db: DbSession,
    timestamps: bool = Query(False, description="Prefix each segment with [HH:MM:SS]"),
) -> StreamingResponse:
    doc, segments = await _get_doc_or_404(job_id, db)
    from app.exports.txt_export import generate_txt
    content = generate_txt(doc, include_timestamps=timestamps, segments=segments).encode("utf-8")
    return StreamingResponse(
        iter([content]),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="transcript-{job_id}.txt"'},
    )


@router.get("/{job_id}/export/srt")
async def export_srt(job_id: uuid.UUID, db: DbSession) -> StreamingResponse:
    _, segments = await _get_doc_or_404(job_id, db)
    from app.exports.srt_export import generate_srt
    srt_content = generate_srt(segments).encode("utf-8")
    return StreamingResponse(
        iter([srt_content]),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="transcript-{job_id}.srt"'},
    )


@router.get("/{job_id}/export/docx")
async def export_docx(job_id: uuid.UUID, db: DbSession) -> StreamingResponse:
    doc, segments = await _get_doc_or_404(job_id, db)
    job = await get_job(db, job_id)
    from app.exports.docx_export import generate_docx
    docx_bytes = generate_docx(job, doc, segments)
    return StreamingResponse(
        iter([docx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="transcript-{job_id}.docx"'},
    )


@router.patch(
    "/{job_id}/segments/{sequence_number}",
    response_model=TranscriptSegmentResponse,
)
async def patch_segment(
    job_id: uuid.UUID,
    sequence_number: int,
    body: PatchSegmentRequest,
    db: DbSession,
) -> TranscriptSegmentResponse:
    from datetime import datetime, timezone
    from app.models.audit_log import AuditLog
    from app.models.transcript_segment import TranscriptSegment

    job = await get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Transcription job not found.")

    from sqlalchemy import select
    result = await db.execute(
        select(TranscriptSegment).where(
            TranscriptSegment.job_id == job_id,
            TranscriptSegment.sequence_number == sequence_number,
        )
    )
    seg = result.scalar_one_or_none()
    if not seg:
        raise HTTPException(status_code=404, detail="Segment not found.")

    old_text = seg.text
    new_text = body.text.strip()
    if not new_text:
        raise HTTPException(status_code=422, detail="Segment text must not be empty.")

    seg.text = new_text
    seg.updated_at = datetime.now(timezone.utc)
    db.add(AuditLog(
        job_id=job_id,
        action="segment_edited",
        details={
            "sequence_number": sequence_number,
            "old_text": old_text,
            "new_text": new_text,
        },
    ))
    await db.commit()
    await db.refresh(seg)
    return _seg_to_response(seg)


async def _get_doc_or_404(job_id, db):
    doc, segments = await get_transcript(db, job_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Transcript not available.")
    return doc, segments


def _seg_to_response(s) -> TranscriptSegmentResponse:
    return TranscriptSegmentResponse(
        sequence_number=s.sequence_number,
        start=float(s.start_seconds),
        end=float(s.end_seconds),
        text=s.text,
        confidence=float(s.confidence) if s.confidence is not None else None,
        speaker_label=s.speaker_label,
        low_confidence=(
            float(s.confidence) < LOW_CONFIDENCE_THRESHOLD
            if s.confidence is not None
            else False
        ),
        updated_at=s.updated_at,
    )


def _job_to_response(job) -> TranscriptionJobResponse:
    return TranscriptionJobResponse(
        job_id=job.id,
        source_url=job.source_url,
        source_type=job.source_type,
        source_domain=job.source_domain,
        title=job.title,
        duration_seconds=job.duration_seconds,
        language=job.language,
        status=job.status,
        processing_strategy=job.processing_strategy,
        error_message=job.error_message,
        progress_pct=job.progress_pct or 0,
        current_step=job.current_step,
        retry_count=job.retry_count or 0,
        is_dead_letter=job.is_dead_letter or False,
        media_stored=job.media_stored,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )
