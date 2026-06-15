from __future__ import annotations

from pydantic import BaseModel


class SummaryResponse(BaseModel):
    job_id: str
    summary: str
    model: str
    truncated: bool
