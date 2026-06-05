"""Runtime configuration for the Blast Radius backend."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


Environment = Literal["local", "dev", "demo", "prod"]


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    port: int = 8080
    log_level: str = "INFO"
    environment: Environment = "local"
    demo_mode: bool = True
    use_gemini_summary: bool = True
    agent_max_iterations: int = Field(default=20, ge=1, le=50)

    google_cloud_project: str = "REPLACE_ME_GCP_PROJECT"
    google_cloud_location: str = "us-central1"
    vertex_model: str = "gemini-2.5-pro"

    gitlab_base_url: HttpUrl = "https://gitlab.com"
    gitlab_group_path: str = "rapid-agent-labs"
    gitlab_mcp_url: HttpUrl = "https://gitlab.com/api/v4/mcp"
    gitlab_mcp_token: SecretStr = SecretStr("REPLACE_ME_GITLAB_TOKEN")
    gitlab_allow_writes: bool = True

    auto_deploy_max_risk: int = Field(default=74, ge=1, le=100)
    demo_cloud_run_region: str = "us-central1"

    @property
    def is_demo(self) -> bool:
        return self.demo_mode or self.environment == "demo"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings object."""

    return Settings()
