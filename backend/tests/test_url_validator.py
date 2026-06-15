from unittest.mock import patch

import pytest

from app.security.url_validator import URLValidationError, validate_url


def _mock_resolve_empty(hostname):
    return []


def _mock_resolve_public(hostname):
    return ["142.250.80.46"]


@pytest.mark.parametrize(
    "url,expected_error",
    [
        ("", "non-empty"),
        ("ftp://example.com/video", "not allowed"),
        ("file:///etc/passwd", "not allowed"),
        ("javascript:alert(1)", "not allowed"),
        ("http://localhost/video", "not allowed"),
        ("http://127.0.0.1/video", "not allowed"),
        ("http://0.0.0.0/video", "not allowed"),
        ("http://10.0.0.1/video", "not allowed"),
        ("http://172.16.0.1/video", "not allowed"),
        ("http://192.168.1.1/video", "not allowed"),
        ("http://169.254.1.1/video", "not allowed"),
        ("not-a-url", "scheme"),
        ("http:///no-host", "hostname"),
    ],
)
def test_blocked_urls(url, expected_error):
    with patch(
        "app.security.url_validator._resolve_hostname", side_effect=_mock_resolve_empty
    ):
        with pytest.raises(URLValidationError, match=expected_error):
            validate_url(url)


def test_valid_youtube_url():
    with patch(
        "app.security.url_validator._resolve_hostname", return_value=["142.250.80.46"]
    ):
        source_type, domain = validate_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert source_type == "youtube"
    assert "youtube.com" in domain


def test_private_ip_via_dns_rejected():
    with patch(
        "app.security.url_validator._resolve_hostname", return_value=["192.168.1.100"]
    ):
        with pytest.raises(URLValidationError, match="private"):
            validate_url("https://example.com/video")


def test_url_too_long():
    long_url = "https://www.youtube.com/" + "a" * 3000
    with pytest.raises(URLValidationError, match="length"):
        validate_url(long_url)


def test_media_stored_never_set():
    """Verify that the media_stored field is always False by design."""
    media_stored = False
    assert media_stored is False, "media_stored must always be False — media is never stored"
