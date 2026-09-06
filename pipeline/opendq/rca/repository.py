"""Persistence for reproducible deterministic RCA analyses."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb

from opendq.rca.engine import RankedCause


class RCARepository:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self.connection = connection

    def incident_context(self, incident_id: str) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT incidents.id, incidents.incident_kind, incidents.dataset_id,
                       d.slug, d.name, incidents.incident_key,
                       rule.slug, rule.dimension, status, summary, latest_quality_result_id,
                       latest_drift_result_id
                FROM incidents
                JOIN datasets d ON d.id = incidents.dataset_id
                JOIN quality_rules rule ON rule.id = incidents.rule_id
                WHERE incidents.id = %s
                """,
                (incident_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            cursor.execute(
                """
                SELECT id, key, name, node_type, distance, path_json
                FROM incident_impacts impacts
                JOIN lineage_nodes nodes ON nodes.id = impacts.lineage_node_id
                WHERE incident_id = %s ORDER BY distance, key
                """,
                (incident_id,),
            )
            impacts = [
                {
                    "id": int(item[0]),
                    "key": str(item[1]),
                    "name": str(item[2]),
                    "node_type": str(item[3]),
                    "distance": int(item[4]),
                    "path": list(item[5]),
                }
                for item in cursor.fetchall()
            ]
        return {
            "id": str(row[0]),
            "incident_kind": str(row[1]),
            "dataset_id": int(row[2]),
            "dataset_slug": str(row[3]),
            "dataset_name": str(row[4]),
            "incident_key": str(row[5]),
            "rule_slug": str(row[6]),
            "rule_dimension": str(row[7]),
            "status": str(row[8]),
            "summary": str(row[9]),
            "latest_quality_result_id": int(row[10]) if row[10] else None,
            "latest_drift_result_id": int(row[11]) if row[11] else None,
            "impacts": impacts,
        }

    def quality_result(self, result_id: int) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, evaluation_run_id, status, observed_value, expected_value,
                       details_json, evaluated_at
                FROM quality_results WHERE id = %s
                """,
                (result_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return {
            "id": int(row[0]),
            "evaluation_run_id": str(row[1]),
            "status": str(row[2]),
            "observed": dict(row[3] or {}),
            "expected": dict(row[4] or {}),
            "details": dict(row[5] or {}),
            "evaluated_at": row[6],
        }

    def drift_result(self, result_id: int) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, evaluation_run_id, column_name, method, status, observed_metric,
                       threshold, baseline_version, details_json, evaluated_at
                FROM drift_results WHERE id = %s
                """,
                (result_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return {
            "id": int(row[0]),
            "evaluation_run_id": str(row[1]),
            "column_name": str(row[2]),
            "method": str(row[3]),
            "status": str(row[4]),
            "observed_metric": row[5],
            "threshold": row[6],
            "baseline_version": row[7],
            "details": dict(row[8] or {}),
            "evaluated_at": row[9],
        }

    def latest_ingestion(self, dataset_id: int) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT run_id, status, records_received, records_written, records_rejected,
                       error_code, error_message, finished_at
                FROM ingestion_runs WHERE dataset_id = %s
                ORDER BY started_at DESC LIMIT 1
                """,
                (dataset_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return {
            "run_id": str(row[0]),
            "status": str(row[1]),
            "records_received": int(row[2]),
            "records_written": int(row[3]),
            "records_rejected": int(row[4]),
            "error_code": row[5],
            "error_message": row[6],
            "finished_at": row[7],
        }

    def upstream_sources(self, dataset_slug: str) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT upstream.key, upstream.name, upstream.node_type
                FROM lineage_edges edges
                JOIN lineage_nodes upstream ON upstream.id = edges.upstream_node_id
                JOIN lineage_nodes downstream ON downstream.id = edges.downstream_node_id
                WHERE downstream.key = %s AND upstream.node_type = 'SOURCE'
                ORDER BY upstream.key
                """,
                (f"dataset:{dataset_slug}",),
            )
            return [
                {"key": str(row[0]), "name": str(row[1]), "node_type": str(row[2])}
                for row in cursor.fetchall()
            ]

    def persist(
        self,
        *,
        incident_id: str,
        top_cause: RankedCause,
        candidates: Sequence[RankedCause],
        algorithm_version: str,
        fingerprint: str,
        summary: str,
        details: dict[str, Any],
    ) -> str:
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                analysis_id = uuid4()
                cursor.execute(
                    """
                    INSERT INTO root_cause_analyses(
                        id, incident_id, status, top_cause, confidence, algorithm_version,
                        evidence_fingerprint, summary, details_json
                    ) VALUES (%s, %s, 'SUCCESS', %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (incident_id, algorithm_version, evidence_fingerprint) DO NOTHING
                    RETURNING id
                    """,
                    (
                        analysis_id,
                        incident_id,
                        top_cause.cause,
                        top_cause.confidence,
                        algorithm_version,
                        fingerprint,
                        summary,
                        Jsonb(details),
                    ),
                )
                inserted = cursor.fetchone()
                if inserted is None:
                    cursor.execute(
                        """
                        SELECT id FROM root_cause_analyses
                        WHERE incident_id = %s AND algorithm_version = %s
                          AND evidence_fingerprint = %s
                        """,
                        (incident_id, algorithm_version, fingerprint),
                    )
                    existing = cursor.fetchone()
                    if existing is None:
                        raise RuntimeError("RCA analysis disappeared after conflict")
                    return str(existing[0])
                analysis_id = inserted[0]
                for candidate in candidates:
                    for signal in candidate.evidence:
                        cursor.execute(
                            """
                            INSERT INTO root_cause_evidence(
                                analysis_id, evidence_type, source_table, source_id,
                                reason_code, weight, details_json
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                analysis_id,
                                signal.evidence_type,
                                signal.details.get("source_table", "derived"),
                                signal.reference,
                                signal.reason_code,
                                signal.weight,
                                Jsonb(dict(signal.details)),
                            ),
                        )
        return str(analysis_id)

    def latest(self, incident_id: str) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, incident_id, status, top_cause, confidence, algorithm_version,
                       evidence_fingerprint, summary, details_json, created_at
                FROM root_cause_analyses
                WHERE incident_id = %s ORDER BY created_at DESC LIMIT 1
                """,
                (incident_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            cursor.execute(
                """
                SELECT evidence_type, source_table, source_id, reason_code, weight, details_json
                FROM root_cause_evidence WHERE analysis_id = %s ORDER BY weight DESC, id
                """,
                (row[0],),
            )
            evidence = [
                {
                    "evidence_type": str(item[0]),
                    "source_table": str(item[1]),
                    "source_id": str(item[2]) if item[2] else None,
                    "reason_code": str(item[3]),
                    "weight": float(item[4]),
                    "details": dict(item[5] or {}),
                }
                for item in cursor.fetchall()
            ]
        return {
            "id": str(row[0]),
            "incident_id": str(row[1]),
            "status": str(row[2]),
            "top_cause": str(row[3]),
            "confidence": str(row[4]),
            "algorithm_version": str(row[5]),
            "evidence_fingerprint": str(row[6]),
            "summary": str(row[7]),
            "details": dict(row[8] or {}),
            "created_at": row[9],
            "evidence": evidence,
        }
