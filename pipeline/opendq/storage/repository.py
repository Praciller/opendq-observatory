"""Small parameterized PostgreSQL repository for the initial data model."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb

from opendq.drift.repository import DriftRepository
from opendq.quality.defaults import default_rules_for_dataset
from opendq.quality.models import (
    IngestionVolume,
    Observation,
    QualityContext,
    QualityEvaluationSummary,
    QualityResult,
    QualityRuleDefinition,
)


class Repository:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self.connection = connection

    def ensure_source_dataset(
        self,
        *,
        source_slug: str,
        source_name: str,
        description: str,
        base_url: str,
        dataset_slug: str,
        dataset_name: str,
        schema_version: str,
    ) -> tuple[int, int]:
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO sources(slug, name, description, base_url)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (slug) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                    """,
                    (source_slug, source_name, description, base_url),
                )
                source_row = cursor.fetchone()
                if source_row is None:
                    raise RuntimeError("source insert did not return an id")
                source_id = source_row[0]
                cursor.execute(
                    """
                    INSERT INTO datasets(source_id, slug, name, description, schema_version)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (source_id, slug) DO UPDATE SET
                        schema_version = EXCLUDED.schema_version,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                    """,
                    (source_id, dataset_slug, dataset_name, description, schema_version),
                )
                dataset_row = cursor.fetchone()
                if dataset_row is None:
                    raise RuntimeError("dataset insert did not return an id")
                dataset_id = dataset_row[0]
        if dataset_slug in {"hourly-weather", "earthquake-events"}:
            DriftRepository(self.connection).ensure_schema_version(int(dataset_id), dataset_slug)
        return int(source_id), int(dataset_id)

    def create_ingestion_run(self, source_id: int, dataset_id: int) -> UUID:
        run_id = uuid4()
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO ingestion_runs(run_id, source_id, dataset_id, status)
                    VALUES (%s, %s, %s, 'RUNNING')
                    """,
                    (run_id, source_id, dataset_id),
                )
        return run_id

    def finish_ingestion_run(
        self,
        run_id: UUID,
        *,
        status: str,
        records_received: int,
        records_written: int,
        records_rejected: int,
        error_code: str | None = None,
        error_message: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        if status not in {"SUCCESS", "PARTIAL", "FAILED", "NO_CHANGE"}:
            raise ValueError("status must be terminal")
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE ingestion_runs SET status = %s, finished_at = %s,
                        records_received = %s, records_written = %s, records_rejected = %s,
                        error_code = %s, error_message = %s, metadata = %s
                    WHERE run_id = %s AND status = 'RUNNING'
                    """,
                    (
                        status,
                        datetime.now(UTC),
                        records_received,
                        records_written,
                        records_rejected,
                        error_code,
                        error_message,
                        Jsonb(dict(metadata or {})),
                        run_id,
                    ),
                )
                if cursor.rowcount != 1:
                    raise ValueError("ingestion run is missing or already terminal")

    def upsert_observations(
        self, dataset_id: int, run_id: UUID, records: Sequence[Mapping[str, Any]]
    ) -> int:
        inserted = 0
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                for record in records:
                    kind = record.get("kind")
                    if kind not in {"weather", "earthquake"}:
                        raise ValueError("record kind must be weather or earthquake")
                    cursor.execute(
                        """
                        INSERT INTO raw_observations(
                            dataset_id, ingestion_run_id, observation_type, observed_at,
                            location_latitude, location_longitude, source_event_id,
                            source_url, temperature_c, relative_humidity_pct,
                            precipitation_mm, wind_speed_kmh, magnitude, depth_km,
                            place, payload, provenance
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT DO NOTHING
                        """,
                        (
                            dataset_id,
                            run_id,
                            kind,
                            record["observed_at"],
                            record.get("latitude"),
                            record.get("longitude"),
                            record.get("event_id"),
                            record.get("source_url"),
                            record.get("temperature_c"),
                            record.get("relative_humidity_pct"),
                            record.get("precipitation_mm"),
                            record.get("wind_speed_kmh"),
                            record.get("magnitude"),
                            record.get("depth_km"),
                            record.get("place"),
                            Jsonb(dict(record.get("payload", {}))),
                            Jsonb(dict(record.get("provenance", {}))),
                        ),
                    )
                    inserted += cursor.rowcount
        return inserted

    def source_statuses(self) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT s.slug, s.name, s.enabled,
                       max(ir.finished_at) FILTER (WHERE ir.status IN ('SUCCESS', 'NO_CHANGE')),
                       max(ir.finished_at) FILTER (
                           WHERE ir.status IN ('SUCCESS', 'NO_CHANGE')
                       ) IS NOT NULL
                FROM sources s
                LEFT JOIN ingestion_runs ir ON ir.source_id = s.id
                GROUP BY s.id, s.slug, s.name, s.enabled
                ORDER BY s.id
                """
            )
            return [
                {
                    "slug": row[0],
                    "name": row[1],
                    "enabled": row[2],
                    "last_successful_ingestion": row[3],
                    "has_ingestion": row[4],
                }
                for row in cursor.fetchall()
            ]

    def dataset_by_slug(self, dataset_slug: str) -> tuple[int, str] | None:
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT id, slug FROM datasets WHERE slug = %s", (dataset_slug,))
            row = cursor.fetchone()
        return (int(row[0]), str(row[1])) if row else None

    def ensure_default_quality_rules(
        self, dataset_id: int, dataset_slug: str
    ) -> list[QualityRuleDefinition]:
        defaults = default_rules_for_dataset(dataset_slug)
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                for rule in defaults:
                    cursor.execute(
                        """
                        INSERT INTO quality_rules(
                            dataset_id, slug, name, dimension, rule_type, severity, config_json
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (dataset_id, slug) DO NOTHING
                        """,
                        (
                            dataset_id,
                            rule["slug"],
                            rule["name"],
                            rule["dimension"],
                            rule["rule_type"],
                            rule["severity"],
                            Jsonb(dict(rule["config"])),
                        ),
                    )
        return self.quality_rules(dataset_id)

    def quality_rules(
        self, dataset_id: int, *, enabled_only: bool = True
    ) -> list[QualityRuleDefinition]:
        predicate = "AND dimension <> 'drift'"
        if enabled_only:
            predicate += " AND enabled"
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id, dataset_id, slug, name, dimension, rule_type,
                       severity, enabled, config_json
                FROM quality_rules
                WHERE dataset_id = %s {predicate}
                ORDER BY id
                """,
                (dataset_id,),
            )
            return [
                QualityRuleDefinition(
                    id=int(row[0]),
                    dataset_id=int(row[1]),
                    slug=str(row[2]),
                    name=str(row[3]),
                    dimension=str(row[4]),
                    rule_type=str(row[5]),
                    severity=str(row[6]),
                    enabled=bool(row[7]),
                    config=dict(row[8] or {}),
                )
                for row in cursor.fetchall()
            ]

    def quality_context(
        self, dataset_id: int, dataset_slug: str, evaluated_at: datetime
    ) -> QualityContext:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT observation_type, observed_at, location_latitude, location_longitude,
                       source_event_id, temperature_c, relative_humidity_pct,
                       precipitation_mm, wind_speed_kmh, magnitude, depth_km, place
                FROM raw_observations
                WHERE dataset_id = %s
                ORDER BY observed_at
                """,
                (dataset_id,),
            )
            observation_rows = cursor.fetchall()
            cursor.execute(
                """
                SELECT finished_at, records_received, records_written, status
                FROM ingestion_runs
                WHERE dataset_id = %s AND status IN ('SUCCESS', 'NO_CHANGE')
                ORDER BY finished_at DESC
                """,
                (dataset_id,),
            )
            volume_rows = cursor.fetchall()
        observations = tuple(
            Observation(
                observed_at=row[1],
                source_event_id=row[4],
                fields={
                    "latitude": row[2],
                    "longitude": row[3],
                    "event_id": row[4],
                    "temperature_c": row[5],
                    "relative_humidity_pct": row[6],
                    "precipitation_mm": row[7],
                    "wind_speed_kmh": row[8],
                    "magnitude": row[9],
                    "depth_km": row[10],
                    "place": row[11],
                },
            )
            for row in observation_rows
        )
        volumes = tuple(
            IngestionVolume(
                finished_at=row[0],
                records_received=int(row[1]),
                records_written=int(row[2]),
                status=str(row[3]),
            )
            for row in volume_rows
        )
        observation_type = (
            str(observation_rows[0][0])
            if observation_rows
            else (
                "weather"
                if dataset_slug == "hourly-weather"
                else "earthquake"
                if dataset_slug == "earthquake-events"
                else "unknown"
            )
        )
        return QualityContext(
            dataset_id=dataset_id,
            dataset_slug=dataset_slug,
            observation_type=observation_type,
            evaluated_at=evaluated_at,
            observations=observations,
            ingestion_volumes=volumes,
        )

    def create_quality_evaluation_run(self, dataset_id: int, triggered_by: str) -> UUID:
        evaluation_run_id = uuid4()
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO quality_evaluation_runs(
                        evaluation_run_id, dataset_id, triggered_by, status
                    )
                    VALUES (%s, %s, %s, 'RUNNING')
                    """,
                    (evaluation_run_id, dataset_id, triggered_by),
                )
        return evaluation_run_id

    def complete_quality_evaluation(
        self,
        evaluation_run_id: UUID,
        dataset_id: int,
        results: Sequence[QualityResult],
        summary: QualityEvaluationSummary,
    ) -> None:
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                for quality_result in results:
                    cursor.execute(
                        """
                        INSERT INTO quality_results(
                            evaluation_run_id, rule_id, dataset_id, status, observed_value,
                            expected_value, affected_records, evaluated_records,
                            details_json, evaluated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            evaluation_run_id,
                            quality_result.rule_id,
                            dataset_id,
                            quality_result.status.value,
                            Jsonb(dict(quality_result.observed_value)),
                            Jsonb(dict(quality_result.expected_value)),
                            quality_result.affected_records,
                            quality_result.evaluated_records,
                            Jsonb(dict(quality_result.details)),
                            quality_result.evaluated_at or summary.evaluated_at,
                        ),
                    )
                cursor.execute(
                    """
                    UPDATE quality_evaluation_runs
                    SET status = 'SUCCESS', finished_at = %s,
                        rules_evaluated = %s, rules_passed = %s, rules_warned = %s,
                        rules_failed = %s, rules_errored = %s, rules_skipped = %s, score = %s
                    WHERE evaluation_run_id = %s AND status = 'RUNNING'
                    """,
                    (
                        datetime.now(UTC),
                        summary.rules_evaluated,
                        summary.rules_passed,
                        summary.rules_warned,
                        summary.rules_failed,
                        summary.rules_errored,
                        summary.rules_skipped,
                        summary.score,
                        evaluation_run_id,
                    ),
                )
                if cursor.rowcount != 1:
                    raise ValueError("quality evaluation run is missing or already terminal")

    def fail_quality_evaluation(
        self, evaluation_run_id: UUID, *, error_code: str, error_message: str
    ) -> None:
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE quality_evaluation_runs
                    SET status = 'FAILED', finished_at = %s, error_code = %s, error_message = %s
                    WHERE evaluation_run_id = %s AND status = 'RUNNING'
                    """,
                    (datetime.now(UTC), error_code, error_message[:500], evaluation_run_id),
                )
                if cursor.rowcount != 1:
                    raise ValueError("quality evaluation run is missing or already terminal")
