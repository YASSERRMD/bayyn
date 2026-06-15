"""Phase 39: LLM summary plugin — service logic and endpoint behavior."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import requires_asyncpg


# ── Service unit tests ────────────────────────────────────────────────────────

class TestGenerateSummaryService:
    @pytest.mark.asyncio
    async def test_raises_disabled_when_flag_is_false(self):
        from app.services.llm_summary import LLMDisabledError, generate_summary
        with patch("app.services.llm_summary.settings") as mock_settings:
            mock_settings.enable_llm_summary = False
            mock_settings.openai_api_key = "sk-test"
            with pytest.raises(LLMDisabledError, match="not enabled"):
                await generate_summary("some transcript text")

    @pytest.mark.asyncio
    async def test_raises_error_when_no_api_key(self):
        from app.services.llm_summary import LLMSummaryError, generate_summary
        with patch("app.services.llm_summary.settings") as mock_settings:
            mock_settings.enable_llm_summary = True
            mock_settings.openai_api_key = ""
            with pytest.raises(LLMSummaryError, match="API key"):
                await generate_summary("some transcript text")

    @pytest.mark.asyncio
    async def test_raises_error_for_empty_transcript(self):
        from app.services.llm_summary import LLMSummaryError, generate_summary
        with patch("app.services.llm_summary.settings") as mock_settings:
            mock_settings.enable_llm_summary = True
            mock_settings.openai_api_key = "sk-test"
            with pytest.raises(LLMSummaryError, match="empty"):
                await generate_summary("")

    @pytest.mark.asyncio
    async def test_raises_error_for_whitespace_only_transcript(self):
        from app.services.llm_summary import LLMSummaryError, generate_summary
        with patch("app.services.llm_summary.settings") as mock_settings:
            mock_settings.enable_llm_summary = True
            mock_settings.openai_api_key = "sk-test"
            with pytest.raises(LLMSummaryError, match="empty"):
                await generate_summary("   \n  ")

    @pytest.mark.asyncio
    async def test_successful_summary_returned(self):
        from app.services.llm_summary import generate_summary
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "  This is a summary.  "}}]
        }
        mock_response.raise_for_status = MagicMock()

        with (
            patch("app.services.llm_summary.settings") as mock_settings,
            patch("httpx.AsyncClient") as mock_client_cls,
        ):
            mock_settings.enable_llm_summary = True
            mock_settings.openai_api_key = "sk-test"
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await generate_summary("Hello world. This is a transcript.")

        assert result == "This is a summary."

    @pytest.mark.asyncio
    async def test_long_transcript_is_truncated(self):
        from app.services.llm_summary import _MAX_INPUT_CHARS, generate_summary
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Summary here."}}]
        }
        mock_response.raise_for_status = MagicMock()

        captured_body = {}

        async def capture_post(url, **kwargs):
            captured_body.update(kwargs)
            return mock_response

        with (
            patch("app.services.llm_summary.settings") as mock_settings,
            patch("httpx.AsyncClient") as mock_client_cls,
        ):
            mock_settings.enable_llm_summary = True
            mock_settings.openai_api_key = "sk-test"
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=capture_post)
            mock_client_cls.return_value = mock_client

            long_text = "word " * 5000  # ~25k chars, well over _MAX_INPUT_CHARS
            await generate_summary(long_text)

        sent_text = captured_body["json"]["messages"][1]["content"]
        assert len(sent_text) <= _MAX_INPUT_CHARS + 100  # +100 for the "[truncated]" suffix
        assert "truncated" in sent_text.lower()

    @pytest.mark.asyncio
    async def test_401_from_openai_raises_api_key_error(self):
        from app.services.llm_summary import LLMSummaryError, generate_summary
        import httpx

        with (
            patch("app.services.llm_summary.settings") as mock_settings,
            patch("httpx.AsyncClient") as mock_client_cls,
        ):
            mock_settings.enable_llm_summary = True
            mock_settings.openai_api_key = "sk-bad"
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            error_response = MagicMock()
            error_response.status_code = 401
            http_err = httpx.HTTPStatusError("unauthorized", request=MagicMock(), response=error_response)
            mock_client.post = AsyncMock(return_value=MagicMock(raise_for_status=MagicMock(side_effect=http_err)))
            mock_client_cls.return_value = mock_client

            with pytest.raises(LLMSummaryError, match="Invalid"):
                await generate_summary("transcript text")

    @pytest.mark.asyncio
    async def test_429_from_openai_raises_rate_limit_error(self):
        from app.services.llm_summary import LLMSummaryError, generate_summary
        import httpx

        with (
            patch("app.services.llm_summary.settings") as mock_settings,
            patch("httpx.AsyncClient") as mock_client_cls,
        ):
            mock_settings.enable_llm_summary = True
            mock_settings.openai_api_key = "sk-test"
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            error_response = MagicMock()
            error_response.status_code = 429
            http_err = httpx.HTTPStatusError("rate limited", request=MagicMock(), response=error_response)
            mock_client.post = AsyncMock(return_value=MagicMock(raise_for_status=MagicMock(side_effect=http_err)))
            mock_client_cls.return_value = mock_client

            with pytest.raises(LLMSummaryError, match="rate limit"):
                await generate_summary("transcript text")

    @pytest.mark.asyncio
    async def test_request_error_raises_connection_error(self):
        from app.services.llm_summary import LLMSummaryError, generate_summary
        import httpx

        with (
            patch("app.services.llm_summary.settings") as mock_settings,
            patch("httpx.AsyncClient") as mock_client_cls,
        ):
            mock_settings.enable_llm_summary = True
            mock_settings.openai_api_key = "sk-test"
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
            mock_client_cls.return_value = mock_client

            with pytest.raises(LLMSummaryError, match="connect"):
                await generate_summary("transcript text")


# ── is_enabled helper ─────────────────────────────────────────────────────────

class TestIsEnabled:
    def test_false_when_flag_is_false(self):
        from app.services.llm_summary import is_enabled
        with patch("app.services.llm_summary.settings") as mock_settings:
            mock_settings.enable_llm_summary = False
            mock_settings.openai_api_key = "sk-test"
            assert is_enabled() is False

    def test_false_when_no_api_key(self):
        from app.services.llm_summary import is_enabled
        with patch("app.services.llm_summary.settings") as mock_settings:
            mock_settings.enable_llm_summary = True
            mock_settings.openai_api_key = ""
            assert is_enabled() is False

    def test_true_when_flag_and_key_set(self):
        from app.services.llm_summary import is_enabled
        with patch("app.services.llm_summary.settings") as mock_settings:
            mock_settings.enable_llm_summary = True
            mock_settings.openai_api_key = "sk-test"
            assert is_enabled() is True


# ── Endpoint integration tests ────────────────────────────────────────────────

@requires_asyncpg
def test_summary_endpoint_returns_503_when_disabled(client):
    job_id = str(uuid.uuid4())
    from app.services.llm_summary import LLMDisabledError

    with (
        patch("app.api.v1.summaries.get_job", new_callable=AsyncMock) as mock_get_job,
        patch("app.api.v1.summaries.get_transcript", new_callable=AsyncMock) as mock_get_transcript,
        patch("app.api.v1.summaries.generate_summary", new_callable=AsyncMock) as mock_generate,
    ):
        mock_job = MagicMock()
        mock_job.id = uuid.UUID(job_id)
        mock_get_job.return_value = mock_job

        mock_doc = MagicMock()
        mock_doc.full_text = "Hello world transcript."
        mock_get_transcript.return_value = (mock_doc, [])

        mock_generate.side_effect = LLMDisabledError("AI summary feature is not enabled on this server.")

        response = client.post(f"/api/transcriptions/{job_id}/summary")

    assert response.status_code == 503
    assert "not enabled" in response.json()["detail"]


@requires_asyncpg
def test_summary_endpoint_returns_404_for_missing_job(client):
    job_id = str(uuid.uuid4())
    with patch("app.api.v1.summaries.get_job", new_callable=AsyncMock) as mock_get_job:
        mock_get_job.return_value = None
        response = client.post(f"/api/transcriptions/{job_id}/summary")
    assert response.status_code == 404


@requires_asyncpg
def test_summary_endpoint_returns_404_for_missing_transcript(client):
    job_id = str(uuid.uuid4())
    with (
        patch("app.api.v1.summaries.get_job", new_callable=AsyncMock) as mock_get_job,
        patch("app.api.v1.summaries.get_transcript", new_callable=AsyncMock) as mock_get_transcript,
    ):
        mock_job = MagicMock()
        mock_job.id = uuid.UUID(job_id)
        mock_get_job.return_value = mock_job
        mock_get_transcript.return_value = (None, [])
        response = client.post(f"/api/transcriptions/{job_id}/summary")
    assert response.status_code == 404


@requires_asyncpg
def test_summary_endpoint_returns_200_with_summary(client):
    job_id = str(uuid.uuid4())
    with (
        patch("app.api.v1.summaries.get_job", new_callable=AsyncMock) as mock_get_job,
        patch("app.api.v1.summaries.get_transcript", new_callable=AsyncMock) as mock_get_transcript,
        patch("app.api.v1.summaries.generate_summary", new_callable=AsyncMock) as mock_generate,
    ):
        mock_job = MagicMock()
        mock_job.id = uuid.UUID(job_id)
        mock_get_job.return_value = mock_job

        mock_doc = MagicMock()
        mock_doc.full_text = "This is a test transcript about Python programming."
        mock_get_transcript.return_value = (mock_doc, [])

        mock_generate.return_value = "The transcript covers Python programming basics."

        response = client.post(f"/api/transcriptions/{job_id}/summary")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["summary"] == "The transcript covers Python programming basics."
    assert data["model"] == "gpt-4o-mini"
    assert data["truncated"] is False


@requires_asyncpg
def test_summary_endpoint_reports_truncated_flag(client):
    from app.services.llm_summary import _MAX_INPUT_CHARS
    job_id = str(uuid.uuid4())
    with (
        patch("app.api.v1.summaries.get_job", new_callable=AsyncMock) as mock_get_job,
        patch("app.api.v1.summaries.get_transcript", new_callable=AsyncMock) as mock_get_transcript,
        patch("app.api.v1.summaries.generate_summary", new_callable=AsyncMock) as mock_generate,
    ):
        mock_job = MagicMock()
        mock_job.id = uuid.UUID(job_id)
        mock_get_job.return_value = mock_job

        mock_doc = MagicMock()
        mock_doc.full_text = "x" * (_MAX_INPUT_CHARS + 1)
        mock_get_transcript.return_value = (mock_doc, [])

        mock_generate.return_value = "Summary of very long transcript."

        response = client.post(f"/api/transcriptions/{job_id}/summary")

    assert response.status_code == 200
    assert response.json()["truncated"] is True
