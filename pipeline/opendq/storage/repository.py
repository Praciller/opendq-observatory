"""Small parameterized PostgreSQL repository for the initial data model."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb


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
