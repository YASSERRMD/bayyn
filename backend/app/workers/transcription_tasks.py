import logging
import uuid
from datetime import datetime, timezone

from celery import Task
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models.audit_log import AuditLog
from app.models.transcript_document import TranscriptDocument
from app.models.transcript_segment import TranscriptSegment
from app.models.transcription_job import JobStatus, ProcessingStrategy, TranscriptionJob
from app.temp_manager import TempManager
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF_BASE_SECONDS = 60

sync_engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
SyncSession = sessionmaker(sync_engine)


def _get_session() -> Session:
    return SyncSession()


def _soft_timeout_exc():
    try:
        from celery.exceptions import SoftTimeLimitExceeded
        return SoftTimeLimitExceeded
    except ImportError:
        return type("_NeverRaised", (BaseException,), {})


def _fail_job(job_uuid: uuid.UUID, message: str, action: str = "job_failed") -> None:
    is_dead_letter = action == "job_dead_letter"
    with _get_session() as db:
        job = db.query(TranscriptionJob).filter(TranscriptionJob.id == job_uuid).first()
        if job:
            job.status = JobStatus.failed
            job.error_message = message
            job.completed_at = datetime.now(timezone.utc)
            if is_dead_letter:
                job.is_dead_letter = True
                logger.error(
                    "DEAD_LETTER job=%s retry_count=%d error=%s",
                    job_uuid, job.retry_count, message,
                )
            db.add(AuditLog(job_id=job_uuid, action=action, details={"error": message}))
            db.commit()


@celery_app.task(
    bind=True,
    name="app.workers.transcription_tasks.process_transcription_job",
    max_retries=MAX_RETRIES,
)
def process_transcription_job(self: Task, job_id: str) -> dict:
    job_uuid = uuid.UUID(job_id)
    attempt = self.request.retries  # 0 on first run, +1 on each retry
    logger.info("Starting transcription job=%s attempt=%d", job_id, attempt)

    with _get_session() as db:
        job = db.query(TranscriptionJob).filter(TranscriptionJob.id == job_uuid).first()
        if not job:
            logger.error("Job not found: %s", job_id)
            return {"status": "error", "message": "job not found"}

        job.status = JobStatus.processing
        job.started_at = datetime.now(timezone.utc)
        job.retry_count = attempt
        db.commit()

    temp_dir = TempManager.create_job_dir(job_uuid)

    try:
        _run_transcription(job_uuid, temp_dir)
        TempManager.cleanup_job_dir(job_uuid, reason="completed")
        return {"status": "completed", "job_id": job_id}

    except Exception as exc:
        TempManager.cleanup_job_dir(job_uuid, reason="failure")

        SoftExc = _soft_timeout_exc()
        if isinstance(exc, SoftExc):
            timeout_msg = "Processing timed out. The video may be too long to transcribe."
            logger.warning("Soft timeout reached job=%s", job_id)
            _fail_job(job_uuid, timeout_msg, action="job_timeout")
            return {"status": "timeout", "job_id": job_id}

        safe_message = _sanitize_error(str(exc))

        if attempt < MAX_RETRIES:
            backoff = _exponential_backoff(attempt)
            logger.warning(
                "Retrying job=%s attempt=%d/%d backoff=%ds error=%s",
                job_id, attempt + 1, MAX_RETRIES, backoff, safe_message,
            )
            _log_retry_audit(job_uuid, attempt + 1, safe_message)
            raise self.retry(exc=exc, countdown=backoff)

        # All retries exhausted → dead-letter
        logger.error("Dead-letter job=%s all %d retries exhausted", job_id, MAX_RETRIES)
        _fail_job(job_uuid, safe_message, action="job_dead_letter")
        return {"status": "failed", "job_id": job_id}


def _exponential_backoff(attempt: int) -> int:
    """Return backoff seconds: 60, 120, 240 for attempts 0, 1, 2."""
    return RETRY_BACKOFF_BASE_SECONDS * (2 ** attempt)


def _log_retry_audit(job_uuid: uuid.UUID, attempt: int, error: str) -> None:
    with _get_session() as db:
        db.add(AuditLog(
            job_id=job_uuid,
            action="job_retry",
            details={"attempt": attempt, "error": error},
        ))
        db.commit()


def _run_transcription(job_uuid: uuid.UUID, temp_dir) -> None:
    from app.source_adapters.youtube import YouTubeSourceAdapter

    with _get_session() as db:
        job = db.query(TranscriptionJob).filter(TranscriptionJob.id == job_uuid).first()
        url = job.source_url

    adapter = YouTubeSourceAdapter(url)
    metadata = adapter.get_metadata()

    with _get_session() as db:
        job = db.query(TranscriptionJob).filter(TranscriptionJob.id == job_uuid).first()
        job.title = metadata.get("title")
        job.duration_seconds = metadata.get("duration")
        job.language = metadata.get("language", settings.default_language)
        db.commit()

    captions = adapter.get_captions()

    if captions:
        logger.info("Caption strategy for job=%s segments=%d", job_uuid, len(captions))
        segments_data = captions
        strategy = ProcessingStrategy.caption
        detected_language = adapter.get_caption_language()
    else:
        logger.info("Whisper strategy for job=%s", job_uuid)
        from app.transcription.whisper_processor import transcribe_audio
        audio_stream_url = adapter.get_audio_stream_url()
        segments_data, detected_language = transcribe_audio(audio_stream_url, temp_dir, job_uuid)
        strategy = ProcessingStrategy.whisper

    _update_job_language(job_uuid, detected_language)
    _store_transcript(job_uuid, segments_data, strategy)


def _update_job_language(job_uuid: uuid.UUID, detected_language: str) -> None:
    from app.transcription.language_detector import DEFAULT_LANGUAGE
    language = detected_language or DEFAULT_LANGUAGE
    with _get_session() as db:
        job = db.query(TranscriptionJob).filter(TranscriptionJob.id == job_uuid).first()
        if job:
            job.language = language
            db.commit()
    logger.info("Updated job=%s detected_language=%s", job_uuid, language)


def _store_transcript(
    job_uuid: uuid.UUID,
    segments: list[dict],
    strategy: ProcessingStrategy,
) -> None:
    from app.transcription.caption_processor import normalize_segments
    from app.transcription.text_cleaner import apply_text_cleanup

    normalized = apply_text_cleanup(normalize_segments(segments))
    full_text = " ".join(s["text"].strip() for s in normalized)
    word_count = len(full_text.split())

    low_confidence_threshold = 0.6
    confident_values = [
        float(s["confidence"]) for s in normalized if s.get("confidence") is not None
    ]
    average_confidence = (
        sum(confident_values) / len(confident_values) if confident_values else None
    )
    low_confidence_count = sum(
        1 for v in confident_values if v < low_confidence_threshold
    )

    with _get_session() as db:
        doc = TranscriptDocument(
            id=uuid.uuid4(),
            job_id=job_uuid,
            full_text=full_text,
            word_count=word_count,
            segment_count=len(normalized),
            average_confidence=average_confidence,
            low_confidence_count=low_confidence_count,
        )
        db.add(doc)

        for i, seg in enumerate(normalized):
            db.add(TranscriptSegment(
                id=uuid.uuid4(),
                job_id=job_uuid,
                sequence_number=i + 1,
                start_seconds=seg["start"],
                end_seconds=seg["end"],
                text=seg["text"].strip(),
                confidence=seg.get("confidence"),
                speaker_label=seg.get("speaker"),
            ))

        job = db.query(TranscriptionJob).filter(TranscriptionJob.id == job_uuid).first()
        job.status = JobStatus.completed
        job.processing_strategy = strategy
        job.completed_at = datetime.now(timezone.utc)
        job.media_stored = False

        db.add(AuditLog(
            job_id=job_uuid,
            action="job_completed",
            details={
                "strategy": strategy.value,
                "segment_count": len(normalized),
                "word_count": word_count,
            },
        ))
        db.commit()


def _sanitize_error(message: str) -> str:
    import re
    message = re.sub(r"https?://\S+", "[URL_REDACTED]", message)
    message = re.sub(r"/tmp/\S+", "[PATH_REDACTED]", message)
    return message[:512]


@celery_app.task(name="app.workers.transcription_tasks.cleanup_stale_temp_dirs")
def cleanup_stale_temp_dirs() -> None:
    TempManager.startup_cleanup()
