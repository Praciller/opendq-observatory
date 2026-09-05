"""USGS GeoJSON earthquake feed adapter."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import ValidationError

from opendq.contracts.models import EarthquakeObservation
from opendq.errors import ErrorCode, IngestionError
from opendq.sources.base import NormalizationResult


class USGSAdapter:
    source_slug = "usgs-earthquakes"
    dataset_slug = "earthquake-events"
    source_name = "USGS Earthquakes"
    dataset_name = "Earthquake events"
    description = "USGS official GeoJSON summary earthquake feed."

    def __init__(self, *, client: httpx.AsyncClient, base_url: str) -> None:
        self.client = client
        self.base_url = base_url

    async def fetch(self) -> dict[str, Any]:
        try:
            response = await self.client.get(self.base_url, timeout=10)
        except httpx.TimeoutException as exc:
            raise IngestionError(ErrorCode.SOURCE_TIMEOUT, "USGS request timed out") from exc
        except httpx.HTTPError as exc:
            raise IngestionError(ErrorCode.SOURCE_UNAVAILABLE, "USGS request failed") from exc
        if response.is_error:
            raise IngestionError(ErrorCode.SOURCE_UNAVAILABLE, "USGS returned an error")
        try:
            payload = response.json()
        except ValueError as exc:
            raise IngestionError(ErrorCode.INVALID_RESPONSE, "USGS returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise IngestionError(ErrorCode.INVALID_RESPONSE, "USGS response must be an object")
        return payload

    def normalize(self, payload: Mapping[str, Any]) -> NormalizationResult:
        return self.normalize_payload(payload)

    @staticmethod
    def normalize_payload(payload: Mapping[str, Any]) -> NormalizationResult:
        features = payload.get("features")
        if not isinstance(features, list):
            raise IngestionError(ErrorCode.INVALID_RESPONSE, "USGS features array is missing")
        records: list[Mapping[str, Any]] = []
        rejected = 0
        for feature in features:
            try:
                if not isinstance(feature, Mapping):
                    raise ValueError("feature is not an object")
                properties = feature["properties"]
                coordinates = feature["geometry"]["coordinates"]
                if not isinstance(properties, Mapping) or not isinstance(coordinates, list):
                    raise ValueError("feature fields are malformed")
                occurred_at = datetime.fromtimestamp(properties["time"] / 1000, tz=UTC)
                observation = EarthquakeObservation(
                    event_id=feature["id"],
                    occurred_at=occurred_at,
                    magnitude=properties["mag"],
                    place=properties["place"],
                    longitude=coordinates[0],
                    latitude=coordinates[1],
                    depth_km=coordinates[2],
                    source_url=properties["url"],
                )
            except (KeyError, IndexError, TypeError, ValueError, ValidationError, OverflowError):
                rejected += 1
                continue
            records.append(
                {
                    "kind": "earthquake",
                    "event_id": observation.event_id,
                    "observed_at": observation.occurred_at,
                    "magnitude": observation.magnitude,
                    "place": observation.place,
                    "latitude": observation.latitude,
                    "longitude": observation.longitude,
                    "depth_km": observation.depth_km,
                    "source_url": observation.source_url,
                    "payload": {
                        "magnitude": observation.magnitude,
                        "place": observation.place,
                        "depth_km": observation.depth_km,
                    },
                    "provenance": {"adapter": "usgs", "event_id": observation.event_id},
                }
            )
        return NormalizationResult(records=records, rejected=rejected)
