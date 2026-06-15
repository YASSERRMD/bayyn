from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

LOW_CONFIDENCE_THRESHOLD = 0.6


class TranscriptSegmentResponse(BaseModel):
    sequence_number: int
    start: float
    end: float
    text: str
    confidence: Optional[float] = None
    speaker_label: Optional[str] = None
    low_confidence: bool = False
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PatchSegmentRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4096)


class TranscriptResponse(BaseModel):
    job_id: uuid.UUID
    full_text: str
    word_count: int
    segment_count: int
    average_confidence: Optional[float] = None
    low_confidence_count: int = 0
    has_low_confidence_segments: bool = False
    accuracy_disclaimer: Optional[str] = None
    segments: list[TranscriptSegmentResponse]
    created_at: datetime

    model_config = {"from_attributes": True}
