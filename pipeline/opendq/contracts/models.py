"""Canonical records shared by adapters and persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _utc_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        timestamp = value
    elif isinstance(value, str):
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError("timestamp must be an ISO-8601 string or datetime")
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC)


class WeatherObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observed_at: datetime
    temperature_c: float
    relative_humidity_pct: float = Field(ge=0, le=100)
    precipitation_mm: float = Field(ge=0)
    wind_speed_kmh: float = Field(ge=0)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    _normalize_timestamp = field_validator("observed_at", mode="before")(_utc_timestamp)


class EarthquakeObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    occurred_at: datetime
    magnitude: float = Field(ge=-2)
    place: str = Field(min_length=1)
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    depth_km: float = Field(ge=-10)
    source_url: str = Field(min_length=1)

    _normalize_timestamp = field_validator("occurred_at", mode="before")(_utc_timestamp)
