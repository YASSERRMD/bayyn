"""POST /api/transcriptions/{job_id}/summary — optional LLM-generated summary."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import OptionalUser
from app.database import get_session
from app.schemas.summary import SummaryResponse
from app.services.llm_summary import LLMDisabledError, LLMSummaryError, _MAX_INPUT_CHARS, generate_summary
from app.services.transcription_service import get_job, get_transcript

router = APIRouter(prefix="/transcriptions", tags=["summaries"])


@router.post("/{job_id}/summary", response_model=SummaryResponse)
async def create_summary(
    job_id: str,
    current_user: OptionalUser,
    db: AsyncSession = Depends(get_session),
):
    try:
        uid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Transcription job not found.")

    requester_id = current_user.id if current_user else None
    job = await get_job(db, uid, requester_id=requester_id)
    if not job:
        raise HTTPException(status_code=404, detail="Transcription job not found.")

    doc, _ = await get_transcript(db, uid)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not available yet.",
        )

    try:
        summary = await generate_summary(doc.full_text)
    except LLMDisabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except LLMSummaryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    return SummaryResponse(
        job_id=job_id,
        summary=summary,
        model="gpt-4o-mini",
        truncated=len(doc.full_text) > _MAX_INPUT_CHARS,
    )
