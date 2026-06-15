"""Tests for observability: request-ID middleware and structured logging."""
import json
import logging
import uuid

import pytest

from tests.conftest import requires_asyncpg


# ── RequestIDMiddleware (standalone ASGI test, no asyncpg needed) ─────────────

def _make_test_app():
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    from app.middleware.request_id import RequestIDMiddleware

    async def homepage(request):
        from app.middleware.request_id import get_request_id
        return JSONResponse({"request_id": get_request_id()})

    app = Starlette(routes=[Route("/", homepage)])
    app.add_middleware(RequestIDMiddleware)
    return app


def test_request_id_added_to_response_header():
    from starlette.testclient import TestClient
    client = TestClient(_make_test_app())
    response = client.get("/")
    assert "x-request-id" in response.headers
    # Must be a valid UUID
    val = response.headers["x-request-id"]
    uuid.UUID(val)  # raises ValueError if not a UUID


def test_existing_request_id_forwarded():
    from starlette.testclient import TestClient
    existing_id = str(uuid.uuid4())
    client = TestClient(_make_test_app())
    response = client.get("/", headers={"X-Request-ID": existing_id})
    assert response.headers["x-request-id"] == existing_id


def test_request_id_available_in_context():
    from starlette.testclient import TestClient
    client = TestClient(_make_test_app())
    response = client.get("/")
    body = response.json()
    # The context var should be the same as the response header
    assert body["request_id"] == response.headers["x-request-id"]


def test_different_requests_get_different_ids():
    from starlette.testclient import TestClient
    client = TestClient(_make_test_app())
    r1 = client.get("/")
    r2 = client.get("/")
    assert r1.headers["x-request-id"] != r2.headers["x-request-id"]


# ── JsonFormatter ─────────────────────────────────────────────────────────────

def test_json_formatter_emits_valid_json():
    from app.logging_config import JsonFormatter

    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="hello world", args=(), exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["msg"] == "hello world"
    assert parsed["level"] == "INFO"
    assert "ts" in parsed


def test_json_formatter_includes_extra_fields():
    from app.logging_config import JsonFormatter

    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="job done", args=(), exc_info=None,
    )
    record.job_id = "abc-123"
    record.duration_ms = 42.1
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["job_id"] == "abc-123"
    assert parsed["duration_ms"] == 42.1


def test_json_formatter_includes_exception():
    from app.logging_config import JsonFormatter
    import sys

    formatter = JsonFormatter()
    try:
        raise ValueError("boom")
    except ValueError:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test", level=logging.ERROR, pathname="", lineno=0,
        msg="error occurred", args=(), exc_info=exc_info,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert "exc" in parsed
    assert "ValueError" in parsed["exc"]


# ── Health endpoint ───────────────────────────────────────────────────────────

@requires_asyncpg
def test_health_simple_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@requires_asyncpg
def test_health_detailed_returns_components(client):
    """Verify /health/detailed has the expected JSON structure."""
    response = client.get("/health/detailed")
    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert body["status"] in ("ok", "degraded")
    assert "components" in body
    assert "database" in body["components"]
    assert "redis" in body["components"]


def test_get_request_id_default_empty():
    from app.middleware.request_id import get_request_id
    # Outside of a request context, get_request_id() returns ""
    result = get_request_id()
    assert result == ""
