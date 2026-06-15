"""Tests for auth: password hashing, JWT, and dependency parsing."""
import time
import uuid

import pytest

from app.auth.password import hash_password, verify_password
from app.auth.jwt_handler import create_access_token, decode_access_token
from app.auth.dependencies import _parse_token


# ── Password ──────────────────────────────────────────────────────────────────

def test_hash_password_returns_string():
    h = hash_password("secret123")
    assert isinstance(h, str)
    assert "$" in h


def test_verify_correct_password():
    h = hash_password("correct-horse-battery-staple")
    assert verify_password("correct-horse-battery-staple", h) is True


def test_verify_wrong_password():
    h = hash_password("correct-horse-battery-staple")
    assert verify_password("wrong-password", h) is False


def test_different_hashes_for_same_password():
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2  # different salts


def test_verify_invalid_hash_returns_false():
    assert verify_password("any", "not-a-valid-hash") is False


# ── JWT ───────────────────────────────────────────────────────────────────────

def test_create_and_decode_token():
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id, "user@example.com")
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["email"] == "user@example.com"


def test_tampered_signature_rejected():
    token = create_access_token(str(uuid.uuid4()), "x@example.com")
    parts = token.split(".")
    # Flip a character in the signature
    corrupted_sig = parts[2][:-1] + ("A" if parts[2][-1] != "A" else "B")
    bad_token = ".".join([parts[0], parts[1], corrupted_sig])
    assert decode_access_token(bad_token) is None


def test_expired_token_rejected(monkeypatch):
    import app.auth.jwt_handler as jh
    from app.config import settings

    # Create a token whose exp is 1 second in the past.
    # exp = mock_now + jwt_expire_minutes*60, so mock_now must be:
    #   mock_now = real_now - jwt_expire_minutes*60 - 1
    real_now = time.time()
    mock_now = real_now - settings.jwt_expire_minutes * 60 - 1

    monkeypatch.setattr(jh.time, "time", lambda: mock_now)
    token = create_access_token(str(uuid.uuid4()), "expired@example.com")
    monkeypatch.undo()

    # With real time, exp is already in the past
    assert decode_access_token(token) is None


def test_malformed_token_rejected():
    assert decode_access_token("not.a.valid") is None
    assert decode_access_token("") is None
    assert decode_access_token("only-one-part") is None


# ── Dependency ────────────────────────────────────────────────────────────────

def test_parse_token_returns_none_for_no_credentials():
    result = _parse_token(None)
    assert result is None


def test_parse_token_returns_user_for_valid_token():
    from fastapi.security import HTTPAuthorizationCredentials

    user_id = uuid.uuid4()
    token = create_access_token(str(user_id), "dep@example.com")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = _parse_token(creds)
    assert user is not None
    assert user.id == user_id
    assert user.email == "dep@example.com"


def test_parse_token_returns_none_for_bad_token():
    from fastapi.security import HTTPAuthorizationCredentials

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad.token.here")
    assert _parse_token(creds) is None
