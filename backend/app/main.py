from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.logging_config import configure_logging
from app.middleware.request_id import RequestIDMiddleware

configure_logging()
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.temp_manager import TempManager
    TempManager.startup_cleanup()
    yield


app = FastAPI(
    title=settings.app_name,
    description="Privacy-first URL-to-transcript API. Store knowledge, not media.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all: log internally, never expose stack traces or paths to clients."""
    logger.error(
        "Unhandled exception method=%s path=%s exc_type=%s exc=%r",
        request.method,
        request.url.path,
        type(exc).__name__,
        str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )


from app.api.v1 import admin, auth, transcriptions  # noqa: E402
app.include_router(transcriptions.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/health", tags=["health"])
async def health_check() -> JSONResponse:
    return JSONResponse({"status": "ok", "service": settings.app_name})


@app.get("/health/detailed", tags=["health"])
async def health_detailed() -> JSONResponse:
    """Component-level health: DB and Redis connectivity."""
    components: dict = {}

    # Database ping
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text as sa_text
        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        async with engine.connect() as conn:
            await conn.execute(sa_text("SELECT 1"))
        await engine.dispose()
        components["database"] = "ok"
    except Exception as exc:
        logger.warning("health: database unreachable exc_type=%s", type(exc).__name__)
        components["database"] = "unreachable"

    # Redis ping
    try:
        import redis as _redis
        r = _redis.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
        components["redis"] = "ok"
    except Exception as exc:
        logger.warning("health: redis unreachable exc_type=%s", type(exc).__name__)
        components["redis"] = "unreachable"

    overall = "ok" if all(v == "ok" for v in components.values()) else "degraded"
    return JSONResponse({"status": overall, "service": settings.app_name, "components": components})
