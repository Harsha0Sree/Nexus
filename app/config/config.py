from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    test_database_url: str = ""
    jwt_secret: str
    openrouter_api_key: str = "fake_key"
    openrouter_model: str = "google/gemini-2.5-flash"
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"
    aws_endpoint_url: str = "http://localhost:4566"
    s3_bucket_name: str = "nexus-documents"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings():
    return Settings()
