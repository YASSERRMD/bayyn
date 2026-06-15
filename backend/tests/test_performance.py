"""Phase 36: Performance benchmarks — timing assertions for critical code paths."""
import time
import uuid
from unittest.mock import patch

import pytest

# Wall-clock thresholds (averaged over N iterations, single-threaded, no JIT).
# Generous enough to pass on slow CI; tight enough to catch accidental sync-IO regressions.
JWT_AVG_MS = 20
URL_AVG_MS = 50
ERROR_MAP_AVG_MS = 10
TEMP_CLEANUP_AVG_MS = 5
TEMP_CYCLE_AVG_MS = 25


def _avg_ms(fn, n: int) -> float:
    start = time.perf_counter()
    for _ in range(n):
        fn()
    return (time.perf_counter() - start) * 1000 / n


# ── JWT ───────────────────────────────────────────────────────────────────────

class TestJWTPerformance:
    def test_token_creation_average(self):
        from app.auth.jwt_handler import create_access_token
        uid = str(uuid.uuid4())
        avg = _avg_ms(lambda: create_access_token(uid, "bench@example.com", is_admin=False), 100)
        assert avg < JWT_AVG_MS, f"create_access_token averaged {avg:.2f}ms > {JWT_AVG_MS}ms"

    def test_token_verification_average(self):
        from app.auth.jwt_handler import create_access_token, decode_access_token
        token = create_access_token(str(uuid.uuid4()), "bench@example.com")
        avg = _avg_ms(lambda: decode_access_token(token), 100)
        assert avg < JWT_AVG_MS, f"decode_access_token averaged {avg:.2f}ms > {JWT_AVG_MS}ms"

    def test_invalid_token_rejection_average(self):
        from app.auth.jwt_handler import decode_access_token
        avg = _avg_ms(lambda: decode_access_token("invalid.token.data"), 100)
        assert avg < JWT_AVG_MS, f"Invalid token rejection averaged {avg:.2f}ms > {JWT_AVG_MS}ms"

    def test_token_round_trip_preserves_claims(self):
        from app.auth.jwt_handler import create_access_token, decode_access_token
        uid = str(uuid.uuid4())
        token = create_access_token(uid, "speed@example.com", is_admin=True)
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == uid
        assert payload["is_admin"] is True


# ── URL validation ─────────────────────────────────────────────────────────────

class TestURLValidationPerformance:
    def test_valid_url_average_with_mocked_dns(self):
        from app.security.url_validator import validate_url
        url = "https://www.youtube.com/watch?v=bench"
        with patch("app.security.url_validator._resolve_hostname", return_value=["142.250.80.110"]):
            avg = _avg_ms(lambda: validate_url(url), 200)
        assert avg < URL_AVG_MS, f"URL validation averaged {avg:.2f}ms > {URL_AVG_MS}ms"

    def test_ssrf_rejection_average(self):
        from app.security.url_validator import URLValidationError, validate_url
        def _reject():
            try:
                validate_url("http://127.0.0.1/admin")
            except URLValidationError:
                pass
        avg = _avg_ms(_reject, 200)
        assert avg < URL_AVG_MS, f"SSRF rejection averaged {avg:.2f}ms > {URL_AVG_MS}ms"

    def test_scheme_rejection_average(self):
        from app.security.url_validator import URLValidationError, validate_url
        def _reject():
            try:
                validate_url("file:///etc/passwd")
            except URLValidationError:
                pass
        avg = _avg_ms(_reject, 200)
        assert avg < URL_AVG_MS, f"Scheme rejection averaged {avg:.2f}ms > {URL_AVG_MS}ms"


# ── Error mapper ──────────────────────────────────────────────────────────────

class TestErrorMapperPerformance:
    def test_classify_error_average(self):
        from app.errors.error_mapper import classify_error
        exc = RuntimeError("connection refused to db.internal:5432 user=bayyn")
        avg = _avg_ms(lambda: classify_error(exc), 500)
        assert avg < ERROR_MAP_AVG_MS, f"classify_error averaged {avg:.2f}ms > {ERROR_MAP_AVG_MS}ms"

    def test_sanitize_for_audit_average(self):
        from app.errors.error_mapper import sanitize_for_audit
        exc = RuntimeError(
            "fetch failed: https://secret.internal/path?key=val at /tmp/bayyn/job-id/audio.wav"
        )
        avg = _avg_ms(lambda: sanitize_for_audit(exc), 500)
        assert avg < ERROR_MAP_AVG_MS, f"sanitize_for_audit averaged {avg:.2f}ms > {ERROR_MAP_AVG_MS}ms"

    def test_classify_error_output_is_short(self):
        from app.errors.error_mapper import classify_error
        exc = RuntimeError("x" * 10_000)
        msg = classify_error(exc)
        assert len(msg) < 300


# ── TempManager ───────────────────────────────────────────────────────────────

class TestTempManagerPerformance:
    def test_cleanup_nonexistent_dir_average(self, tmp_path):
        from app.temp_manager import TempManager
        with patch.object(TempManager, "_base_dir", return_value=tmp_path):
            avg = _avg_ms(
                lambda: TempManager.cleanup_job_dir(uuid.uuid4(), reason="completed"),
                500,
            )
        assert avg < TEMP_CLEANUP_AVG_MS, f"cleanup (no-op) averaged {avg:.2f}ms > {TEMP_CLEANUP_AVG_MS}ms"

    def test_full_create_cleanup_cycle_average(self, tmp_path):
        from app.temp_manager import TempManager
        with patch.object(TempManager, "_base_dir", return_value=tmp_path):
            def _cycle():
                jid = uuid.uuid4()
                TempManager.create_job_dir(jid)
                TempManager.cleanup_job_dir(jid, reason="completed")
            avg = _avg_ms(_cycle, 50)
        assert avg < TEMP_CYCLE_AVG_MS, f"create+cleanup cycle averaged {avg:.2f}ms > {TEMP_CYCLE_AVG_MS}ms"

    def test_cleanup_with_files_average(self, tmp_path):
        """Cleanup with real file content should still be fast."""
        from app.temp_manager import TempManager
        with patch.object(TempManager, "_base_dir", return_value=tmp_path):
            # Pre-populate dirs
            ids = []
            for _ in range(20):
                jid = uuid.uuid4()
                d = TempManager.create_job_dir(jid)
                (d / "audio.wav").write_bytes(b"\x00" * 4096)
                ids.append(jid)

            start = time.perf_counter()
            for jid in ids:
                TempManager.cleanup_job_dir(jid, reason="completed")
            avg_ms = (time.perf_counter() - start) * 1000 / 20

        assert avg_ms < 50, f"cleanup with 4KB file averaged {avg_ms:.2f}ms > 50ms"


# ── Password hashing ──────────────────────────────────────────────────────────

class TestPasswordHashPerformance:
    def test_hash_is_slow_enough_for_security(self):
        """PBKDF2 with ≥100k iterations must take at least 50ms — fast hashing is a security risk."""
        from app.auth.password import hash_password
        start = time.perf_counter()
        hash_password("test-password-12345")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms >= 50, (
            f"Password hashing took only {elapsed_ms:.0f}ms — must be ≥50ms for ≥100k PBKDF2 iterations"
        )

    def test_verify_timing_consistent_on_match(self):
        from app.auth.password import hash_password, verify_password
        hashed = hash_password("correct-password")
        times = []
        for _ in range(5):
            t = time.perf_counter()
            verify_password("correct-password", hashed)
            times.append((time.perf_counter() - t) * 1000)
        # Coefficient of variation < 50% — consistent timing
        avg = sum(times) / len(times)
        cv = (max(times) - min(times)) / avg if avg > 0 else 0
        assert cv < 0.5, f"verify_password timing too variable (CV={cv:.2f}), may indicate a timing attack surface"
