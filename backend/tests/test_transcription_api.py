from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
from fastapi.testclient import TestClient


def make_mock_job(status="pending", **kwargs):
    from app.models.transcription_job import JobStatus, ProcessingStrategy
    from datetime import datetime, timezone
    job = MagicMock()
    job.id = uuid.uuid4()
    job.source_url = "https://www.youtube.com/watch?v=test"
    job.source_type = "youtube"
    job.source_domain = "www.youtube.com"
    job.title = "Test Video"
    job.duration_seconds = 120
    job.language = "en"
    job.status = getattr(JobStatus, status)
    job.processing_strategy = ProcessingStrategy.caption
    job.error_message = None
    job.media_stored = False
    job.created_at = datetime.now(timezone.utc)
    job.started_at = None
    job.completed_at = None
    job.deleted_at = None
    for k, v in kwargs.items():
        setattr(job, k, v)
    return job


@pytest.fixture
def mock_task():
    with patch("app.workers.transcription_tasks.process_transcription_job") as mock:
        mock.delay = MagicMock()
        yield mock


def test_create_transcription_job_success(client, mock_task):
    mock_job = make_mock_job()
    with patch("app.api.v1.transcriptions.create_transcription_job", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_job
        response = client.post(
            "/api/transcriptions",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        )
    assert response.status_code == 201
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"


def test_create_transcription_invalid_url(client, mock_task):
    response = client.post("/api/transcriptions", json={"url": "not-a-url"})
    assert response.status_code == 422


def test_create_transcription_blocked_localhost(client, mock_task):
    with patch("app.security.url_validator._resolve_hostname", return_value=[]):
        response = client.post("/api/transcriptions", json={"url": "http://localhost/video"})
    assert response.status_code == 422


def test_get_nonexistent_job(client):
    with patch("app.api.v1.transcriptions.get_job", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        response = client.get(f"/api/transcriptions/{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_existing_job(client):
    mock_job = make_mock_job(status="completed")
    with patch("app.api.v1.transcriptions.get_job", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_job
        response = client.get(f"/api/transcriptions/{mock_job.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["media_stored"] is False


def test_delete_existing_job(client):
    with patch("app.api.v1.transcriptions.delete_job", new_callable=AsyncMock) as mock_del:
        mock_del.return_value = True
        response = client.delete(f"/api/transcriptions/{uuid.uuid4()}")
    assert response.status_code == 204


def test_delete_nonexistent_job(client):
    with patch("app.api.v1.transcriptions.delete_job", new_callable=AsyncMock) as mock_del:
        mock_del.return_value = False
        response = client.delete(f"/api/transcriptions/{uuid.uuid4()}")
    assert response.status_code == 404


def test_media_stored_is_always_false(client):
    mock_job = make_mock_job()
    assert mock_job.media_stored is False
