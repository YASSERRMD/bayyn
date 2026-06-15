"""
Password hashing using PBKDF2-HMAC-SHA256 (Python built-in).
Produces tokens compatible with Django-style {algorithm}${iterations}${salt}${hash}.
"""
from __future__ import annotations

import base64
import hashlib
import os
import secrets

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 260_000
_SALT_BYTES = 16


def hash_password(raw_password: str) -> str:
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", raw_password.encode(), salt, _ITERATIONS)
    salt_b64 = base64.b64encode(salt).decode()
    hash_b64 = base64.b64encode(digest).decode()
    return f"{_ALGORITHM}${_ITERATIONS}${salt_b64}${hash_b64}"


def verify_password(raw_password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_str, salt_b64, hash_b64 = encoded.split("$")
        if algorithm != _ALGORITHM:
            return False
        iterations = int(iterations_str)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        digest = hashlib.pbkdf2_hmac("sha256", raw_password.encode(), salt, iterations)
        return secrets.compare_digest(digest, expected)
    except (ValueError, Exception):
        return False
