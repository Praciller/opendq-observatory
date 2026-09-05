"""Open-Meteo forecast adapter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

import httpx
import polars as pl
from pydantic import ValidationError

from opendq.contracts.models import WeatherObservation
from opendq.errors import ErrorCode, IngestionError
from opendq.sources.base import NormalizationResult


class OpenMeteoAdapter:
    source_slug = "open-meteo"
    dataset_slug = "hourly-weather"
    source_name = "Open-Meteo"
    dataset_name = "Hourly weather"
    description = "Hourly public weather forecast for the Bangkok demo location."

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        base_url: str,
        latitude: float = 13.7563,
        longitude: float = 100.5018,
    ) -> None:
        self.client = client
        self.base_url = base_url
        self.latitude = latitude
        self.longitude = longitude

    async def fetch(self) -> dict[str, Any]:
        try:
            response = await self.client.get(
                self.base_url,
                params={
                    "latitude": self.latitude,
                    "longitude": self.longitude,
                    "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
                    "forecast_days": 1,
                    "timezone": "UTC",
                },
                timeout=10,
            )
        except httpx.TimeoutException as exc:
            raise IngestionError(ErrorCode.SOURCE_TIMEOUT, "Open-Meteo request timed out") from exc
        except httpx.HTTPError as exc:
            raise IngestionError(ErrorCode.SOURCE_UNAVAILABLE, "Open-Meteo request failed") from exc
        if response.is_error:
            raise IngestionError(ErrorCode.SOURCE_UNAVAILABLE, "Open-Meteo returned an error")
        try:
            payload = response.json()
        except ValueError as exc:
            raise IngestionError(
                ErrorCode.INVALID_RESPONSE, "Open-Meteo returned invalid JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise IngestionError(
                ErrorCode.INVALID_RESPONSE, "Open-Meteo response must be an object"
            )
        return payload

    def normalize(self, payload: Mapping[str, Any]) -> NormalizationResult:
        return self.normalize_payload(payload)

    @staticmethod
    def normalize_payload(payload: Mapping[str, Any]) -> NormalizationResult:
        hourly = payload.get("hourly")
        if not isinstance(hourly, Mapping):
            raise IngestionError(ErrorCode.INVALID_RESPONSE, "Open-Meteo hourly object is missing")
        names = (
            "time",
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "wind_speed_10m",
        )
        arrays = [hourly.get(name) for name in names]
        if any(not isinstance(values, list) for values in arrays):
            raise IngestionError(ErrorCode.INVALID_RESPONSE, "Open-Meteo hourly arrays are missing")
        typed_arrays = cast(list[list[Any]], arrays)
        if len({len(values) for values in typed_arrays}) != 1:
            raise IngestionError(
                ErrorCode.INVALID_RESPONSE, "Open-Meteo hourly arrays have different lengths"
            )
        latitude = payload.get("latitude")
        longitude = payload.get("longitude")
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            raise IngestionError(ErrorCode.INVALID_RESPONSE, "Open-Meteo coordinates are missing")

        frame = pl.DataFrame(dict(zip(names, typed_arrays, strict=True)))
        records: list[Mapping[str, Any]] = []
        rejected = 0
        for row in frame.iter_rows(named=True):
            try:
                observation = WeatherObservation(
                    observed_at=row["time"],
                    temperature_c=row["temperature_2m"],
                    relative_humidity_pct=row["relative_humidity_2m"],
                    precipitation_mm=row["precipitation"],
                    wind_speed_kmh=row["wind_speed_10m"],
                    latitude=latitude,
                    longitude=longitude,
                )
            except (ValidationError, ValueError, TypeError):
                rejected += 1
                continue
            records.append(
                {
                    "kind": "weather",
                    "observed_at": observation.observed_at,
                    "temperature_c": observation.temperature_c,
                    "relative_humidity_pct": observation.relative_humidity_pct,
                    "precipitation_mm": observation.precipitation_mm,
                    "wind_speed_kmh": observation.wind_speed_kmh,
                    "latitude": observation.latitude,
                    "longitude": observation.longitude,
                    "payload": {
                        "temperature_2m": observation.temperature_c,
                        "relative_humidity_2m": observation.relative_humidity_pct,
                        "precipitation": observation.precipitation_mm,
                        "wind_speed_10m": observation.wind_speed_kmh,
                    },
                    "provenance": {"adapter": "open-meteo", "timezone": "UTC"},
                }
            )
        return NormalizationResult(records=records, rejected=rejected)
