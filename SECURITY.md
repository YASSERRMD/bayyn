# Bayyn Security Model

## URL Validation

All submitted URLs pass through a multi-layer security validator before any processing begins:

### Blocked Schemes
- `file://`
- `ftp://`
- `javascript:`
- Any scheme not in `{https, http}`

### Blocked Hostnames
- `localhost`
- `localhost.localdomain`
- `broadcasthost`
- `ip6-localhost`
- `ip6-loopback`

### Blocked IP Ranges (IPv4)
```
127.0.0.0/8      Loopback
10.0.0.0/8       RFC 1918 Private
172.16.0.0/12    RFC 1918 Private
192.168.0.0/16   RFC 1918 Private
169.254.0.0/16   Link-local (APIPA)
0.0.0.0/8        "This" network
100.64.0.0/10    Shared address space
198.18.0.0/15    Benchmarking
240.0.0.0/4      Reserved
```

### Blocked IP Ranges (IPv6)
```
::1/128           IPv6 loopback
fc00::/7          IPv6 unique local
fe80::/10         IPv6 link-local
::ffff:0:0/96     IPv4-mapped IPv6
```

### DNS Resolution Check
After parsing, Bayyn resolves the hostname via DNS (A + AAAA records) and checks all
resolved IPs against the blocked range list. This prevents DNS rebinding attacks.

## Rate Limiting
- 10 requests per minute per IP (configurable via `RATE_LIMIT_PER_MINUTE`)
- Implemented via `slowapi`

## Temp File Security
- Each job gets an isolated temp directory: `/tmp/bayyn/{job_uuid}`
- Deleted on success (in `finally` block)
- Deleted on failure (in `finally` block)
- Temp paths are never returned in API responses
- Only SHA-256 hash of temp path is logged, never the full path
- Audio stream URLs are never logged (redacted from error messages)
- Stale directories older than 1 hour are cleaned at startup and on schedule

## Media Storage Invariant
The `media_stored` column in `transcription_jobs` is always `false`.
This is enforced at the application layer and verified in the test suite.

## Error Sanitization
Worker errors are sanitized before storage:
- `https?://\S+` → `[URL_REDACTED]`
- `/tmp/\S+` → `[PATH_REDACTED]`
- Truncated to 512 characters

## Database Security
- UUID primary keys prevent enumeration
- Soft delete preserves audit trail without exposing content
- All queries use parameterized SQLAlchemy ORM (no raw SQL injection surface)
