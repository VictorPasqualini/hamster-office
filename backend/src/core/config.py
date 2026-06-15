from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://app_rw:app_pw@db:5432/hamster"
    database_superuser_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/hamster"
    app_db_user: str = "app_rw"
    app_db_password: str = "app_pw"

    redis_url: str = "redis://redis:6379/0"

    minio_endpoint: str = "minio:9000"
    minio_public_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "hamster"
    minio_secure: bool = False

    ollama_url: str = "http://ollama:11434"
    ollama_chat_model: str = "qwen3:8b"
    ollama_embed_model: str = "qwen3:8b"
    embed_dim: int = 1024
    ollama_required: bool = False

    jwt_secret: str = "dev-secret-change-me-please-use-32+chars"
    jwt_alg: str = "HS256"
    access_token_ttl_min: int = 60
    refresh_token_ttl_days: int = 14

    cors_origins: str = "http://localhost:3000,http://localhost:8000"
    seed_demo: bool = True

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
