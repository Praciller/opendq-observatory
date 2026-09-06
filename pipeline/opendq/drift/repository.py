"""Bounded PostgreSQL access for drift baselines and evaluations."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb

from opendq.drift.config import canonical_schema
from opendq.drift.models import DriftFeature, DriftResult

DRIFT_COLUMNS = {
    "temperature_c",
    "relative_humidity_pct",
    "precipitation_mm",
    "wind_speed_kmh",
    "magnitude",
    "depth_km",
    "place",
}


def _schema_hash(schema: Mapping[str, Any]) -> str:
    encoded = json.dumps(schema, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


class DriftRepository:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self.connection = connection

    def dataset(self, dataset_slug: str) -> tuple[int, str] | None:
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT id, slug FROM datasets WHERE slug = %s", (dataset_slug,))
            row = cursor.fetchone()
        return (int(row[0]), str(row[1])) if row else None

    def ensure_schema_version(self, dataset_id: int, dataset_slug: str) -> None:
        schema = canonical_schema(dataset_slug)
        version = "1"
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO dataset_versions(dataset_id, version, schema_hash, schema_json)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (dataset_id, version) DO NOTHING
                    """,
                    (dataset_id, version, _schema_hash(schema), Jsonb(schema)),
                )

    def current_schema(self, dataset_id: int) -> dict[str, Any]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT schema_json FROM dataset_versions
                WHERE dataset_id = %s ORDER BY created_at DESC, id DESC LIMIT 1
                """,
                (dataset_id,),
            )
            row = cursor.fetchone()
        return dict(row[0] or {}) if row else {}

    def observations(
        self,
        dataset_id: int,
        column_name: str,
        *,
        after: datetime | None = None,
        limit: int = 1000,
        latest: bool = False,
    ) -> list[tuple[datetime, Any, UUID]]:
        if column_name not in DRIFT_COLUMNS:
            raise ValueError(f"unsupported drift column: {column_name}")
        where = f"dataset_id = %s AND {column_name} IS NOT NULL"
        params: list[Any] = [dataset_id]
        if after is not None:
            where += " AND observed_at > %s"
            params.append(after)
        params.append(max(1, min(limit, 5000)))
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT observed_at, {column_name}, ingestion_run_id
                FROM raw_observations
                WHERE {where}
                ORDER BY observed_at {"DESC" if latest else "ASC"}
                LIMIT %s
                """,
                params,
            )
            rows = [(row[0], row[1], row[2]) for row in cursor.fetchall()]
            return list(reversed(rows)) if latest else rows

    def latest_ingestion_run(self, dataset_id: int) -> UUID | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT run_id FROM ingestion_runs
                WHERE dataset_id = %s AND status IN ('SUCCESS', 'NO_CHANGE')
                ORDER BY finished_at DESC LIMIT 1
                """,
                (dataset_id,),
            )
            row = cursor.fetchone()
        return row[0] if row else None

    def active_baseline(
        self, dataset_id: int, column_name: str, baseline_type: str
    ) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, column_name, baseline_type, baseline_version, window_start, window_end,
                       sample_count, statistics_json, distribution_json, created_from_run_id
                FROM drift_baselines
                WHERE dataset_id = %s AND column_name = %s AND baseline_type = %s AND active
                ORDER BY baseline_version DESC LIMIT 1
                """,
                (dataset_id, column_name, baseline_type),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return {
            "id": int(row[0]),
            "column_name": str(row[1]),
            "baseline_type": str(row[2]),
            "baseline_version": int(row[3]),
            "window_start": row[4],
            "window_end": row[5],
            "sample_count": int(row[6]),
            "statistics": dict(row[7] or {}),
            "distribution": dict(row[8] or {}),
            "created_from_run_id": row[9],
        }

    def active_baselines(self, dataset_id: int) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name, baseline_type, baseline_version, sample_count
                FROM drift_baselines WHERE dataset_id = %s AND active
                ORDER BY column_name, baseline_type
                """,
                (dataset_id,),
            )
            return [
                {
                    "column_name": str(row[0]),
                    "baseline_type": str(row[1]),
                    "baseline_version": int(row[2]),
                    "sample_count": int(row[3]),
                }
                for row in cursor.fetchall()
            ]

    def create_baseline(
        self,
        dataset_id: int,
        *,
        column_name: str,
        baseline_type: str,
        window_start: datetime | None,
        window_end: datetime | None,
        sample_count: int,
        statistics: Mapping[str, Any],
        distribution: Mapping[str, Any],
        created_from_run_id: UUID | None,
    ) -> dict[str, Any]:
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COALESCE(MAX(baseline_version), 0) + 1
                    FROM drift_baselines
                    WHERE dataset_id = %s AND column_name = %s AND baseline_type = %s
                    """,
                    (dataset_id, column_name, baseline_type),
                )
                version_row = cursor.fetchone()
                if version_row is None:
                    raise RuntimeError("baseline version query returned no row")
                version = int(version_row[0])
                cursor.execute(
                    """
                    UPDATE drift_baselines SET active = FALSE, updated_at = CURRENT_TIMESTAMP
                    WHERE dataset_id = %s AND column_name = %s AND baseline_type = %s AND active
                    """,
                    (dataset_id, column_name, baseline_type),
                )
                cursor.execute(
                    """
                    INSERT INTO drift_baselines(
                        dataset_id, column_name, baseline_type, baseline_version,
                        window_start, window_end, sample_count, statistics_json,
                        distribution_json, created_from_run_id, active
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                    RETURNING id, baseline_version
                    """,
                    (
                        dataset_id,
                        column_name,
                        baseline_type,
                        version,
                        window_start,
                        window_end,
                        sample_count,
                        Jsonb(dict(statistics)),
                        Jsonb(dict(distribution)),
                        created_from_run_id,
                    ),
                )
                row = cursor.fetchone()
        if row is None:
            raise RuntimeError("baseline insert did not return an id")
        return {"id": int(row[0]), "baseline_version": int(row[1])}

    def create_evaluation_run(self, dataset_id: int, triggered_by: str) -> UUID:
        evaluation_run_id = uuid4()
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO drift_evaluation_runs(
                        evaluation_run_id, dataset_id, triggered_by, status
                    )
                    VALUES (%s, %s, %s, 'RUNNING')
                    """,
                    (evaluation_run_id, dataset_id, triggered_by),
                )
        return evaluation_run_id

    def complete_evaluation(
        self,
        evaluation_run_id: UUID,
        dataset_id: int,
        results: Sequence[DriftResult],
        *,
        status: str,
        evaluated_at: datetime,
    ) -> None:
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                for result in results:
                    cursor.execute(
                        """
                        INSERT INTO drift_results(
                            evaluation_run_id, dataset_id, column_name, method, status, severity,
                            baseline_id, baseline_version, baseline_window_start,
                            baseline_window_end,
                            current_window_start, current_window_end, observed_metric, threshold,
                            baseline_sample_count, current_sample_count, details_json, evaluated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        """,
                        (
                            evaluation_run_id,
                            dataset_id,
                            result.column_name,
                            result.method,
                            result.status.value,
                            result.severity,
                            result.baseline_id,
                            result.baseline_version,
                            result.baseline_window_start,
                            result.baseline_window_end,
                            result.current_window_start,
                            result.current_window_end,
                            result.observed_metric,
                            result.threshold,
                            result.baseline_sample_count,
                            result.current_sample_count,
                            Jsonb(dict(result.details)),
                            evaluated_at,
                        ),
                    )
                counts = {
                    status: sum(result.status.value == status for result in results)
                    for status in ("STABLE", "WARN", "DRIFT", "SKIPPED", "ERROR")
                }
                cursor.execute(
                    """
                    UPDATE drift_evaluation_runs
                    SET status = %s, finished_at = %s, checks_evaluated = %s,
                        checks_stable = %s, checks_warned = %s, checks_drifted = %s,
                        checks_skipped = %s, checks_errored = %s
                    WHERE evaluation_run_id = %s AND status = 'RUNNING'
                    """,
                    (
                        status,
                        evaluated_at,
                        len(results),
                        counts["STABLE"],
                        counts["WARN"],
                        counts["DRIFT"],
                        counts["SKIPPED"],
                        counts["ERROR"],
                        evaluation_run_id,
                    ),
                )
                if cursor.rowcount != 1:
                    raise ValueError("drift evaluation run is missing or already terminal")

    def fail_evaluation(self, evaluation_run_id: UUID, error_message: str) -> None:
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE drift_evaluation_runs
                    SET status = 'FAILED', finished_at = %s, error_code = 'DRIFT_EVALUATION_ERROR',
                        error_message = %s
                    WHERE evaluation_run_id = %s AND status = 'RUNNING'
                    """,
                    (datetime.now(UTC), error_message[:500], evaluation_run_id),
                )

    def drift_results_for_run(self, evaluation_run_id: UUID) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT result.id, result.evaluation_run_id, result.dataset_id, d.slug, d.name,
                       result.column_name, result.method, result.status, result.severity,
                       result.baseline_id, result.baseline_version, result.observed_metric,
                       result.threshold, result.baseline_sample_count, result.current_sample_count,
                       result.details_json, result.evaluated_at
                FROM drift_results result JOIN datasets d ON d.id = result.dataset_id
                WHERE result.evaluation_run_id = %s ORDER BY result.id
                """,
                (evaluation_run_id,),
            )
            return [
                {
                    "drift_result_id": int(row[0]),
                    "evaluation_run_id": row[1],
                    "dataset_id": int(row[2]),
                    "dataset_slug": str(row[3]),
                    "dataset_name": str(row[4]),
                    "column_name": str(row[5]),
                    "method": str(row[6]),
                    "status": str(row[7]),
                    "severity": str(row[8]),
                    "baseline_id": int(row[9]) if row[9] else None,
                    "baseline_version": int(row[10]) if row[10] else None,
                    "observed_metric": row[11],
                    "threshold": row[12],
                    "baseline_sample_count": int(row[13]),
                    "current_sample_count": int(row[14]),
                    "details": dict(row[15] or {}),
                    "evaluated_at": row[16],
                }
                for row in cursor.fetchall()
            ]

    def ensure_drift_rule(self, dataset_id: int, feature: DriftFeature) -> int:
        slug = f"drift:{feature.column_name}:{feature.method.lower()}"
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO quality_rules(
                        dataset_id, slug, name, dimension, rule_type, severity, config_json
                    )
                    VALUES (%s, %s, %s, 'drift', %s, %s, %s)
                    ON CONFLICT (dataset_id, slug) DO UPDATE SET severity = EXCLUDED.severity
                    RETURNING id
                    """,
                    (
                        dataset_id,
                        slug,
                        f"{feature.column_name} {feature.method} drift",
                        feature.method,
                        feature.severity,
                        Jsonb(
                            {
                                "threshold": feature.threshold,
                                "minimum_samples": feature.minimum_samples,
                            }
                        ),
                    ),
                )
                row = cursor.fetchone()
        if row is None:
            raise RuntimeError("drift rule insert did not return an id")
        return int(row[0])

    def active_drift_baselines(self, dataset_id: int) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name, baseline_type, baseline_version, sample_count,
                       window_start, window_end
                FROM drift_baselines WHERE dataset_id = %s AND active
                ORDER BY column_name, baseline_type
                """,
                (dataset_id,),
            )
            return [
                {
                    "column_name": str(row[0]),
                    "baseline_type": str(row[1]),
                    "baseline_version": int(row[2]),
                    "sample_count": int(row[3]),
                    "window_start": row[4],
                    "window_end": row[5],
                }
                for row in cursor.fetchall()
            ]

    def latest_drift_results(
        self, dataset_slug: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT ON (d.slug, result.column_name, result.method)
                       result.id, d.slug, d.name, result.column_name, result.method, result.status,
                       result.severity, result.baseline_version, result.observed_metric,
                       result.threshold,
                       result.baseline_sample_count, result.current_sample_count,
                       result.details_json,
                       result.evaluated_at, run.status
                FROM drift_results result
                JOIN datasets d ON d.id = result.dataset_id
                JOIN drift_evaluation_runs run ON run.evaluation_run_id = result.evaluation_run_id
                WHERE (%s IS NULL OR d.slug = %s)
                ORDER BY d.slug, result.column_name, result.method, result.evaluated_at DESC
                LIMIT %s
                """,
                (dataset_slug, dataset_slug, max(1, min(limit, 200))),
            )
            return [
                {
                    "id": int(row[0]),
                    "dataset_slug": str(row[1]),
                    "dataset_name": str(row[2]),
                    "column_name": str(row[3]),
                    "method": str(row[4]),
                    "status": str(row[5]),
                    "severity": str(row[6]),
                    "baseline_version": int(row[7]) if row[7] else None,
                    "observed_metric": row[8],
                    "threshold": row[9],
                    "baseline_sample_count": int(row[10]),
                    "current_sample_count": int(row[11]),
                    "details": dict(row[12] or {}),
                    "evaluated_at": row[13],
                    "run_status": str(row[14]),
                }
                for row in cursor.fetchall()
            ]

    def baseline_rows(
        self, dataset_slug: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT b.id, d.slug, b.column_name, b.baseline_type, b.baseline_version,
                       b.window_start, b.window_end, b.sample_count, b.active, b.created_at
                FROM drift_baselines b JOIN datasets d ON d.id = b.dataset_id
                WHERE (%s IS NULL OR d.slug = %s)
                ORDER BY d.slug, b.column_name, b.baseline_type, b.baseline_version DESC
                LIMIT %s
                """,
                (dataset_slug, dataset_slug, max(1, min(limit, 200))),
            )
            return [
                {
                    "id": int(row[0]),
                    "dataset_slug": str(row[1]),
                    "column_name": str(row[2]),
                    "baseline_type": str(row[3]),
                    "baseline_version": int(row[4]),
                    "window_start": row[5],
                    "window_end": row[6],
                    "sample_count": int(row[7]),
                    "active": bool(row[8]),
                    "created_at": row[9],
                }
                for row in cursor.fetchall()
            ]
