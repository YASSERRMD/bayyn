"""Tests for admin role: JWT claim, dependency guard, and admin endpoints."""
import uuid

import pytest

from app.auth.jwt_handler import create_access_token, decode_access_token
from app.auth.dependencies import _parse_token


# ── JWT carries is_admin claim ────────────────────────────────────────────────

def test_token_contains_is_admin_false_by_default():
    token = create_access_token(str(uuid.uuid4()), "user@example.com")
    payload = decode_access_token(token)
    assert payload is not None
    assert payload.get("is_admin") is False


def test_token_contains_is_admin_true_when_set():
    token = create_access_token(str(uuid.uuid4()), "admin@example.com", is_admin=True)
    payload = decode_access_token(token)
    assert payload is not None
    assert payload.get("is_admin") is True


# ── CurrentUser.is_admin parsed correctly ─────────────────────────────────────

def test_parse_token_non_admin_user():
    from fastapi.security import HTTPAuthorizationCredentials

    user_id = uuid.uuid4()
    token = create_access_token(str(user_id), "user@example.com", is_admin=False)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = _parse_token(creds)
    assert user is not None
    assert user.is_admin is False


def test_parse_token_admin_user():
    from fastapi.security import HTTPAuthorizationCredentials

    user_id = uuid.uuid4()
    token = create_access_token(str(user_id), "admin@example.com", is_admin=True)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = _parse_token(creds)
    assert user is not None
    assert user.is_admin is True


# ── Legacy tokens without is_admin claim default to False ─────────────────────

def test_legacy_token_without_is_admin_defaults_false():
    """Tokens created before the is_admin claim was added should still work."""
    import base64, json, hmac, hashlib
    from app.config import settings

    def b64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    import time
    header = b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    # No is_admin field in the payload (legacy token)
    payload_data = {"sub": str(uuid.uuid4()), "email": "old@example.com", "exp": int(time.time()) + 3600}
    payload = b64url_encode(json.dumps(payload_data).encode())
    sig = hmac.new(settings.secret_key.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    legacy_token = f"{header}.{payload}.{b64url_encode(sig)}"

    from fastapi.security import HTTPAuthorizationCredentials
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=legacy_token)
    user = _parse_token(creds)
    assert user is not None
    assert user.is_admin is False


# ── Admin dependency: 401 for unauthenticated, 403 for non-admin ──────────────

@pytest.mark.asyncio
async def test_admin_dependency_rejects_unauthenticated():
    from app.auth.dependencies import get_admin_user
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await get_admin_user(credentials=None)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_admin_dependency_rejects_non_admin():
    from fastapi.security import HTTPAuthorizationCredentials
    from app.auth.dependencies import get_admin_user
    from fastapi import HTTPException

    token = create_access_token(str(uuid.uuid4()), "user@example.com", is_admin=False)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc_info:
        await get_admin_user(credentials=creds)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_admin_dependency_allows_admin():
    from fastapi.security import HTTPAuthorizationCredentials
    from app.auth.dependencies import get_admin_user

    admin_id = uuid.uuid4()
    token = create_access_token(str(admin_id), "admin@example.com", is_admin=True)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = await get_admin_user(credentials=creds)
    assert user is not None
    assert user.id == admin_id
    assert user.is_admin is True


# ── AdminJobEntry: metadata-only (no transcript text) ─────────────────────────

def test_admin_job_entry_has_no_transcript_fields():
    from app.api.v1.admin import AdminJobEntry
    fields = AdminJobEntry.model_fields.keys()
    # Confirm transcript text is NOT exposed in the admin job view
    assert "full_text" not in fields
    assert "segments" not in fields


def test_admin_job_entry_exposes_ownership_metadata():
    from app.api.v1.admin import AdminJobEntry
    fields = AdminJobEntry.model_fields.keys()
    assert "user_id" in fields
    assert "status" in fields
    assert "media_stored" in fields
