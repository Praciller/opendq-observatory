"""Guarded local incident demo orchestration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import psycopg

from opendq.ai.service import analyze_incident as analyze_ai_incident
from opendq.config import Settings
from opendq.drift.service import create_baselines
from opendq.drift.service import evaluate_dataset as evaluate_drift
from opendq.failure_scenarios import ScenarioEvidence, run_scenario
from opendq.incidents.repository import IncidentRepository
from opendq.lineage.seed import seed_lineage
from opendq.quality.engine import evaluate_dataset as evaluate_quality
from opendq.rca.repository import RCARepository
from opendq.storage.migrations import apply_migrations
from opendq.storage.repository import Repository


@dataclass(frozen=True, slots=True)
class DemoTimeline:
    baseline_start: datetime
    failure_start: datetime
    failure_evaluated_at: datetime
    repair_gap: datetime
    recovery_start: datetime
    recovery_evaluated_at: datetime


def demo_timeline(now: datetime) -> DemoTimeline:
    now = now.astimezone(UTC)
    return DemoTimeline(
        baseline_start=now - timedelta(hours=100),
        failure_start=now + timedelta(hours=1),
        failure_evaluated_at=now + timedelta(hours=100),
        repair_gap=now,
        recovery_start=now + timedelta(hours=101),
        recovery_evaluated_at=now + timedelta(hours=200),
    )


def validate_demo_environment(
    *, app_env: str, demo_database_url: str | None, production_database_url: str | None
) -> str:
    """Return a safe demo URL or refuse to run against an unsafe target."""
    if app_env.lower() not in {"demo", "test"}:
        raise ValueError("demo command requires APP_ENV=demo or APP_ENV=test")
    if not demo_database_url:
        raise ValueError("demo command requires DEMO_DATABASE_URL")
    if production_database_url and demo_database_url == production_database_url:
        raise ValueError("demo database must not equal DATABASE_URL")
    parsed = urlparse(demo_database_url)
    if parsed.scheme not in {"postgres", "postgresql"} or parsed.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise ValueError("demo database must be a local PostgreSQL URL")
    return demo_database_url


def _reset_demo_database(connection: psycopg.Connection[object]) -> None:
    with connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA public CASCADE")
        cursor.execute("CREATE SCHEMA public")
    connection.commit()
    apply_migrations(connection)


def _write_weather(
    repository: Repository,
    source_id: int,
    dataset_id: int,
    start: datetime,
    temperatures: list[float],
    *,
    humidity: float,
) -> None:
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
            "payload": {"demo": True},
            "provenance": {"fixture": "phase6-demo"},
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


def run_incident_demo(
    demo_database_url: str, production_database_url: str | None = None
) -> dict[str, object]:
    """Run the complete incident narrative against a guarded local database."""
    validate_demo_environment(
        app_env=os.getenv("APP_ENV", ""),
        demo_database_url=demo_database_url,
        production_database_url=production_database_url,
    )
    previous_database_url = os.environ.get("DATABASE_URL")
    previous_ai_enabled = os.environ.get("AI_COPILOT_ENABLED")
    os.environ["DATABASE_URL"] = demo_database_url
    os.environ["AI_COPILOT_ENABLED"] = "false"
    settings = Settings.from_env()
    evidence: list[ScenarioEvidence] = []
    try:
        with psycopg.connect(demo_database_url) as connection:
            _reset_demo_database(connection)
            repository = Repository(connection)
            source_id, dataset_id = repository.ensure_source_dataset(
                source_slug="open-meteo",
                source_name="Open-Meteo fixture",
                description="Phase 6 local incident demo",
                base_url="https://example.test/open-meteo",
                dataset_slug="hourly-weather",
                dataset_name="Hourly weather demo",
                schema_version="1",
            )
            seed_lineage(connection)
            timeline = demo_timeline(datetime.now(UTC).replace(minute=0, second=0, microsecond=0))
            healthy = [25.0 + (index % 3) for index in range(100)]
            shifted = [45.0 + (index % 3) for index in range(100)]
            _write_weather(
                repository,
                source_id,
                dataset_id,
                timeline.baseline_start,
                healthy,
                humidity=50.0,
            )
            healthy_quality = evaluate_quality(
                repository,
                "hourly-weather",
                triggered_by="demo",
                evaluated_at=timeline.baseline_start + timedelta(hours=100),
            )
            create_baselines(connection, "hourly-weather")

            _write_weather(
                repository,
                source_id,
                dataset_id,
                timeline.failure_start,
                shifted,
                humidity=50.0,
            )
            failed_quality = evaluate_quality(
                repository,
                "hourly-weather",
                triggered_by="demo",
                evaluated_at=timeline.failure_evaluated_at,
            )
            drift = evaluate_drift(
                connection,
                "hourly-weather",
                triggered_by="demo",
                evaluated_at=timeline.failure_evaluated_at,
            )
            incidents = IncidentRepository(connection)
            open_incidents = incidents.list_incidents(status="OPEN")
            selected = next(
                (item for item in open_incidents if item["incident_kind"] == "DATA_QUALITY"),
                open_incidents[0],
            )
            rca = RCARepository(connection).latest(selected["id"])
            ai = analyze_ai_incident(connection, selected["id"], settings)

            _write_weather(
                repository,
                source_id,
                dataset_id,
                timeline.repair_gap,
                [25.0],
                humidity=50.0,
            )
            _write_weather(
                repository,
                source_id,
                dataset_id,
                timeline.recovery_start,
                healthy,
                humidity=50.0,
            )
            recovery_quality = evaluate_quality(
                repository,
                "hourly-weather",
                triggered_by="demo",
                evaluated_at=timeline.recovery_evaluated_at,
            )
            recovery_drift = evaluate_drift(
                connection,
                "hourly-weather",
                triggered_by="demo",
                evaluated_at=timeline.recovery_evaluated_at,
            )
            final_incident = incidents.get_incident(selected["id"])

            evidence.extend(
                [
                    run_scenario(
                        "quality_failure",
                        lambda: "FAIL" if failed_quality.rules_failed > 0 else "PASS",
                    ),
                    run_scenario(
                        "drift_incident_open",
                        lambda: (
                            "OPEN"
                            if any(item["incident_kind"] == "DATA_DRIFT" for item in open_incidents)
                            else "CLOSED"
                        ),
                    ),
                    run_scenario(
                        "ai_all_providers_failure",
                        lambda: "FALLBACK" if ai.fallback_used else "SUCCESS",
                    ),
                    run_scenario(
                        "incident_resolution",
                        lambda: (
                            "RESOLVED"
                            if final_incident and final_incident["status"] == "RESOLVED"
                            else "OPEN"
                        ),
                    ),
                ]
            )
            return {
                "databaseScope": "local-demo-only",
                "healthy": {
                    "qualityStatus": healthy_quality.status,
                    "qualityFailedRules": healthy_quality.rules_failed,
                },
                "failure": {
                    "qualityStatus": failed_quality.status,
                    "qualityFailedRules": failed_quality.rules_failed,
                    "driftStatus": drift.status,
                },
                "incidentId": selected["id"],
                "blastRadiusCount": len(incidents.get_incident(selected["id"])["impacts"]),
                "rca": {
                    "topCause": rca["top_cause"] if rca else None,
                    "confidence": rca["confidence"] if rca else None,
                },
                "ai": {"status": ai.analysis.status.value, "provider": ai.analysis.provider},
                "recovery": {
                    "qualityStatus": recovery_quality.status,
                    "driftStatus": recovery_drift.status,
                    "incidentStatus": final_incident["status"] if final_incident else None,
                },
                "evidence": [item.as_dict() for item in evidence],
            }
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
        if previous_ai_enabled is None:
            os.environ.pop("AI_COPILOT_ENABLED", None)
        else:
            os.environ["AI_COPILOT_ENABLED"] = previous_ai_enabled
