"""Explicit, small drift method registry; no executable configuration is stored in SQL."""

from __future__ import annotations

from opendq.drift.models import DriftFeature

SCHEMA_COLUMN = "__schema__"

DRIFT_FEATURES: tuple[DriftFeature, ...] = (
    DriftFeature("hourly-weather", "temperature_c", "PSI", 0.20, "WARNING"),
    DriftFeature("hourly-weather", "relative_humidity_pct", "PSI", 0.20, "WARNING"),
    DriftFeature("hourly-weather", "precipitation_mm", "PSI", 0.20, "WARNING"),
    DriftFeature("hourly-weather", "wind_speed_kmh", "PSI", 0.20, "WARNING"),
    DriftFeature("earthquake-events", "magnitude", "PSI", 0.30, "WARNING"),
    DriftFeature("earthquake-events", "depth_km", "PSI", 0.30, "WARNING"),
    DriftFeature("hourly-weather", SCHEMA_COLUMN, "SCHEMA_DIFF", 0.0, "HIGH"),
    DriftFeature("earthquake-events", SCHEMA_COLUMN, "SCHEMA_DIFF", 0.0, "HIGH"),
)


def features_for_dataset(dataset_slug: str) -> tuple[DriftFeature, ...]:
    return tuple(feature for feature in DRIFT_FEATURES if feature.dataset_slug == dataset_slug)


def feature_for(dataset_slug: str, column_name: str, method: str) -> DriftFeature:
    for feature in features_for_dataset(dataset_slug):
        if feature.column_name == column_name and feature.method == method:
            return feature
    raise ValueError(f"unsupported drift feature: {dataset_slug}:{column_name}:{method}")


def canonical_schema(dataset_slug: str) -> dict[str, dict[str, object]]:
    if dataset_slug == "hourly-weather":
        return {
            "observed_at": {"type": "timestamp", "nullable": False},
            "temperature_c": {"type": "number", "nullable": False},
            "relative_humidity_pct": {"type": "number", "nullable": False},
            "precipitation_mm": {"type": "number", "nullable": False},
            "wind_speed_kmh": {"type": "number", "nullable": False},
            "latitude": {"type": "number", "nullable": False},
            "longitude": {"type": "number", "nullable": False},
        }
    if dataset_slug == "earthquake-events":
        return {
            "observed_at": {"type": "timestamp", "nullable": False},
            "event_id": {"type": "string", "nullable": False},
            "magnitude": {"type": "number", "nullable": False},
            "depth_km": {"type": "number", "nullable": False},
            "place": {"type": "string", "nullable": False},
            "latitude": {"type": "number", "nullable": False},
            "longitude": {"type": "number", "nullable": False},
        }
    raise ValueError(f"unsupported dataset schema: {dataset_slug}")
