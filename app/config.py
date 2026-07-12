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
    openai_api_key: str = ""
    openai_planner_model: str = "gpt-5.4-mini"
    openai_evaluation_model: str = "gpt-5.4-mini"
    openai_orchestrator_model: str = "gpt-5.4-mini"
    openai_interview_model: str = "gpt-5.4-mini"
    openai_timeout_seconds: float = 30.0
    openai_max_retries: int = 2

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
