from datetime import UTC, datetime, timedelta

from opendq.quality.engine import evaluate_dataset
from opendq.quality.registry import RULE_EVALUATORS


def _seed_weather(repository) -> int:
    _, dataset_id = repository.ensure_source_dataset(
        source_slug="open-meteo",
        source_name="Open-Meteo",
        description="Fixture weather source",
        base_url="https://example.test/weather",
        dataset_slug="hourly-weather",
        dataset_name="Hourly weather",
        schema_version="1",
    )
    return dataset_id


def test_evaluation_persists_results_and_keeps_ingestion_health_separate(repository) -> None:
    dataset_id = _seed_weather(repository)
    run_id = repository.create_ingestion_run(1, dataset_id)
    now = datetime(2026, 9, 6, 12, tzinfo=UTC)
    records = [
        {
            "kind": "weather",
            "observed_at": now - timedelta(hours=1),
            "latitude": 13.7563,
            "longitude": 100.5018,
            "temperature_c": 25.0,
            "relative_humidity_pct": 50.0,
            "precipitation_mm": 0.0,
            "wind_speed_kmh": 10.0,
            "payload": {},
            "provenance": {},
        },
        {
            "kind": "weather",
            "observed_at": now,
            "latitude": 13.7563,
            "longitude": 100.5018,
            "temperature_c": 25.0,
            "relative_humidity_pct": 50.0,
            "precipitation_mm": 0.0,
            "wind_speed_kmh": 10.0,
            "payload": {},
            "provenance": {},
        },
    ]
    assert repository.upsert_observations(dataset_id, run_id, records) == 2
    repository.finish_ingestion_run(
        run_id,
        status="SUCCESS",
        records_received=2,
        records_written=2,
        records_rejected=0,
    )

    summary = evaluate_dataset(repository, "hourly-weather", evaluated_at=now)

    assert summary.status == "SUCCESS"
    assert summary.rules_evaluated >= 6
    assert summary.score is not None
    assert all(result.evaluated_at == now for result in summary.results)
    with repository.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT status, rules_evaluated, score, finished_at
            FROM quality_evaluation_runs WHERE evaluation_run_id = %s
            """,
            (summary.evaluation_run_id,),
        )
        run = cursor.fetchone()
        cursor.execute(
            "SELECT count(*) FROM quality_results WHERE evaluation_run_id = %s",
            (summary.evaluation_run_id,),
        )
        result_count = cursor.fetchone()[0]
    assert run[0] == "SUCCESS"
    assert run[1] == summary.rules_evaluated
    assert run[2] == summary.score
    assert run[3] is not None
    assert result_count == summary.rules_evaluated


def test_default_rules_are_seeded_idempotently(repository) -> None:
    dataset_id = _seed_weather(repository)

    first = repository.ensure_default_quality_rules(dataset_id, "hourly-weather")
    second = repository.ensure_default_quality_rules(dataset_id, "hourly-weather")

    assert len(first) == len(second)
    assert {rule.slug for rule in first} == {rule.slug for rule in second}


def test_unknown_dataset_evaluation_is_explicitly_empty(repository) -> None:
    _, dataset_id = repository.ensure_source_dataset(
        source_slug="fixture-source",
        source_name="Fixture source",
        description="Fixture",
        base_url="https://example.test",
        dataset_slug="fixture-dataset",
        dataset_name="Fixture dataset",
        schema_version="1",
    )

    summary = evaluate_dataset(repository, "fixture-dataset", evaluated_at=datetime.now(UTC))

    assert summary.status == "SUCCESS"
    assert summary.rules_evaluated == 0
    assert summary.score is None


def test_quality_fail_is_persisted_without_failing_evaluation_run(repository) -> None:
    dataset_id = _seed_weather(repository)
    run_id = repository.create_ingestion_run(1, dataset_id)
    now = datetime(2026, 9, 6, 12, tzinfo=UTC)
    record = {
        "kind": "weather",
        "observed_at": now,
        "latitude": 13.7563,
        "longitude": 100.5018,
        "temperature_c": 100.0,
        "relative_humidity_pct": 50.0,
        "precipitation_mm": 0.0,
        "wind_speed_kmh": 10.0,
        "payload": {},
        "provenance": {},
    }
    assert repository.upsert_observations(dataset_id, run_id, [record]) == 1
    repository.finish_ingestion_run(
        run_id,
        status="SUCCESS",
        records_received=1,
        records_written=1,
        records_rejected=0,
    )

    summary = evaluate_dataset(repository, "hourly-weather", evaluated_at=now)

    assert summary.status == "SUCCESS"
    assert summary.rules_failed >= 1
    assert any(result.status.value == "FAIL" for result in summary.results)


def test_rule_runtime_error_is_persisted_as_error(repository, monkeypatch) -> None:
    _seed_weather(repository)

    def fail(*args, **kwargs):
        raise RuntimeError("fixture rule failure")

    monkeypatch.setitem(RULE_EVALUATORS, "freshness", fail)
    summary = evaluate_dataset(
        repository,
        "hourly-weather",
        evaluated_at=datetime(2026, 9, 6, 12, tzinfo=UTC),
    )

    assert summary.status == "SUCCESS"
    assert summary.rules_errored == 1
    assert any(result.status.value == "ERROR" for result in summary.results)
