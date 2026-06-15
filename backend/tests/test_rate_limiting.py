"""Tests for per-user rate limiting (active-job cap and daily-job cap)."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.rate_limiter import RateLimitError, check_user_limits


# ── Helpers ───────────────────────────────────────────────────────────────────

def _count_db(active: int, daily: int):
    """Return a mock AsyncSession that answers count queries in order."""
    results = [_scalar_result(active), _scalar_result(daily)]
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=lambda s: results.pop(0))
    return db


def _scalar_result(value):
    r = MagicMock()
    r.scalar_one.return_value = value
    return r


# ── Anonymous user — no DB checks ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_anonymous_user_skips_db_checks():
    db = AsyncMock()
    await check_user_limits(db, user_id=None)
    db.execute.assert_not_called()


# ── Active-job cap ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_under_active_limit_passes():
    from app.config import settings
    db = _count_db(active=settings.max_active_jobs_per_user - 1, daily=0)
    await check_user_limits(db, user_id=uuid.uuid4())  # should not raise


@pytest.mark.asyncio
async def test_at_active_limit_raises():
    from app.config import settings
    db = _count_db(active=settings.max_active_jobs_per_user, daily=0)
    with pytest.raises(RateLimitError, match="already have"):
        await check_user_limits(db, user_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_exceeds_active_limit_raises():
    from app.config import settings
    db = _count_db(active=settings.max_active_jobs_per_user + 3, daily=0)
    with pytest.raises(RateLimitError):
        await check_user_limits(db, user_id=uuid.uuid4())


# ── Daily-job cap ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_under_daily_limit_passes():
    from app.config import settings
    db = _count_db(active=0, daily=settings.max_daily_jobs_per_user - 1)
    await check_user_limits(db, user_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_at_daily_limit_raises():
    from app.config import settings
    db = _count_db(active=0, daily=settings.max_daily_jobs_per_user)
    with pytest.raises(RateLimitError, match="daily limit"):
        await check_user_limits(db, user_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_exceeds_daily_limit_raises():
    from app.config import settings
    db = _count_db(active=0, daily=settings.max_daily_jobs_per_user + 10)
    with pytest.raises(RateLimitError):
        await check_user_limits(db, user_id=uuid.uuid4())


# ── Active-limit checked before daily ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_active_limit_checked_first():
    """If active-job limit is hit, we raise before even checking daily count."""
    from app.config import settings

    # Return active=limit, but daily DB query should NOT be executed at all
    active_result = _scalar_result(settings.max_active_jobs_per_user)
    db = AsyncMock()
    db.execute = AsyncMock(return_value=active_result)

    with pytest.raises(RateLimitError, match="already have"):
        await check_user_limits(db, user_id=uuid.uuid4())

    # Only one execute call (active count); daily was never queried
    assert db.execute.call_count == 1


# ── Config defaults ───────────────────────────────────────────────────────────

def test_config_defaults():
    from app.config import Settings
    s = Settings()
    assert s.max_active_jobs_per_user >= 1
    assert s.max_daily_jobs_per_user >= 1
    assert s.max_daily_jobs_per_user >= s.max_active_jobs_per_user
