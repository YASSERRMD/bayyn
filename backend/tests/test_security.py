"""Security-focused tests: SSRF, token tampering, injection, path traversal."""
import uuid
from unittest.mock import patch

import pytest

from app.auth.jwt_handler import create_access_token, decode_access_token
from app.security.url_validator import URLValidationError, validate_url


# ── SSRF: URL validator blocks private/reserved ranges ────────────────────────

SSRF_URLS = [
    "http://localhost/api",
    "http://127.0.0.1/secret",
    "http://0.0.0.0/data",
    "http://[::1]/admin",
    "http://169.254.169.254/latest/meta-data/",  # AWS metadata
    "http://10.0.0.1/internal",
    "http://192.168.1.100/router",
    "http://172.16.0.1/vpc",
]


@pytest.mark.parametrize("url", SSRF_URLS)
def test_ssrf_private_ip_blocked(url):
    with patch("app.security.url_validator._resolve_hostname", return_value=[]):
        with pytest.raises(URLValidationError):
            validate_url(url)


def test_ssrf_file_scheme_blocked():
    with pytest.raises(URLValidationError):
        validate_url("file:///etc/passwd")


def test_ssrf_ftp_scheme_blocked():
    with pytest.raises(URLValidationError):
        validate_url("ftp://example.com/file")


def test_ssrf_non_http_scheme_blocked():
    with pytest.raises(URLValidationError):
        validate_url("javascript:alert(1)")


# ── URL validation: only supported domains ────────────────────────────────────

def test_non_youtube_domain_returns_unknown_source_type():
    """Unknown-domain URLs are accepted but labeled 'unknown' (go through Whisper)."""
    with patch("app.security.url_validator._resolve_hostname", return_value=["93.184.216.34"]):
        source_type, domain = validate_url("https://example.com/video")
    assert source_type == "unknown"


def test_supported_youtube_domain_accepted():
    with patch("app.security.url_validator._resolve_hostname", return_value=["142.250.80.110"]):
        source_type, domain = validate_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert source_type == "youtube"


# ── Token security ────────────────────────────────────────────────────────────

def test_none_algorithm_attack_rejected():
    """JWT 'alg=none' attack must not bypass verification."""
    import base64, json

    def b64(s: str) -> str:
        return base64.urlsafe_b64encode(s.encode()).rstrip(b"=").decode()

    import time
    header = b64('{"alg":"none","typ":"JWT"}')
    payload = b64(json.dumps({"sub": str(uuid.uuid4()), "email": "attacker@example.com", "exp": int(time.time()) + 3600}))
    # "none" algorithm means no signature
    forged_token = f"{header}.{payload}."

    assert decode_access_token(forged_token) is None


def test_empty_signature_rejected():
    token = create_access_token(str(uuid.uuid4()), "user@example.com")
    parts = token.split(".")
    no_sig = f"{parts[0]}.{parts[1]}."
    assert decode_access_token(no_sig) is None


def test_wrong_secret_rejected():
    """Token signed with a different secret must be rejected."""
    import base64, hashlib, hmac, json, time
    from app.config import settings

    def b64(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = b64(json.dumps({"sub": str(uuid.uuid4()), "email": "x@x.com", "exp": int(time.time()) + 3600, "is_admin": False}).encode())
    wrong_secret = "wrong-secret-key"
    sig = hmac.new(wrong_secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    bad_token = f"{header}.{payload}.{b64(sig)}"

    assert decode_access_token(bad_token) is None


def test_admin_claim_cannot_be_forged_without_secret():
    """Attacker cannot forge is_admin=True without the signing secret."""
    import base64, hashlib, hmac, json, time

    def b64(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = b64(json.dumps({
        "sub": str(uuid.uuid4()), "email": "attacker@example.com",
        "exp": int(time.time()) + 3600, "is_admin": True,
    }).encode())
    # Signed with wrong secret
    sig = hmac.new(b"wrong", f"{header}.{payload}".encode(), hashlib.sha256).digest()
    forged = f"{header}.{payload}.{b64(sig)}"

    result = decode_access_token(forged)
    assert result is None


# ── Audit log: sanitize_for_audit removes sensitive data ─────────────────────

def test_sanitize_removes_url_from_traceback():
    from app.errors.error_mapper import sanitize_for_audit
    exc = ValueError("failed to fetch https://secret.internal/api?key=MY_SECRET_KEY")
    output = sanitize_for_audit(exc)
    assert "secret.internal" not in output
    assert "[URL]" in output


def test_sanitize_removes_filesystem_paths():
    from app.errors.error_mapper import sanitize_for_audit
    exc = FileNotFoundError("/tmp/bayyn/job-abc123/audio.wav")
    output = sanitize_for_audit(exc)
    assert "/tmp/bayyn" not in output
    assert "[PATH]" in output


def test_classify_error_never_exposes_exception_details():
    from app.errors.error_mapper import classify_error
    exc = RuntimeError("Internal server error: DB connection failed at host=db.internal:5432 user=bayyn")
    message = classify_error(exc)
    # User-facing message must not contain any internal details
    assert "db.internal" not in message
    assert "5432" not in message
    assert "bayyn" not in message
    # Must be a generic safe message
    assert len(message) < 200


# ── Segment editing: text length limits ──────────────────────────────────────

def test_segment_patch_rejects_oversized_text():
    from app.schemas.transcript import PatchSegmentRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        PatchSegmentRequest(text="x" * 4097)


def test_segment_patch_rejects_empty_text():
    from app.schemas.transcript import PatchSegmentRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        PatchSegmentRequest(text="")


# ── Password security ─────────────────────────────────────────────────────────

def test_password_hash_uses_sufficient_iterations():
    from app.auth.password import hash_password, _ITERATIONS, _ALGORITHM
    assert _ITERATIONS >= 100_000, "PBKDF2 iterations must be >= 100k for security"
    assert _ALGORITHM == "pbkdf2_sha256"


def test_password_hash_is_not_reversible_to_original():
    from app.auth.password import hash_password
    raw = "my-secret-password"
    h = hash_password(raw)
    assert raw not in h
    # Must not be base64 of the raw password
    import base64
    assert h != base64.b64encode(raw.encode()).decode()


def test_timing_safe_comparison_used():
    """verify_password must use compare_digest (timing-safe), not == operator."""
    import inspect
    from app.auth import password as pw_module
    source = inspect.getsource(pw_module)
    assert "compare_digest" in source
    # Must NOT use a direct equality comparison on raw bytes
    assert "== digest" not in source and "digest ==" not in source
