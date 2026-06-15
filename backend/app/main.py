from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.v1 import transcriptions  # noqa: E402
app.include_router(transcriptions.router, prefix="/api")


@app.get("/health", tags=["health"])
async def health_check() -> JSONResponse:
    return JSONResponse({"status": "ok", "service": settings.app_name})
