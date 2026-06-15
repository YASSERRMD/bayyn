"""Tests for the metrics endpoint aggregation logic."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row(status_val, n):
    row = MagicMock()
    row.status = status_val
    row.n = n
    return row


def _strat_row(strat_val, n):
    row = MagicMock()
    row.processing_strategy = strat_val
    row.n = n
    return row


def _scalar_result(value):
    r = MagicMock()
    r.scalar_one.return_value = value
    return r


def _fetchall_result(rows):
    r = MagicMock()
    r.__iter__ = lambda self: iter(rows)
    return r


# ── Success rate calculation (pure logic) ─────────────────────────────────────

def test_success_rate_all_completed():
    completed, failed = 10, 0
    terminal = completed + failed
    rate = round(completed / terminal, 4) if terminal > 0 else None
    assert rate == 1.0


def test_success_rate_mixed():
    completed, failed = 7, 3
    terminal = completed + failed
    rate = round(completed / terminal, 4) if terminal > 0 else None
    assert rate == 0.7


def test_success_rate_none_when_no_terminal_jobs():
    completed, failed = 0, 0
    terminal = completed + failed
    rate = round(completed / terminal, 4) if terminal > 0 else None
    assert rate is None


def test_success_rate_all_failed():
    completed, failed = 0, 5
    terminal = completed + failed
    rate = round(completed / terminal, 4) if terminal > 0 else None
    assert rate == 0.0


# ── Retry rate calculation (pure logic) ──────────────────────────────────────

def test_retry_rate_no_retries():
    retried, total = 0, 10
    rate = round(retried / total, 4) if total > 0 else None
    assert rate == 0.0


def test_retry_rate_half_retried():
    retried, total = 5, 10
    rate = round(retried / total, 4) if total > 0 else None
    assert rate == 0.5


def test_retry_rate_none_when_no_jobs():
    retried, total = 0, 0
    rate = round(retried / total, 4) if total > 0 else None
    assert rate is None


# ── Metrics response shape (service layer mock) ───────────────────────────────

@pytest.mark.asyncio
async def test_metrics_endpoint_returns_expected_keys():
    """Invoke the endpoint function with a mocked DB and verify the JSON shape."""
    from app.api.v1.metrics import get_metrics
    from app.models.transcription_job import JobStatus, ProcessingStrategy
    from app.auth.dependencies import CurrentUser

    # Ordered mocked DB responses for each execute() call
    status_enum = JobStatus.completed
    strat_enum = ProcessingStrategy.caption

    class _StatusRow:
        status = status_enum
        n = 8

    class _StratRow:
        processing_strategy = strat_enum
        n = 8

    # Build a DB that returns results in call order
    execute_calls = [
        _iter_result([_StatusRow()]),   # status counts
        _iter_result([_StratRow()]),    # strategy counts
        _scalar_result(0),              # dead letter count
        _scalar_result(2),              # retried count
        _scalar_result(45.5),           # avg duration
    ]

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=lambda s: execute_calls.pop(0))

    admin_user = CurrentUser(user_id=uuid.uuid4(), email="admin@example.com", is_admin=True)

    response = await get_metrics(db=db, _admin=admin_user)
    body = response.body
    import json
    data = json.loads(body)

    assert "jobs_total" in data
    assert "jobs_by_status" in data
    assert "jobs_by_strategy" in data
    assert "success_rate" in data
    assert "retry_rate" in data
    assert "dead_letter_count" in data
    assert "avg_processing_duration_seconds" in data


@pytest.mark.asyncio
async def test_metrics_avg_duration_none_when_no_completed():
    from app.api.v1.metrics import get_metrics
    from app.auth.dependencies import CurrentUser
    import json

    execute_calls = [
        _iter_result([]),   # no status rows
        _iter_result([]),   # no strategy rows
        _scalar_result(0),  # dead letters
        _scalar_result(0),  # retried
        _scalar_result(None),  # no completed → avg is None
    ]
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=lambda s: execute_calls.pop(0))

    admin_user = CurrentUser(user_id=uuid.uuid4(), email="admin@example.com", is_admin=True)
    response = await get_metrics(db=db, _admin=admin_user)
    data = json.loads(response.body)
    assert data["avg_processing_duration_seconds"] is None
    assert data["success_rate"] is None
    assert data["jobs_total"] == 0


# ── Helpers ───────────────────────────────────────────────────────────────────

def _iter_result(rows):
    r = MagicMock()
    r.__iter__ = lambda self: iter(rows)
    return r


def _scalar_result(value):
    r = MagicMock()
    r.scalar_one.return_value = value
    return r
