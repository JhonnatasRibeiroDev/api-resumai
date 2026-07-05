from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ResumAi API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"

    database_url: str = (
        "postgresql+psycopg://resumai:resumai_password@postgres:5432/resumai"
    )

    jwt_secret: str = "change_this_secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    upload_dir: str = "/app/uploads"
    max_upload_size_mb: int = 50
    max_llm_chars: int = 30_000
    summary_chunk_chars: int = 12_000
    summary_chunk_overlap_chars: int = 500
    summary_max_chunks: int = 20
    user_max_active_summary_jobs: int = 2
    summary_max_attempts: int = 3

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    celery_broker_url: str = "amqp://resumai:resumai_password@rabbitmq:5672//"
    enqueue_summary_jobs: bool = True

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
