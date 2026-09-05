"""Version-one rule definitions for the two production datasets."""

from __future__ import annotations

from typing import Any

_DEFAULTS: dict[str, tuple[dict[str, Any], ...]] = {
    "hourly-weather": (
        {
            "slug": "freshness",
            "name": "Latest observation freshness",
            "dimension": "freshness",
            "rule_type": "freshness",
            "severity": "HIGH",
            "config": {"max_age_minutes": 180},
        },
        {
            "slug": "temperature-completeness",
            "name": "Temperature completeness",
            "dimension": "completeness",
            "rule_type": "completeness",
            "severity": "WARNING",
            "config": {"column": "temperature_c", "max_null_rate": 0.0},
        },
        {
            "slug": "temperature-range",
            "name": "Temperature validity range",
            "dimension": "validity",
            "rule_type": "range",
            "severity": "HIGH",
            "config": {"column": "temperature_c", "min": -90, "max": 60},
        },
        {
            "slug": "humidity-range",
            "name": "Relative humidity range",
            "dimension": "validity",
            "rule_type": "range",
            "severity": "HIGH",
            "config": {"column": "relative_humidity_pct", "min": 0, "max": 100},
        },
        {
            "slug": "precipitation-nonnegative",
            "name": "Precipitation is non-negative",
            "dimension": "validity",
            "rule_type": "range",
            "severity": "HIGH",
            "config": {"column": "precipitation_mm", "min": 0},
        },
        {
            "slug": "timestamp-continuity",
            "name": "Hourly timestamp continuity",
            "dimension": "timestamp_gap",
            "rule_type": "timestamp_gap",
            "severity": "WARNING",
            "config": {"expected_interval_minutes": 60, "maximum_allowed_gap_minutes": 90},
        },
        {
            "slug": "logical-uniqueness",
            "name": "Logical observation uniqueness",
            "dimension": "uniqueness",
            "rule_type": "uniqueness",
            "severity": "CRITICAL",
            "config": {"key": "weather"},
        },
        {
            "slug": "volume-anomaly",
            "name": "Ingestion volume baseline",
            "dimension": "volume",
            "rule_type": "volume",
            "severity": "WARNING",
            "config": {"minimum_baseline_runs": 5, "lower_ratio": 0.5, "upper_ratio": 2.0},
        },
    ),
    "earthquake-events": (
        {
            "slug": "freshness",
            "name": "Latest event freshness",
            "dimension": "freshness",
            "rule_type": "freshness",
            "severity": "HIGH",
            "config": {"max_age_minutes": 1440},
        },
        {
            "slug": "event-id-completeness",
            "name": "Event identifier completeness",
            "dimension": "completeness",
            "rule_type": "completeness",
            "severity": "CRITICAL",
            "config": {"column": "event_id", "max_null_rate": 0.0},
        },
        {
            "slug": "event-id-uniqueness",
            "name": "Event identifier uniqueness",
            "dimension": "uniqueness",
            "rule_type": "uniqueness",
            "severity": "CRITICAL",
            "config": {"key": "earthquake"},
        },
        {
            "slug": "magnitude-range",
            "name": "Magnitude sanity range",
            "dimension": "validity",
            "rule_type": "range",
            "severity": "HIGH",
            "config": {"column": "magnitude", "min": -2, "max": 10},
        },
        {
            "slug": "latitude-range",
            "name": "Latitude range",
            "dimension": "validity",
            "rule_type": "range",
            "severity": "HIGH",
            "config": {"column": "latitude", "min": -90, "max": 90},
        },
        {
            "slug": "longitude-range",
            "name": "Longitude range",
            "dimension": "validity",
            "rule_type": "range",
            "severity": "HIGH",
            "config": {"column": "longitude", "min": -180, "max": 180},
        },
        {
            "slug": "depth-range",
            "name": "Depth sanity range",
            "dimension": "validity",
            "rule_type": "range",
            "severity": "HIGH",
            "config": {"column": "depth_km", "min": -10, "max": 1000},
        },
        {
            "slug": "volume-anomaly",
            "name": "Ingestion volume baseline",
            "dimension": "volume",
            "rule_type": "volume",
            "severity": "WARNING",
            "config": {"minimum_baseline_runs": 5, "lower_ratio": 0.5, "upper_ratio": 2.0},
        },
    ),
}


def default_rules_for_dataset(dataset_slug: str) -> tuple[dict[str, Any], ...]:
    return tuple(
        dict(rule, config=dict(rule["config"])) for rule in _DEFAULTS.get(dataset_slug, ())
    )
