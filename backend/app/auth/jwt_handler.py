"""
Minimal JWT implementation using HMAC-SHA256 (HS256) and Python built-ins only.
Produces standard JWT tokens (header.payload.signature).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Optional

from app.config import settings


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_access_token(user_id: str, email: str) -> str:
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    expire = int(time.time()) + settings.jwt_expire_minutes * 60
    payload = _b64url_encode(
        json.dumps({"sub": user_id, "email": email, "exp": expire}).encode()
    )
    sig_input = f"{header}.{payload}".encode()
    sig = hmac.new(
        settings.secret_key.encode(), sig_input, hashlib.sha256
    ).digest()
    return f"{header}.{payload}.{_b64url_encode(sig)}"


def decode_access_token(token: str) -> Optional[dict]:
    """Return payload dict if the token is valid and not expired, else None."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_part, payload_part, sig_part = parts
        sig_input = f"{header_part}.{payload_part}".encode()
        expected = hmac.new(
            settings.secret_key.encode(), sig_input, hashlib.sha256
        ).digest()
        actual = _b64url_decode(sig_part)
        if not hmac.compare_digest(expected, actual):
            return None
        payload = json.loads(_b64url_decode(payload_part))
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None
