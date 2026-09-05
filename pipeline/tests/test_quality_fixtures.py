import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from opendq.quality.models import Observation, QualityContext, QualityRuleDefinition, QualityStatus
from opendq.quality.rules.completeness import evaluate_completeness
from opendq.quality.rules.gap import evaluate_timestamp_gap
from opendq.quality.rules.range import evaluate_range

FIXTURES = Path(__file__).parent / "fixtures" / "quality"
NOW = datetime(2026, 9, 6, 12, tzinfo=UTC)


def _context(filename: str, observation_type: str) -> QualityContext:
    rows = json.loads((FIXTURES / filename).read_text(encoding="utf-8"))
    observations = tuple(
        Observation(
            observed_at=datetime.fromisoformat(row["observed_at"].replace("Z", "+00:00")),
            fields=row["fields"],
            source_event_id=row["fields"].get("event_id"),
        )
        for row in rows
    )
    return QualityContext(7, "fixture", observation_type, NOW, observations)


def _rule(rule_type: str, config: dict):
    return QualityRuleDefinition(
        1, 7, "fixture", "Fixture", rule_type, rule_type, "HIGH", config=config
    )


@pytest.mark.parametrize(
    ("filename", "expected"),
    [("weather_good.json", QualityStatus.PASS), ("weather_invalid_range.json", QualityStatus.FAIL)],
)
def test_weather_range_fixture(filename: str, expected: QualityStatus) -> None:
    result = evaluate_range(
        _context(filename, "weather"),
        _rule("range", {"column": "relative_humidity_pct", "min": 0, "max": 100}),
    )

    assert result.status is expected


def test_weather_timestamp_gap_fixture() -> None:
    result = evaluate_timestamp_gap(
        _context("weather_timestamp_gap.json", "weather"),
        _rule(
            "timestamp_gap", {"expected_interval_minutes": 60, "maximum_allowed_gap_minutes": 90}
        ),
    )

    assert result.status is QualityStatus.FAIL
    assert result.observed_value["gap_count"] == 1


def test_weather_missing_value_fixture() -> None:
    result = evaluate_completeness(
        _context("weather_missing_values.json", "weather"),
        _rule("completeness", {"column": "temperature_c", "max_null_rate": 0.0}),
    )

    assert result.status is QualityStatus.FAIL


def test_earthquake_fixture_scenarios() -> None:
    good = evaluate_range(
        _context("earthquake_good.json", "earthquake"),
        _rule("range", {"column": "latitude", "min": -90, "max": 90}),
    )
    invalid = evaluate_range(
        _context("earthquake_invalid_coordinates.json", "earthquake"),
        _rule("range", {"column": "latitude", "min": -90, "max": 90}),
    )

    assert good.status is QualityStatus.PASS
    assert invalid.status is QualityStatus.FAIL
