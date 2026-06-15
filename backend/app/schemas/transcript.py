from __future__ import annotations
import uuid
from datetime import datetime

from pydantic import BaseModel


class TranscriptSegmentResponse(BaseModel):
    sequence_number: int
    start: float
    end: float
    text: str
    confidence: float | None = None
    speaker_label: str | None = None

    model_config = {"from_attributes": True}


class TranscriptResponse(BaseModel):
    job_id: uuid.UUID
    full_text: str
    word_count: int
    segment_count: int
    segments: list[TranscriptSegmentResponse]
    created_at: datetime

    model_config = {"from_attributes": True}
