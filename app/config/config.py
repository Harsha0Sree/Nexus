import secrets
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    database_url: str = Field(..., min_length=1)
    test_database_url: str = ""
    jwt_secret: str = Field(..., min_length=32)
    redis_url: str = "redis://localhost:6379/0"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    openrouter_api_key: str = "fake_key"
    openrouter_model: str = "google/gemini-2.5-flash"
    openrouter_embedding_model: str = "text-embedding-3-small"
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"
    aws_endpoint_url: str = "http://localhost:4566"
    s3_bucket_name: str = "nexus-documents"
    max_file_size_mb: int = 40
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("jwt_secret")
    @classmethod
    def _no_default_secret(cls, v: str) -> str:
        forbidden = {"jwt_secret", "secret", "test", "password", "123456", "changeme", "default"}
        if v.lower() in forbidden:
            raise ValueError("JWT_SECRET must be a strong, non-default value")
        return v


@lru_cache
def get_settings():
    return Settings()
