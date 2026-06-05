"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


Environment = Literal["local", "dev", "demo", "prod"]


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Service / runtime
    port: int = 8080
    log_level: str = "INFO"
    environment: Environment = "local"
    agent_max_iterations: int = Field(default=12, ge=1, le=50)

    # Google Cloud / Gemini
    google_cloud_project: str
    google_cloud_location: str = "us-central1"
    google_application_credentials: str | None = None
    # Flash is the loop default: the investigation is a tool-routing task, not a
    # reasoning-heavy one, and flash cuts per-turn latency ~2-3x — which is what
    # the operator feels after pressing "Investigate". Override to pro via env if
    # a deeper narrative is wanted for a specific demo.
    vertex_model: str = "gemini-2.5-flash"
    stub_gemini_responses: bool = False

    # Dynatrace
    dynatrace_environment_url: HttpUrl
    dynatrace_mcp_url: HttpUrl
    dynatrace_mcp_token: SecretStr
    dynatrace_default_notebook_name: str = "agent-reliability-guard"
    dynatrace_notification_channel: str = "#ai-platform-alerts"
    lookback_minutes_default: int = Field(default=120, ge=5, le=1440)
    # Davis analyzer display names are tenant-dependent. The defaults below match
    # the canonical names from the Dynatrace AI Observability sample tenant. Before
    # running against a live tenant, verify the names by calling `list_davis_analyzers`
    # via the MCP server, or check the Davis analyzer registry in the Dynatrace UI
    # under Settings > Davis > Analyzers. Override via env vars
    # DYNATRACE_CHANGE_ANALYZER_NAME and DYNATRACE_FORECAST_ANALYZER_NAME if your
    # tenant exposes them under different display names (e.g. "dt.statistics.changepoint").
    dynatrace_change_analyzer_name: str = "Changepoint Agent"
    dynatrace_forecast_analyzer_name: str = "Forecasting Agent"
    stub_dynatrace_tools: bool = False

    # Demo mode
    demo_mode: bool = False
    demo_service_name: str = "refund-assistant"
    demo_release_id: str = "release-2026-05-26-bad-prompt"

    @property
    def is_demo(self) -> bool:
        """Return True when deterministic demo shortcuts should be used."""

        return self.demo_mode or self.environment == "demo"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""

    return Settings()  # type: ignore[call-arg]
