"""
Application settings loaded from environment variables / .env file.

All values can be overridden via environment or a .env file in the project root.
"""

from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "postgresql+psycopg://finops:finops@db:5432/finops_recommendations"

    # ── AWS ───────────────────────────────────────────────────────────────────
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_default_region: str = "us-east-1"
    aws_role_arn: str = ""
    aws_external_id: str = ""

    # ── Azure ─────────────────────────────────────────────────────────────────
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""
    azure_subscription_id: str = ""

    # ── GCP ───────────────────────────────────────────────────────────────────
    gcp_project_id: str = ""
    gcp_service_account_json: str = ""          # inline JSON string or path
    gcp_bigquery_dataset: str = ""

    # ── AI Provider API keys (for direct spend polling) ───────────────────────
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    cohere_api_key: str = ""
    mistral_api_key: str = ""

    # ── Application ───────────────────────────────────────────────────────────
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "*"
    secret_key: str = "change-me-in-production"

    # ── File paths (relative to project root) ────────────────────────────────
    provider_registry_path: str = "config/provider_registry.yaml"
    catalog_path: str = "config/recommendations/basic-recommendation-catalog-global.csv"
    product_catalog_seed_path: str = "config/product_catalog_seed.csv"
    schedules_path: str = "config/schedules.yaml"

    # ── Scheduler ─────────────────────────────────────────────────────────────
    scheduler_enabled: bool = True
    cost_ingest_interval_minutes: int = 5
    focus_transform_interval_minutes: int = 60
    anomaly_detect_interval_minutes: int = 30
    forecast_interval_hours: int = 6

    def resolve_config_path(self, relative: str) -> Path:
        """Resolve a config path relative to the project root (two levels up from this file)."""
        return Path(__file__).parent.parent.parent / relative
