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
    job_timeout_seconds: int = 3600
    max_transcript_chars: int = 1_000_000

    whisper_model: str = "large-v3"
    default_language: str = "en"

    enable_llm_summary: bool = False
    openai_api_key: str = ""

    rate_limit_per_minute: int = 10
    secret_key: str = "change-me-in-production"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()
