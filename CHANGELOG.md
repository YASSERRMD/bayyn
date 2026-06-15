# Changelog

All notable changes to Bayyn are documented here.

## [0.1.0] — 2026-06-16

Initial release of Bayyn — a privacy-first URL-to-transcript platform.

### Core features

- **URL-to-transcript pipeline**: submit any YouTube URL, get a timestamped transcript
- **Caption-first strategy**: extract native captions when available (instant, no GPU)
- **Whisper fallback**: stream audio → faster-whisper for videos without captions
- **Privacy by design**: `media_stored = false` enforced in code and verified by tests; temp dirs deleted after every job (success, failure, retry)
- **Soft delete**: jobs soft-deleted by default (`deleted_at` timestamp); hard delete available

### Auth and ownership

- **User accounts**: PBKDF2-HMAC-SHA256 passwords + HS256 JWT authentication
- **Job ownership**: jobs scoped to their creator; cross-user access returns 404 (anti-enumeration)
- **Admin role**: `is_admin` JWT claim gates `/api/admin/*` and `/api/metrics`
- **Rate limiting**: per-IP slowapi on POST + per-user DB checks (active jobs cap, daily cap)

### API surface

- Transcription CRUD + segment editing + TXT/SRT/DOCX export
- Auth: register, login, `/me`
- Admin: job list (filterable, paginated), single job metadata
- Metrics: jobs by status/strategy, success rate, retry rate, avg duration
- LLM summary: optional `POST /api/transcriptions/{id}/summary` via OpenAI (gated by `ENABLE_LLM_SUMMARY`)

### Security

- SSRF protection: private IP ranges (RFC 1918, loopback, link-local, AWS metadata), scheme allow-list
- JWT attack surface covered: alg=none, empty signature, wrong secret, forged claims
- Error sanitization: `sanitize_for_audit()` strips URLs and paths from tracebacks; `classify_error()` returns user-safe messages
- Production startup guards: rejects insecure `SECRET_KEY`, localhost `DATABASE_URL`

### Observability

- `ContextVar`-based request ID propagation across async middleware
- JSON structured logging via `JsonFormatter`
- `/health/detailed`: DB + Redis connectivity
- Worker heartbeat task

### Frontend

- Next.js 15 + TypeScript + Tailwind (Navy #1B2A4A / Gold #C5A55A)
- Login, register, history, transcript detail, export buttons
- Auth context with JWT storage, loading states, redirect guards
- Playwright E2E tests (auth flows, export buttons, privacy notice)

### Infrastructure

- Docker Compose: postgres:16, redis:7, backend (uvicorn), worker (celery), frontend (Next.js)
- GitHub Actions CI: backend tests (asyncpg + full suite), frontend build + tsc + eslint, Playwright E2E
- Alembic migrations: 7 migration files covering all schema changes
- Production config: `APP_ENV=production` enables strict guards; `.env.example` documents all variables

### Testing

323 tests across 25 test files:
- Unit: JWT, password, URL validation, error mapping, temp cleanup, performance
- Integration: auth flows, ownership, rate limiting, admin access, request ID
- Security: SSRF, JWT forgery, audit sanitization, input validation
- E2E (Playwright): login, register, export buttons, history redirect
- QA assertions: cross-cutting invariants verified as a living spec

[0.1.0]: https://github.com/YASSERRMD/bayyn/releases/tag/v0.1.0
