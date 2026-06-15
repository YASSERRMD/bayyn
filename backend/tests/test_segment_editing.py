"""Tests for segment editing: schema validation and PATCH endpoint (requires asyncpg)."""
import importlib
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

requires_asyncpg = pytest.mark.skipif(
    importlib.util.find_spec("asyncpg") is None,
    reason="asyncpg not installed; API tests run in Docker",
)


def make_mock_job(job_id=None):
    from app.models.transcription_job import JobStatus, ProcessingStrategy
    job = MagicMock()
    job.id = job_id or uuid.uuid4()
    job.source_url = "https://www.youtube.com/watch?v=test"
    job.source_type = "youtube"
    job.source_domain = "youtube.com"
    job.title = "Test"
    job.duration_seconds = 60
    job.language = "en"
    job.status = JobStatus.completed
    job.processing_strategy = ProcessingStrategy.caption
    job.error_message = None
    job.media_stored = False
    job.progress_pct = 100
    job.current_step = "completed"
    job.retry_count = 0
    job.is_dead_letter = False
    job.created_at = datetime.now(timezone.utc)
    job.started_at = None
    job.completed_at = None
    return job


def make_mock_segment(seq=1, text="Hello world", job_id=None):
    seg = MagicMock()
    seg.id = uuid.uuid4()
    seg.job_id = job_id or uuid.uuid4()
    seg.sequence_number = seq
    seg.start_seconds = 0.0
    seg.end_seconds = 5.0
    seg.text = text
    seg.confidence = None
    seg.speaker_label = None
    seg.created_at = datetime.now(timezone.utc)
    seg.updated_at = None
    return seg


# ── Schema validation (no asyncpg needed) ─────────────────────────────────────

def test_patch_segment_request_accepts_valid_text():
    from app.schemas.transcript import PatchSegmentRequest
    req = PatchSegmentRequest(text="Valid text here.")
    assert req.text == "Valid text here."


def test_patch_segment_request_rejects_empty_text():
    from app.schemas.transcript import PatchSegmentRequest
    import pydantic
    with pytest.raises(pydantic.ValidationError):
        PatchSegmentRequest(text="")


def test_patch_segment_request_rejects_missing_field():
    from app.schemas.transcript import PatchSegmentRequest
    import pydantic
    with pytest.raises(pydantic.ValidationError):
        PatchSegmentRequest()  # type: ignore[call-arg]


def test_segment_response_updated_at_defaults_none():
    from app.schemas.transcript import TranscriptSegmentResponse
    resp = TranscriptSegmentResponse(
        sequence_number=1, start=0.0, end=5.0, text="Hello"
    )
    assert resp.updated_at is None


def test_segment_response_updated_at_accepts_datetime():
    from app.schemas.transcript import TranscriptSegmentResponse
    now = datetime.now(timezone.utc)
    resp = TranscriptSegmentResponse(
        sequence_number=2, start=5.0, end=10.0, text="World", updated_at=now
    )
    assert resp.updated_at == now


def test_segment_response_preserves_timestamps():
    from app.schemas.transcript import TranscriptSegmentResponse
    resp = TranscriptSegmentResponse(
        sequence_number=3, start=12.5, end=20.0, text="Test"
    )
    assert resp.start == 12.5
    assert resp.end == 20.0


# ── API endpoint tests (require asyncpg / run in Docker) ──────────────────────

@requires_asyncpg
def test_patch_segment_job_not_found_returns_404(client):
    job_id = uuid.uuid4()
    with patch("app.api.v1.transcriptions.get_job", new_callable=AsyncMock, return_value=None):
        resp = client.patch(
            f"/api/transcriptions/{job_id}/segments/1",
            json={"text": "New text"},
        )
    assert resp.status_code == 404


@requires_asyncpg
def test_patch_segment_whitespace_text_returns_422(client):
    job_id = uuid.uuid4()
    mock_job = make_mock_job(job_id=job_id)
    mock_seg = make_mock_segment(seq=1, job_id=job_id)

    async def _override_db():
        from sqlalchemy.ext.asyncio import AsyncSession
        db = AsyncMock(spec=AsyncSession)
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = mock_seg
        db.execute = AsyncMock(return_value=execute_result)
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        yield db

    from app.database import get_session
    from app.main import app
    from fastapi.testclient import TestClient

    with patch("app.api.v1.transcriptions.get_job", new_callable=AsyncMock, return_value=mock_job):
        app.dependency_overrides[get_session] = _override_db
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.patch(
            f"/api/transcriptions/{job_id}/segments/1",
            json={"text": "   "},
        )
        app.dependency_overrides.clear()

    assert resp.status_code == 422
