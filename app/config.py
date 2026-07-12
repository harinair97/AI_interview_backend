from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env."""

    app_name: str = "Hybrid AI Interview Orchestrator"
    app_env: Literal["development", "test", "production"] = "development"
    app_debug: bool = False
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:55432/interviews"
    llm_provider: str = "openai"
    llm_model: str = ""
    llm_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
