from __future__ import annotations
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.models.transcription_job import JobStatus, ProcessingStrategy


class CreateTranscriptionRequest(BaseModel):
    url: str = Field(..., min_length=10, max_length=2048, description="Video URL to transcribe")

    @field_validator("url")
    @classmethod
    def url_must_have_scheme(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class CreateTranscriptionResponse(BaseModel):
    job_id: uuid.UUID
    status: JobStatus


class TranscriptionJobResponse(BaseModel):
    job_id: uuid.UUID
    source_url: str
    source_type: str
    source_domain: str | None
    title: str | None
    duration_seconds: int | None
    language: str | None
    status: JobStatus
    processing_strategy: ProcessingStrategy
    error_message: str | None
    media_stored: bool
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class TranscriptionJobListResponse(BaseModel):
    jobs: list[TranscriptionJobResponse]
    total: int
