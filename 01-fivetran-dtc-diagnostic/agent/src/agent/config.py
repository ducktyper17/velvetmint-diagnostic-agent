"""Runtime configuration loaded from environment variables.

Uses pydantic-settings so the same code path works in three contexts:

1. Local development from a ``.env`` file.
2. Cloud Run, where env vars are injected by the platform.
3. Tests, which pass overrides via the constructor.

The settings object is cached by :func:`get_settings` so that
:class:`Settings()` is only instantiated once per process — important because
the constructor reads files and contacts Secret Manager indirectly via
service-account credential discovery.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


Environment = Literal["local", "dev", "demo", "prod"]


class Settings(BaseSettings):
    """Application configuration.

    Attribute names match ``.env.example``. Anything secret is wrapped in
    :class:`SecretStr` so it does not leak into logs or tracebacks.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ----- Service / runtime ------------------------------------------------

    port: int = 8080
    log_level: str = "INFO"
    environment: Environment = "local"
    agent_max_iterations: int = Field(default=25, ge=1, le=100)

    # ----- Google Cloud / Vertex AI -----------------------------------------

    google_cloud_project: str
    google_cloud_location: str = "us-central1"
    # Optional because Cloud Run uses workload identity; set this only locally.
    google_application_credentials: str | None = None
    vertex_model: str = "gemini-3.0-pro"

    # ----- BigQuery ---------------------------------------------------------

    bigquery_dataset: str = "fivetran_velvetmint"
    bigquery_location: str | None = None

    # ----- Fivetran MCP -----------------------------------------------------

    fivetran_mcp_url: HttpUrl
    fivetran_mcp_token: SecretStr
    fivetran_allow_writes: bool = True

    # ----- MongoDB Atlas ----------------------------------------------------

    mongodb_uri: SecretStr
    mongodb_db: str = "dtc_diagnostic"

    # ----- Demo mode --------------------------------------------------------

    demo_mode: bool = False
    demo_brand_id: str = "velvetmint"

    # Convenience derived properties ----------------------------------------

    @property
    def is_demo(self) -> bool:
        """True when the agent should take the demo-mode shortcuts.

        Decoupled from ``environment`` so we can run the polished demo from a
        production-tier deployment when recording the video.
        """
        return self.demo_mode or self.environment == "demo"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance.

    FastAPI dependency-injects this so handlers do not re-parse env vars.
    """
    return Settings()  # type: ignore[call-arg]
