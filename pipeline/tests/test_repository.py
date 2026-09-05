from datetime import UTC, datetime

import pytest


def _seed(repository) -> tuple[int, int]:
    return repository.ensure_source_dataset(
        source_slug="test-source",
        source_name="Test source",
        description="Fixture source",
        base_url="https://example.test",
        dataset_slug="test-dataset",
        dataset_name="Test dataset",
        schema_version="1",
    )


def test_repository_records_terminal_run(repository) -> None:
    source_id, dataset_id = _seed(repository)
    run_id = repository.create_ingestion_run(source_id, dataset_id)

    repository.finish_ingestion_run(
        run_id,
        status="SUCCESS",
        records_received=2,
        records_written=2,
        records_rejected=0,
    )

    with repository.connection.cursor() as cursor:
        cursor.execute(
            "SELECT status, records_received, finished_at FROM ingestion_runs WHERE run_id = %s",
            (run_id,),
        )
        row = cursor.fetchone()
    assert row == ("SUCCESS", 2, row[2])
    assert row[2] is not None


def test_repository_weather_upsert_is_idempotent(repository) -> None:
    source_id, dataset_id = _seed(repository)
    run_id = repository.create_ingestion_run(source_id, dataset_id)
    record = {
        "kind": "weather",
        "observed_at": datetime(2026, 9, 6, 0, tzinfo=UTC),
        "latitude": 13.7563,
        "longitude": 100.5018,
        "payload": {"temperature_2m": 29.0},
        "provenance": {"source": "fixture"},
    }

    assert repository.upsert_observations(dataset_id, run_id, [record]) == 1
    assert repository.upsert_observations(dataset_id, run_id, [record]) == 0


def test_repository_rejects_unknown_observation_kind(repository) -> None:
    source_id, dataset_id = _seed(repository)
    run_id = repository.create_ingestion_run(source_id, dataset_id)

    with pytest.raises(ValueError, match="kind"):
        repository.upsert_observations(dataset_id, run_id, [{"kind": "other"}])
