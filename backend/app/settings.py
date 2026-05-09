from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./finops_recommendations.db"
    cors_origins: str = "http://127.0.0.1:5174,http://localhost:5174"
    seed_on_startup: bool = True
    scheduler_enabled: bool = True
    catalog_path: str = Field(default="/app/config/recommendations/basic-recommendation-catalog-global.csv")
    provider_registry_path: str = Field(default="/app/config/provider_registry.yaml")
    schedules_path: str = Field(default="/app/config/schedules.yaml")
    product_catalog_seed_path: str = Field(default="/app/config/product_catalog_seed.csv")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def resolve_config_path(self, path_value: str) -> Path:
        path = Path(path_value)
        if path.exists():
            return path
        relative = path_value.removeprefix("/app/")
        repo_relative = Path(__file__).resolve().parents[2] / relative
        return repo_relative


@lru_cache
def get_settings() -> Settings:
    return Settings()
