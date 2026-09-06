from datetime import UTC, datetime, timedelta

from opendq.drift.repository import DriftRepository
from opendq.drift.service import create_baselines, evaluate_dataset
from opendq.incidents.repository import IncidentRepository
from opendq.lineage.seed import seed_lineage
from opendq.rca.repository import RCARepository
from psycopg.types.json import Jsonb


def _seed_weather(repository):
    source_id, dataset_id = repository.ensure_source_dataset(
        source_slug="open-meteo",
        source_name="Open-Meteo",
        description="Fixture source",
        base_url="https://example.test",
        dataset_slug="hourly-weather",
        dataset_name="Hourly weather",
        schema_version="1",
    )
    return source_id, dataset_id


def _write_weather(repository, source_id, dataset_id, start, temperatures):
    run_id = repository.create_ingestion_run(source_id, dataset_id)
    records = [
        {
            "kind": "weather",
            "observed_at": start + timedelta(hours=index),
            "temperature_c": temperature,
            "relative_humidity_pct": 50.0,
            "precipitation_mm": 0.0,
            "wind_speed_kmh": 10.0,
            "latitude": 13.7563,
            "longitude": 100.5018,
            "payload": {},
            "provenance": {"fixture": True},
        }
        for index, temperature in enumerate(temperatures)
    ]
    assert repository.upsert_observations(dataset_id, run_id, records) == len(records)
    repository.finish_ingestion_run(
        run_id,
        status="SUCCESS",
        records_received=len(records),
        records_written=len(records),
        records_rejected=0,
    )


def test_baseline_versioning_is_immutable_and_numeric_drift_opens_rca(repository) -> None:
    source_id, dataset_id = _seed_weather(repository)
    baseline_start = datetime(2026, 1, 1, tzinfo=UTC)
    _write_weather(repository, source_id, dataset_id, baseline_start, list(range(100)))

    first = create_baselines(repository.connection, "hourly-weather")
    second = create_baselines(repository.connection, "hourly-weather")
    assert {item["status"] for item in first} == {"BASELINE_CREATED"}
    assert {item["status"] for item in second} == {"BASELINE_CREATED"}
    baselines = DriftRepository(repository.connection).active_baselines(dataset_id)
    assert all(item["baseline_version"] == 2 for item in baselines)

    seed_lineage(repository.connection)
    _write_weather(
        repository,
        source_id,
        dataset_id,
        baseline_start + timedelta(days=5),
        list(range(9, 109)),
    )
    summary = evaluate_dataset(
        repository.connection, "hourly-weather", evaluated_at=datetime(2026, 2, 1, tzinfo=UTC)
    )

    assert summary.status == "SUCCESS"
    assert any(result.status.value == "DRIFT" for result in summary.results)
    incidents = IncidentRepository(repository.connection).list_incidents(status="OPEN")
    assert len(incidents) == 1
    assert incidents[0]["incident_kind"] == "DATA_DRIFT"
    analysis = RCARepository(repository.connection).latest(incidents[0]["id"])
    assert analysis is not None
    assert analysis["top_cause"] == "DISTRIBUTION_SHIFT"
    assert analysis["algorithm_version"] == "deterministic-rca-v1"


def test_stable_latest_window_resolves_drift_incident(repository) -> None:
    source_id, dataset_id = _seed_weather(repository)
    start = datetime(2026, 1, 1, tzinfo=UTC)
    _write_weather(repository, source_id, dataset_id, start, list(range(100)))
    create_baselines(repository.connection, "hourly-weather")
    seed_lineage(repository.connection)
    _write_weather(
        repository, source_id, dataset_id, start + timedelta(days=5), list(range(9, 109))
    )
    evaluate_dataset(repository.connection, "hourly-weather")
    _write_weather(repository, source_id, dataset_id, start + timedelta(days=10), list(range(100)))
    evaluate_dataset(repository.connection, "hourly-weather")

    rows = IncidentRepository(repository.connection).list_incidents()
    assert rows
    assert rows[0]["status"] == "RESOLVED"


def test_schema_drift_is_separate_and_reports_insufficient_numeric_baselines(repository) -> None:
    _, dataset_id = _seed_weather(repository)
    create_baselines(repository.connection, "hourly-weather")
    with repository.connection.transaction():
        with repository.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO dataset_versions(dataset_id, version, schema_hash, schema_json)
                VALUES (%s, '2', 'fixture-schema-v2', %s)
                """,
                (
                    dataset_id,
                    Jsonb(
                        {
                            "observed_at": {"type": "timestamp", "nullable": False},
                            "temperature_c": {"type": "string", "nullable": False},
                            "relative_humidity_pct": {"type": "number", "nullable": False},
                            "precipitation_mm": {"type": "number", "nullable": False},
                            "wind_speed_kmh": {"type": "number", "nullable": False},
                            "latitude": {"type": "number", "nullable": False},
                            "longitude": {"type": "number", "nullable": False},
                            "new_field": {"type": "boolean", "nullable": True},
                        }
                    ),
                ),
            )

    summary = evaluate_dataset(repository.connection, "hourly-weather")

    schema_result = next(result for result in summary.results if result.method == "SCHEMA_DIFF")
    assert schema_result.status.value == "DRIFT"
    assert {item["kind"] for item in schema_result.details["differences"]} == {
        "TYPE_CHANGED",
        "ADDED",
    }
    assert summary.status == "PARTIAL"
    assert summary.checks_skipped == 4
