import ipaddress
import logging
from urllib.parse import urlparse

import dns.resolver
import dns.exception

logger = logging.getLogger(__name__)

ALLOWED_SCHEMES = {"https", "http"}

BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("::ffff:0:0/96"),
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "broadcasthost",
    "ip6-localhost",
    "ip6-loopback",
}

SUPPORTED_DOMAINS = {
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "m.youtube.com",
}

MAX_URL_LENGTH = 2048


class URLValidationError(ValueError):
    pass


def _is_private_ip(addr: str) -> bool:
    try:
        ip = ipaddress.ip_address(addr)
        return any(ip in net for net in BLOCKED_NETWORKS)
    except ValueError:
        return False


def validate_url(url: str) -> tuple[str, str]:
    """
    Validate URL for safety and support. Returns (source_type, source_domain).
    Raises URLValidationError on any violation.
    """
    if not url or not isinstance(url, str):
        raise URLValidationError("URL must be a non-empty string.")

    url = url.strip()
    if len(url) > MAX_URL_LENGTH:
        raise URLValidationError(f"URL exceeds maximum length of {MAX_URL_LENGTH} characters.")

    try:
        parsed = urlparse(url)
    except Exception:
        raise URLValidationError("Malformed URL.")

    scheme = parsed.scheme.lower()
    if not scheme:
        raise URLValidationError("URL must include a scheme (https://).")
    if scheme not in ALLOWED_SCHEMES:
        raise URLValidationError(
            f"Scheme '{scheme}://' is not allowed. Only https:// and http:// are permitted."
        )

    hostname = parsed.hostname
    if not hostname:
        raise URLValidationError("URL has no valid hostname.")

    hostname = hostname.lower()

    if hostname in BLOCKED_HOSTNAMES:
        raise URLValidationError(f"Hostname '{hostname}' is not allowed.")

    if _is_private_ip(hostname):
        raise URLValidationError("URLs resolving to private or loopback addresses are not allowed.")

    resolved_ips = _resolve_hostname(hostname)
    for ip in resolved_ips:
        if _is_private_ip(ip):
            raise URLValidationError(
                "URL resolves to a private or loopback IP address."
            )

    source_type = _detect_source_type(hostname)
    return source_type, hostname


def _resolve_hostname(hostname: str) -> list[str]:
    try:
        answers = dns.resolver.resolve(hostname, "A", lifetime=5)
        return [str(r) for r in answers]
    except dns.exception.DNSException:
        pass

    try:
        answers = dns.resolver.resolve(hostname, "AAAA", lifetime=5)
        return [str(r) for r in answers]
    except dns.exception.DNSException:
        pass

    return []


def _detect_source_type(hostname: str) -> str:
    hostname = hostname.lower()
    if hostname in SUPPORTED_DOMAINS:
        return "youtube"
    return "unknown"


def extract_domain(url: str) -> str:
    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""
