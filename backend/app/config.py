from typing import List

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Bayyn"
    app_env: str = "development"

    database_url: str = "postgresql+asyncpg://bayyn:bayyn@localhost:5432/bayyn"
    sync_database_url: str = "postgresql://bayyn:bayyn@localhost:5432/bayyn"
    redis_url: str = "redis://localhost:6379/0"

    temp_dir: str = "/tmp/bayyn"
    max_video_duration_seconds: int = 7200
    chunk_threshold_seconds: int = 600
    chunk_duration_seconds: int = 600
    job_timeout_seconds: int = 3600
    max_transcript_chars: int = 1_000_000

    whisper_model: str = "large-v3"
    default_language: str = "en"

    enable_llm_summary: bool = False
    openai_api_key: str = ""

    rate_limit_per_minute: int = 10
    max_active_jobs_per_user: int = 5
    max_daily_jobs_per_user: int = 20
    secret_key: str = _INSECURE_SECRET
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    soft_delete_jobs: bool = True

    # Comma-separated list via CORS_ORIGINS env var; pydantic-settings handles list parsing.
    cors_origins: List[str] = ["http://localhost:3000", "http://frontend:3000"]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @model_validator(mode="after")
    def _validate_production_settings(self) -> "Settings":
        if not self.is_production:
            return self
        if self.secret_key == _INSECURE_SECRET:
            raise ValueError(
                "SECRET_KEY must be changed in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in production.")
        if "localhost" in self.database_url or "127.0.0.1" in self.database_url:
            raise ValueError(
                "DATABASE_URL must point to a production database, not localhost."
            )
        if self.enable_llm_summary and not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY must be set when ENABLE_LLM_SUMMARY=true."
            )
        return self


settings = Settings()
