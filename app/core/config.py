from __future__ import annotations

from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    All settings can be overridden via environment variables or a local .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["dev", "prod", "test"] = Field(default="dev", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    request_timeout_s: float = Field(default=12.0, alias="REQUEST_TIMEOUT_S")

    # CrewAI / LLM
    model: str = Field(default="openai/gpt-4o-mini", alias="MODEL")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    # Some models/providers don't support custom temperatures. If unset, we don't
    # send a temperature parameter and let the provider default apply.
    temperature: Optional[float] = Field(default=None, alias="TEMPERATURE")
    crewai_verbose: bool = Field(default=False, alias="CREWAI_VERBOSE")

    # If no API key is set, the app will automatically fall back to rule-based planning.


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
