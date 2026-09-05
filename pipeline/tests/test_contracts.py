from datetime import UTC, datetime

import pytest
from opendq.contracts.models import EarthquakeObservation, WeatherObservation
from pydantic import ValidationError


def test_weather_contract_normalizes_naive_source_timestamp_to_utc() -> None:
    observation = WeatherObservation(
        observed_at="2026-09-06T00:00:00",
        temperature_c=28.1,
        relative_humidity_pct=82,
        precipitation_mm=0,
        wind_speed_kmh=8.4,
        latitude=13.7563,
        longitude=100.5018,
    )

    assert observation.observed_at == datetime(2026, 9, 6, tzinfo=UTC)


def test_contract_rejects_invalid_earthquake_magnitude() -> None:
    with pytest.raises(ValidationError):
        EarthquakeObservation(
            event_id="fixture",
            occurred_at="2026-09-06T00:00:00Z",
            magnitude="not-a-number",
            place="Example",
            longitude=-150,
            latitude=61,
            depth_km=12,
            source_url="https://example.test/event",
        )
