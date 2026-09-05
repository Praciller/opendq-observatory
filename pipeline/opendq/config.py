"""Environment-backed application settings."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    app_env: str
    log_level: str
    open_meteo_base_url: str
    usgs_base_url: str

    @classmethod
    def from_env(cls) -> Settings:
        database_url = os.getenv("DATABASE_URL", "").strip()
        if not database_url:
            raise ValueError("DATABASE_URL is required")
        return cls(
            database_url=database_url,
            app_env=os.getenv("APP_ENV", "development"),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            open_meteo_base_url=os.getenv(
                "OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast"
            ),
            usgs_base_url=os.getenv(
                "USGS_BASE_URL",
                "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
            ),
        )
