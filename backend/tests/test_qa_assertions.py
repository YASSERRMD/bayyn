"""Phase 40: QA assertions — cross-cutting invariant checks across all phases."""
import inspect
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.conftest import requires_asyncpg


# ── API route registration ────────────────────────────────────────────────────

@requires_asyncpg
def test_all_expected_routes_registered(client):
    routes = {r.path for r in client.app.routes}

    expected = {
        "/health",
        "/health/detailed",
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/me",
        "/api/transcriptions",
        "/api/transcriptions/{job_id}",
        "/api/transcriptions/{job_id}/transcript",
        "/api/transcriptions/{job_id}/summary",
        "/api/admin/jobs",
        "/api/admin/jobs/{job_id}",
        "/api/metrics",
    }

    for path in expected:
        assert path in routes, f"Route missing: {path}"


@requires_asyncpg
def test_docs_hidden_in_production(client):
    """Swagger UI must not be accessible at /docs in production mode."""
    from app.config import settings
    if settings.is_production:
        response = client.get("/docs")
        assert response.status_code == 404


# ── Security invariants ───────────────────────────────────────────────────────

def test_jwt_uses_hs256_not_none_algorithm():
    from app.auth import jwt_handler
    source = inspect.getsource(jwt_handler)
    assert "HS256" in source
    assert '"none"' not in source.lower() and "'none'" not in source.lower()


def test_password_module_uses_pbkdf2():
    from app.auth import password as pw_module
    source = inspect.getsource(pw_module)
    assert "pbkdf2" in source.lower()
    assert "compare_digest" in source


def test_error_mapper_never_exposes_raw_exc():
    from app.errors.error_mapper import classify_error
    dangerous_messages = [
        "db.internal connection refused",
        "/tmp/bayyn/job-id/audio.wav",
        "SELECT * FROM users",
    ]
    for msg in dangerous_messages:
        result = classify_error(RuntimeError(msg))
        for dangerous in ["db.internal", "/tmp/bayyn", "SELECT"]:
            assert dangerous not in result, f"classify_error leaked '{dangerous}' from: {msg!r}"


def test_temp_manager_cleanup_is_recursive(tmp_path):
    from app.temp_manager import TempManager
    job_id = uuid.uuid4()
    with patch.object(TempManager, "_base_dir", return_value=tmp_path):
        job_dir = TempManager.create_job_dir(job_id)
        deep = job_dir / "a" / "b" / "c"
        deep.mkdir(parents=True)
        (deep / "file.bin").write_bytes(b"data")
        TempManager.cleanup_job_dir(job_id)
    assert not job_dir.exists()


def test_media_stored_invariant_in_worker_source():
    from app.workers import transcription_tasks
    source = inspect.getsource(transcription_tasks)
    assert "media_stored = True" not in source
    assert "media_stored=True" not in source


def test_media_stored_set_false_in_store_transcript():
    from app.workers import transcription_tasks
    source = inspect.getsource(transcription_tasks._store_transcript)
    assert "media_stored" in source
    assert "media_stored = False" in source or "media_stored=False" in source


# ── Configuration guards ──────────────────────────────────────────────────────

def test_insecure_secret_rejected_in_production():
    from app.config import Settings, _INSECURE_SECRET
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            secret_key=_INSECURE_SECRET,
            database_url="postgresql+asyncpg://u:p@prod:5432/db",
        )


def test_localhost_db_rejected_in_production():
    from app.config import Settings
    from pydantic import ValidationError
    with pytest.raises(ValidationError, match="production database"):
        Settings(
            app_env="production",
            secret_key="x" * 32,
            database_url="postgresql+asyncpg://u:p@localhost:5432/db",
        )


def test_development_mode_has_no_restrictions():
    from app.config import Settings, _INSECURE_SECRET
    s = Settings(
        app_env="development",
        secret_key=_INSECURE_SECRET,
        database_url="postgresql+asyncpg://bayyn:bayyn@localhost:5432/bayyn",
    )
    assert s.is_production is False


# ── Rate limiter checks ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_user_limits_skips_anonymous():
    from app.services.rate_limiter import check_user_limits
    # Should not raise for anonymous (None user_id)
    with patch("app.services.rate_limiter._count_active_jobs") as _:
        await check_user_limits(db=None, user_id=None)  # must return without calling DB


# ── LLM summary plugin guards ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_llm_summary_disabled_by_default():
    from app.services.llm_summary import LLMDisabledError, generate_summary
    from app.config import settings
    if not settings.enable_llm_summary:
        with pytest.raises(LLMDisabledError):
            await generate_summary("some text")


def test_llm_summary_is_enabled_respects_both_flags():
    from app.services.llm_summary import is_enabled
    with patch("app.services.llm_summary.settings") as m:
        m.enable_llm_summary = True
        m.openai_api_key = ""
        assert not is_enabled()
        m.openai_api_key = "sk-key"
        assert is_enabled()


# ── Request ID middleware ─────────────────────────────────────────────────────

@requires_asyncpg
def test_request_id_echoed_on_every_response(client):
    for path in ["/health", "/api/auth/me"]:
        response = client.get(path)
        assert "x-request-id" in response.headers, f"Missing X-Request-ID on {path}"


@requires_asyncpg
def test_forwarded_request_id_preserved(client):
    rid = str(uuid.uuid4())
    response = client.get("/health", headers={"X-Request-ID": rid})
    assert response.headers["x-request-id"] == rid


# ── Schema model constraints ──────────────────────────────────────────────────

def test_segment_patch_rejects_empty_text():
    from app.schemas.transcript import PatchSegmentRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        PatchSegmentRequest(text="")


def test_segment_patch_rejects_oversized_text():
    from app.schemas.transcript import PatchSegmentRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        PatchSegmentRequest(text="x" * 4097)


def test_summary_response_schema_fields():
    from app.schemas.summary import SummaryResponse
    s = SummaryResponse(job_id="abc", summary="text", model="gpt-4o-mini", truncated=False)
    assert s.job_id == "abc"
    assert s.truncated is False
