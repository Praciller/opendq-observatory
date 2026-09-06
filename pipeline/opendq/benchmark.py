"""Reproducible local performance baseline for representative pipeline paths."""

from __future__ import annotations

import os
import platform
import sys
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from statistics import median
from time import perf_counter

import psycopg

from opendq.demo import _reset_demo_database, _write_weather, validate_demo_environment
from opendq.drift.service import create_baselines
from opendq.drift.service import evaluate_dataset as evaluate_drift
from opendq.incidents.repository import IncidentRepository
from opendq.lineage.seed import seed_lineage
from opendq.quality.engine import evaluate_dataset as evaluate_quality
from opendq.rca.service import analyze_incident
from opendq.storage.repository import Repository


def summarize_samples(samples: list[float]) -> dict[str, float | int | None]:
    if not samples:
        return {"runs": 0, "medianMs": None, "minMs": None, "maxMs": None}
    return {
        "runs": len(samples),
        "medianMs": round(median(samples), 2),
        "minMs": round(min(samples), 2),
        "maxMs": round(max(samples), 2),
    }


def _timed(callback: Callable[[], object]) -> float:
    started = perf_counter()
    callback()
    return max(0.0, (perf_counter() - started) * 1000)


def _single_run(database_url: str, run_number: int) -> dict[str, float]:
    with psycopg.connect(database_url) as connection:
        _reset_demo_database(connection)
        repository = Repository(connection)
        source_id, dataset_id = repository.ensure_source_dataset(
            source_slug="open-meteo",
            source_name="Open-Meteo benchmark",
            description="Phase 6 local benchmark",
            base_url="https://example.test/open-meteo",
            dataset_slug="hourly-weather",
            dataset_name="Hourly weather benchmark",
            schema_version="1",
        )
        seed_lineage(connection)
        base_start = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=run_number * 10)
        healthy = [25.0 + (index % 3) for index in range(100)]
        shifted = [45.0 + (index % 3) for index in range(100)]
        samples = {
            "fixture_ingestion": _timed(
                lambda: _write_weather(
                    repository, source_id, dataset_id, base_start, healthy, humidity=50.0
                )
            ),
            "quality_evaluation": _timed(
                lambda: evaluate_quality(
                    repository,
                    "hourly-weather",
                    triggered_by="benchmark",
                    evaluated_at=base_start + timedelta(hours=100),
                )
            ),
        }
        create_baselines(connection, "hourly-weather")
        _write_weather(
            repository,
            source_id,
            dataset_id,
            base_start + timedelta(hours=101),
            shifted,
            humidity=50.0,
        )
        samples["drift_evaluation_and_reconciliation"] = _timed(
            lambda: evaluate_drift(
                connection,
                "hourly-weather",
                triggered_by="benchmark",
                evaluated_at=base_start + timedelta(hours=200),
            )
        )
        incident = IncidentRepository(connection).list_incidents(status="OPEN")[0]
        samples["incident_reconciliation_query"] = _timed(
            lambda: IncidentRepository(connection).get_incident(incident["id"])
        )
        samples["deterministic_rca"] = _timed(lambda: analyze_incident(connection, incident["id"]))
        return samples


def run_benchmark(
    database_url: str, *, runs: int = 5, production_database_url: str | None = None
) -> dict[str, object]:
    validate_demo_environment(
        app_env=os.getenv("APP_ENV", ""),
        demo_database_url=database_url,
        production_database_url=production_database_url,
    )
    bounded_runs = max(1, min(runs, 20))
    samples: dict[str, list[float]] = {}
    for run_number in range(bounded_runs):
        for name, duration in _single_run(database_url, run_number).items():
            samples.setdefault(name, []).append(duration)
    return {
        "databaseScope": "local-benchmark-only",
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "runs": bounded_runs,
        "recordsPerFixture": 100,
        "metrics": {name: summarize_samples(values) for name, values in samples.items()},
    }
