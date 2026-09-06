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
    ai_copilot_enabled: bool
    ai_allowed_data_classification: str
    groq_api_key: str
    groq_model: str
    gemini_api_key: str
    gemini_model: str
    ai_timeout_seconds: float
    ai_max_input_tokens: int
    ai_max_output_tokens: int
    ai_max_calls_per_run: int
    ai_max_calls_per_incident: int

    @classmethod
    def from_env(cls) -> Settings:
        database_url = os.getenv("DATABASE_URL", "").strip()
        if not database_url:
            raise ValueError("DATABASE_URL is required")
        allowed_data_classification = (
            os.getenv("AI_ALLOWED_DATA_CLASSIFICATION", "PUBLIC_ONLY").strip().upper()
        )
        if allowed_data_classification != "PUBLIC_ONLY":
            raise ValueError("AI_ALLOWED_DATA_CLASSIFICATION must be PUBLIC_ONLY")
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
            ai_copilot_enabled=os.getenv("AI_COPILOT_ENABLED", "false").strip().lower()
            in {"1", "true", "yes", "on"},
            ai_allowed_data_classification=allowed_data_classification,
            groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
            groq_model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip(),
            gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip(),
            ai_timeout_seconds=max(1.0, min(float(os.getenv("AI_TIMEOUT_SECONDS", "8")), 30.0)),
            ai_max_input_tokens=max(500, min(int(os.getenv("AI_MAX_INPUT_TOKENS", "3000")), 6000)),
            ai_max_output_tokens=max(200, min(int(os.getenv("AI_MAX_OUTPUT_TOKENS", "700")), 1500)),
            ai_max_calls_per_run=max(0, min(int(os.getenv("AI_MAX_CALLS_PER_RUN", "3")), 5)),
            ai_max_calls_per_incident=max(
                1, min(int(os.getenv("AI_MAX_CALLS_PER_INCIDENT", "1")), 2)
            ),
        )
