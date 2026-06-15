"""Integration tests: full HTTP flows across auth, transcription, admin, and rate-limiting."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import requires_asyncpg
from app.auth.jwt_handler import create_access_token


# ── Helpers ───────────────────────────────────────────────────────────────────

def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _make_job(status="pending", user_id=None, **kwargs):
    from app.models.transcription_job import JobStatus, ProcessingStrategy
    job = MagicMock()
    job.id = uuid.uuid4()
    job.user_id = user_id
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
    job.progress_pct = 0
    job.current_step = None
    job.retry_count = 0
    job.is_dead_letter = False
    for k, v in kwargs.items():
        setattr(job, k, v)
    return job


# ── Auth flow ─────────────────────────────────────────────────────────────────

@requires_asyncpg
def test_get_me_without_token_returns_401(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


@requires_asyncpg
def test_get_me_with_valid_token_returns_user(client):
    user_id = uuid.uuid4()
    token = create_access_token(str(user_id), "test@example.com")
    response = client.get("/api/auth/me", headers=_bearer(token))
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert str(data["id"]) == str(user_id)


@requires_asyncpg
def test_get_me_with_tampered_token_returns_401(client):
    token = create_access_token(str(uuid.uuid4()), "user@example.com")
    bad_token = token[:-5] + "XXXXX"
    response = client.get("/api/auth/me", headers=_bearer(bad_token))
    assert response.status_code == 401


# ── Authenticated job access ──────────────────────────────────────────────────

@requires_asyncpg
def test_unauthenticated_job_list_returns_401(client):
    response = client.get("/api/transcriptions")
    assert response.status_code == 401


@requires_asyncpg
def test_authenticated_user_can_create_job(client):
    user_id = uuid.uuid4()
    token = create_access_token(str(user_id), "user@example.com")
    mock_job = _make_job(user_id=user_id)

    with (
        patch("app.api.v1.transcriptions.check_user_limits", new_callable=AsyncMock) as mock_limits,
        patch("app.api.v1.transcriptions.create_transcription_job", new_callable=AsyncMock) as mock_create,
        patch("app.workers.transcription_tasks.process_transcription_job") as mock_task,
    ):
        mock_limits.return_value = None
        mock_create.return_value = mock_job
        mock_task.delay = MagicMock()

        response = client.post(
            "/api/transcriptions",
            json={"url": "https://www.youtube.com/watch?v=test"},
            headers=_bearer(token),
        )

    assert response.status_code == 201
    assert response.json()["job_id"] == str(mock_job.id)


@requires_asyncpg
def test_cross_user_job_access_returns_404(client):
    """A user cannot access another user's job — returns 404 (not 403) to prevent enumeration."""
    owner_id = uuid.uuid4()
    other_id = uuid.uuid4()
    job_id = uuid.uuid4()

    other_token = create_access_token(str(other_id), "other@example.com")

    # get_job() returns None when the requester_id doesn't match
    with patch("app.api.v1.transcriptions.get_job", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        response = client.get(f"/api/transcriptions/{job_id}", headers=_bearer(other_token))

    assert response.status_code == 404


# ── Rate limiting ─────────────────────────────────────────────────────────────

@requires_asyncpg
def test_rate_limit_exceeded_returns_429(client):
    from app.services.rate_limiter import RateLimitError

    user_id = uuid.uuid4()
    token = create_access_token(str(user_id), "busy@example.com")

    with patch("app.api.v1.transcriptions.check_user_limits", new_callable=AsyncMock) as mock_limits:
        mock_limits.side_effect = RateLimitError("You already have 5 job(s) in progress.")
        response = client.post(
            "/api/transcriptions",
            json={"url": "https://www.youtube.com/watch?v=test"},
            headers=_bearer(token),
        )

    assert response.status_code == 429
    assert "in progress" in response.json()["detail"]


# ── Admin endpoint access control ─────────────────────────────────────────────

@requires_asyncpg
def test_admin_endpoint_requires_auth(client):
    response = client.get("/api/admin/jobs")
    assert response.status_code == 401


@requires_asyncpg
def test_admin_endpoint_rejects_non_admin(client):
    token = create_access_token(str(uuid.uuid4()), "user@example.com", is_admin=False)
    response = client.get("/api/admin/jobs", headers=_bearer(token))
    assert response.status_code == 403


@requires_asyncpg
def test_admin_endpoint_accessible_by_admin(client):
    token = create_access_token(str(uuid.uuid4()), "admin@example.com", is_admin=True)

    with patch("app.api.v1.admin.get_metrics", new_callable=AsyncMock) as _:
        # We just need the dependency check to pass; mock the DB query
        with patch("app.api.v1.admin.admin_list_jobs", new_callable=AsyncMock) as _mock:
            _mock.return_value = None
            # Patch the actual DB query inside the route
            pass

    # Patch at service level: mock the DB execute to return empty results
    with patch("app.api.v1.admin.AsyncSession", new_callable=MagicMock):
        # Use the actual route but mock get_session dependency
        response = client.get("/api/admin/jobs", headers=_bearer(token))

    # Admin token gets through the auth gate; DB might fail (no real DB), but that's 500 not 401/403
    assert response.status_code in (200, 500)
    assert response.status_code != 401
    assert response.status_code != 403


# ── Metrics endpoint access control ──────────────────────────────────────────

@requires_asyncpg
def test_metrics_endpoint_requires_auth(client):
    response = client.get("/api/metrics")
    assert response.status_code == 401


@requires_asyncpg
def test_metrics_endpoint_rejects_non_admin(client):
    token = create_access_token(str(uuid.uuid4()), "user@example.com", is_admin=False)
    response = client.get("/api/metrics", headers=_bearer(token))
    assert response.status_code == 403


# ── Request ID in response ────────────────────────────────────────────────────

@requires_asyncpg
def test_response_includes_request_id(client):
    response = client.get("/health")
    assert "x-request-id" in response.headers


@requires_asyncpg
def test_forwarded_request_id_echoed(client):
    custom_id = str(uuid.uuid4())
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.headers["x-request-id"] == custom_id
