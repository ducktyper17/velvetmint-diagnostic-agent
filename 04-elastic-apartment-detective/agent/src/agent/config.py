"""Runtime settings for the Elastic Apartment Detective."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "dev", "demo", "prod"]


class Settings(BaseSettings):
    """Application configuration loaded from env vars or `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    port: int = 8080
    log_level: str = "INFO"
    environment: Environment = "local"
    agent_max_iterations: int = Field(default=10, ge=1, le=30)

    google_cloud_project: str
    google_cloud_location: str = "us-central1"
    google_application_credentials: str | None = None
    # The investigation is a tool-routing task, not a reasoning-heavy one, so
    # flash keeps per-turn latency low — which is what the renter feels after
    # pressing "Investigate". Override to gemini-2.5-pro via env for a deeper
    # narrative in a specific demo.
    vertex_model: str = "gemini-2.5-flash"
    # When true, the planner returns a deterministic tool sequence instead of
    # calling Gemini. Defaults to true so the app runs end-to-end with no GCP
    # credentials; set false once Vertex AI access is wired (see SETUP).
    stub_gemini_responses: bool = True

    elastic_mcp_url: HttpUrl
    elastic_mcp_api_key: SecretStr

    # When true, the Elastic tools return seeded sample payloads instead of
    # hitting the Agent Builder MCP endpoint. Independent of the Gemini stub so
    # you can run a real Gemini loop against sample data, or vice versa.
    demo_mode: bool = True
    default_city: str = "New York"
    default_state: str = "NY"
    default_zip: str = "10002"
    demo_listing_url: HttpUrl = "https://streeteasy.example/listing/123-orchard-st-new-york-ny-10002"
    demo_address: str = "123 Orchard St, New York, NY 10002"

    @property
    def is_demo(self) -> bool:
        """Return True when demo shortcuts should be used."""

        return self.demo_mode or self.environment == "demo"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()  # type: ignore[call-arg]
