from datetime import UTC, datetime, timedelta

from opendq.quality.models import (
    IngestionVolume,
    Observation,
    QualityContext,
    QualityRuleDefinition,
    QualityStatus,
)
from opendq.quality.rules.completeness import evaluate_completeness
from opendq.quality.rules.freshness import evaluate_freshness
from opendq.quality.rules.gap import evaluate_timestamp_gap
from opendq.quality.rules.range import evaluate_range
from opendq.quality.rules.uniqueness import evaluate_uniqueness
from opendq.quality.rules.volume import evaluate_volume
from opendq.quality.scoring import calculate_quality_score

NOW = datetime(2026, 9, 6, 12, tzinfo=UTC)


def _rule(slug: str, rule_type: str, config: dict, *, severity: str = "HIGH"):
    return QualityRuleDefinition(
        id=1,
        dataset_id=7,
        slug=slug,
        name=slug.replace("-", " "),
        dimension=rule_type,
        rule_type=rule_type,
        severity=severity,
        config=config,
    )


def _context(observations: list[Observation], volumes=()) -> QualityContext:
    return QualityContext(
        dataset_id=7,
        dataset_slug="hourly-weather",
        observation_type="weather",
        evaluated_at=NOW,
        observations=tuple(observations),
        ingestion_volumes=tuple(volumes),
    )


def _observation(at: datetime, **fields) -> Observation:
    return Observation(observed_at=at, fields=fields, source_event_id=fields.get("event_id"))


def test_freshness_passes_when_latest_observation_is_within_threshold() -> None:
    result = evaluate_freshness(
        _context([_observation(NOW - timedelta(minutes=30))]),
        _rule("freshness", "freshness", {"max_age_minutes": 180}),
    )

    assert result.status is QualityStatus.PASS
    assert result.observed_value["observed_age_minutes"] == 30.0
    assert result.expected_value["maximum_age_minutes"] == 180


def test_freshness_fails_when_latest_observation_is_stale() -> None:
    result = evaluate_freshness(
        _context([_observation(NOW - timedelta(hours=4))]),
        _rule("freshness", "freshness", {"max_age_minutes": 180}),
    )

    assert result.status is QualityStatus.FAIL
    assert result.affected_records == 1


def test_completeness_fails_when_null_rate_exceeds_threshold() -> None:
    observations = [_observation(NOW, temperature_c=20.0), _observation(NOW, temperature_c=None)]

    result = evaluate_completeness(
        _context(observations),
        _rule(
            "temperature-completeness",
            "completeness",
            {"column": "temperature_c", "max_null_rate": 0.0},
        ),
    )

    assert result.status is QualityStatus.FAIL
    assert result.observed_value["null_records"] == 1
    assert result.observed_value["null_rate"] == 0.5


def test_uniqueness_fails_for_duplicate_logical_keys() -> None:
    observed_at = NOW - timedelta(hours=1)
    observations = [
        _observation(observed_at, latitude=1, longitude=2),
        _observation(observed_at, latitude=1, longitude=2),
    ]

    result = evaluate_uniqueness(
        _context(observations),
        _rule("logical-uniqueness", "uniqueness", {"key": "weather"}),
    )

    assert result.status is QualityStatus.FAIL
    assert result.affected_records == 1


def test_range_fails_for_values_outside_configured_bounds() -> None:
    observations = [
        _observation(NOW, relative_humidity_pct=40),
        _observation(NOW, relative_humidity_pct=120),
    ]

    result = evaluate_range(
        _context(observations),
        _rule(
            "humidity-range", "validity", {"column": "relative_humidity_pct", "min": 0, "max": 100}
        ),
    )

    assert result.status is QualityStatus.FAIL
    assert result.affected_records == 1
    assert result.expected_value == {"column": "relative_humidity_pct", "min": 0, "max": 100}


def test_timestamp_gap_fails_when_interval_exceeds_threshold() -> None:
    observations = [
        _observation(NOW - timedelta(hours=3)),
        _observation(NOW - timedelta(hours=2)),
        _observation(NOW),
    ]

    result = evaluate_timestamp_gap(
        _context(observations),
        _rule(
            "hourly-gaps",
            "timestamp_gap",
            {"expected_interval_minutes": 60, "maximum_allowed_gap_minutes": 60},
        ),
    )

    assert result.status is QualityStatus.FAIL
    assert result.observed_value["gap_count"] == 1
    assert result.observed_value["largest_gap_minutes"] == 120.0


def test_volume_skips_when_baseline_history_is_insufficient() -> None:
    volumes = [IngestionVolume(NOW, 24, 24, "SUCCESS")]

    result = evaluate_volume(
        _context([], volumes),
        _rule(
            "volume", "volume", {"minimum_baseline_runs": 5, "lower_ratio": 0.5, "upper_ratio": 2.0}
        ),
    )

    assert result.status is QualityStatus.SKIPPED
    assert result.details["reason"] == "INSUFFICIENT_BASELINE"


def test_volume_passes_against_a_stable_median_baseline() -> None:
    volumes = [
        IngestionVolume(NOW, 24, 24, "SUCCESS"),
        IngestionVolume(NOW - timedelta(hours=1), 24, 24, "SUCCESS"),
        IngestionVolume(NOW - timedelta(hours=2), 20, 20, "SUCCESS"),
        IngestionVolume(NOW - timedelta(hours=3), 30, 30, "SUCCESS"),
        IngestionVolume(NOW - timedelta(hours=4), 24, 24, "SUCCESS"),
        IngestionVolume(NOW - timedelta(hours=5), 26, 26, "SUCCESS"),
    ]

    result = evaluate_volume(
        _context([], volumes),
        _rule(
            "volume", "volume", {"minimum_baseline_runs": 5, "lower_ratio": 0.5, "upper_ratio": 2.0}
        ),
    )

    assert result.status is QualityStatus.PASS


def test_volume_fails_for_a_large_drop_against_baseline() -> None:
    volumes = [
        IngestionVolume(NOW, 2, 2, "SUCCESS"),
        IngestionVolume(NOW - timedelta(hours=1), 24, 24, "SUCCESS"),
        IngestionVolume(NOW - timedelta(hours=2), 20, 20, "SUCCESS"),
        IngestionVolume(NOW - timedelta(hours=3), 30, 30, "SUCCESS"),
        IngestionVolume(NOW - timedelta(hours=4), 24, 24, "SUCCESS"),
        IngestionVolume(NOW - timedelta(hours=5), 26, 26, "SUCCESS"),
    ]

    result = evaluate_volume(
        _context([], volumes),
        _rule(
            "volume", "volume", {"minimum_baseline_runs": 5, "lower_ratio": 0.5, "upper_ratio": 2.0}
        ),
    )

    assert result.status is QualityStatus.FAIL


def test_quality_score_is_transparent_and_excludes_skipped_and_error() -> None:
    results = [
        QualityStatus.PASS,
        QualityStatus.WARN,
        QualityStatus.FAIL,
        QualityStatus.SKIPPED,
        QualityStatus.ERROR,
    ]

    assert calculate_quality_score(results) == 50.0
