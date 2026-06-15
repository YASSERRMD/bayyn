from pydantic_settings import BaseSettings, SettingsConfigDict


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
    secret_key: str = "change-me-in-production"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # When True (default), job records are soft-deleted (deleted_at set).
    # When False, job records are permanently removed along with their transcript.
    soft_delete_jobs: bool = True

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()
