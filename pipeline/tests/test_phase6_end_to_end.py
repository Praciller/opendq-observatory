from datetime import UTC, datetime, timedelta

from opendq.ai.models import AICopilotStatus
from opendq.ai.service import analyze_incident
from opendq.config import Settings
from opendq.drift.service import create_baselines
from opendq.drift.service import evaluate_dataset as evaluate_drift
from opendq.incidents.repository import IncidentRepository
from opendq.lineage.seed import seed_lineage
from opendq.quality.engine import evaluate_dataset as evaluate_quality
from opendq.rca.repository import RCARepository


def _write_weather(repository, source_id, dataset_id, start, temperatures, humidity=50.0):
    run_id = repository.create_ingestion_run(source_id, dataset_id)
    records = [
        {
            "kind": "weather",
            "observed_at": start + timedelta(hours=index),
            "temperature_c": temperature,
            "relative_humidity_pct": humidity,
            "precipitation_mm": 0.0,
            "wind_speed_kmh": 10.0,
            "latitude": 13.7563,
            "longitude": 100.5018,
            "payload": {"fixture": "phase6"},
            "provenance": {"fixture": True},
        }
        for index, temperature in enumerate(temperatures)
    ]
    written = repository.upsert_observations(dataset_id, run_id, records)
    repository.finish_ingestion_run(
        run_id,
        status="SUCCESS",
        records_received=len(records),
        records_written=written,
        records_rejected=len(records) - written,
    )


def test_deterministic_incident_flow_reaches_recovery(repository, monkeypatch) -> None:
    source_id, dataset_id = repository.ensure_source_dataset(
        source_slug="open-meteo",
        source_name="Open-Meteo fixture",
        description="Phase 6 end-to-end fixture",
        base_url="https://example.test/open-meteo",
        dataset_slug="hourly-weather",
        dataset_name="Hourly weather fixture",
        schema_version="1",
    )
    seed_lineage(repository.connection)
    base_start = datetime(2026, 1, 1, tzinfo=UTC)
    healthy = [25.0 + (index % 3) for index in range(100)]
    shifted = [45.0 + (index % 3) for index in range(100)]

    _write_weather(repository, source_id, dataset_id, base_start, healthy)
    healthy_quality = evaluate_quality(
        repository,
        "hourly-weather",
        triggered_by="test",
        evaluated_at=base_start + timedelta(hours=100),
    )
    assert healthy_quality.rules_failed == 0
    create_baselines(repository.connection, "hourly-weather")

    failure_start = base_start + timedelta(hours=101)
    _write_weather(repository, source_id, dataset_id, failure_start, shifted)
    failed_quality = evaluate_quality(
        repository,
        "hourly-weather",
        triggered_by="test",
        evaluated_at=base_start + timedelta(hours=200),
    )
    failed_drift = evaluate_drift(
        repository.connection,
        "hourly-weather",
        triggered_by="test",
        evaluated_at=base_start + timedelta(hours=200),
    )
    assert failed_quality.rules_failed == 1
    assert any(result.status.value == "DRIFT" for result in failed_drift.results)

    incidents = IncidentRepository(repository.connection)
    open_incidents = incidents.list_incidents(status="OPEN")
    quality_incident = next(
        item for item in open_incidents if item["incident_kind"] == "DATA_QUALITY"
    )
    assert any(item["incident_kind"] == "DATA_DRIFT" for item in open_incidents)
    detail = incidents.get_incident(quality_incident["id"])
    assert len(detail["impacts"]) == 3
    assert (
        RCARepository(repository.connection).latest(quality_incident["id"])["top_cause"]
        == "TIMESTAMP_GAP"
    )

    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("AI_COPILOT_ENABLED", "false")
    fallback = analyze_incident(
        repository.connection,
        quality_incident["id"],
        Settings.from_env(),
    )
    assert fallback.analysis.status is AICopilotStatus.FALLBACK
    assert fallback.analysis.deterministic_rca_analysis_id is not None

    _write_weather(repository, source_id, dataset_id, base_start + timedelta(hours=100), [25.0])
    _write_weather(repository, source_id, dataset_id, base_start + timedelta(hours=201), healthy)
    recovery_quality = evaluate_quality(
        repository,
        "hourly-weather",
        triggered_by="test",
        evaluated_at=base_start + timedelta(hours=301),
    )
    recovery_drift = evaluate_drift(
        repository.connection,
        "hourly-weather",
        triggered_by="test",
        evaluated_at=base_start + timedelta(hours=301),
    )

    assert recovery_quality.rules_failed == 0
    assert all(result.status.value in {"STABLE", "SKIPPED"} for result in recovery_drift.results)
    assert incidents.get_incident(quality_incident["id"])["status"] == "RESOLVED"
