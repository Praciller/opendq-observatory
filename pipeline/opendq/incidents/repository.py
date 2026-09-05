"""PostgreSQL persistence for incident state and immutable evidence history."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb

from opendq.incidents.models import IncidentEventType, IncidentKind, IncidentStatus


def _row_to_incident(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "incident_key": str(row[1]),
        "incident_kind": str(row[2]),
        "dataset_id": int(row[3]),
        "dataset_slug": str(row[4]),
        "dataset_name": str(row[5]),
        "rule_id": int(row[6]),
        "rule_slug": str(row[7]),
        "rule_name": str(row[8]),
        "status": str(row[9]),
        "severity": str(row[10]),
        "opened_at": row[11],
        "last_seen_at": row[12],
        "resolved_at": row[13],
        "acknowledged_at": row[14],
        "first_evaluation_run_id": str(row[15]),
        "latest_evaluation_run_id": str(row[16]),
        "first_quality_result_id": int(row[17]),
        "latest_quality_result_id": int(row[18]),
        "occurrence_count": int(row[19]),
        "summary": str(row[20]),
        "evidence": dict(row[21] or {}),
        "created_at": row[22],
        "updated_at": row[23],
    }


class IncidentRepository:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self.connection = connection

    def quality_results_for_run(self, evaluation_run_id: UUID) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT result.id, result.evaluation_run_id, result.dataset_id,
                       d.slug, d.name, result.rule_id, rule.slug, rule.name,
                       result.status, rule.severity, result.observed_value,
                       result.expected_value, result.affected_records,
                       result.evaluated_records, result.details_json, result.evaluated_at
                FROM quality_results result
                JOIN datasets d ON d.id = result.dataset_id
                JOIN quality_rules rule ON rule.id = result.rule_id
                WHERE result.evaluation_run_id = %s
                ORDER BY result.id
                """,
                (evaluation_run_id,),
            )
            return [
                {
                    "quality_result_id": int(row[0]),
                    "evaluation_run_id": row[1],
                    "dataset_id": int(row[2]),
                    "dataset_slug": str(row[3]),
                    "dataset_name": str(row[4]),
                    "rule_id": int(row[5]),
                    "rule_slug": str(row[6]),
                    "rule_name": str(row[7]),
                    "status": str(row[8]),
                    "severity": str(row[9]),
                    "observed_value": dict(row[10] or {}),
                    "expected_value": dict(row[11] or {}),
                    "affected_records": int(row[12]),
                    "evaluated_records": int(row[13]),
                    "details": dict(row[14] or {}),
                    "evaluated_at": row[15],
                }
                for row in cursor.fetchall()
            ]

    def _active_for_update(self, dataset_id: int, rule_id: int) -> tuple[Any, ...] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, status, severity, occurrence_count
                FROM incidents
                WHERE dataset_id = %s AND rule_id = %s AND status IN ('OPEN', 'ACKNOWLEDGED')
                FOR UPDATE
                """,
                (dataset_id, rule_id),
            )
            return cursor.fetchone()

    def open_or_observe(
        self,
        result: Mapping[str, Any],
        *,
        incident_kind: IncidentKind,
        summary: str,
        evidence: Mapping[str, Any],
        impacts: Sequence[Mapping[str, Any]],
    ) -> str:
        now = result["evaluated_at"] or datetime.now(UTC)
        incident_id = uuid4()
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO incidents(
                        id, incident_key, incident_kind, dataset_id, rule_id, status, severity,
                        opened_at, last_seen_at, first_evaluation_run_id, latest_evaluation_run_id,
                        first_quality_result_id, latest_quality_result_id, summary, evidence_json
                    ) VALUES (%s, %s, %s, %s, %s, 'OPEN', %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (dataset_id, rule_id)
                        WHERE status IN ('OPEN', 'ACKNOWLEDGED') DO NOTHING
                    RETURNING id
                    """,
                    (
                        incident_id,
                        f"{result['dataset_slug']}:{result['rule_slug']}",
                        incident_kind.value,
                        result["dataset_id"],
                        result["rule_id"],
                        result["severity"],
                        now,
                        now,
                        result["evaluation_run_id"],
                        result["evaluation_run_id"],
                        result["quality_result_id"],
                        result["quality_result_id"],
                        summary,
                        Jsonb(dict(evidence)),
                    ),
                )
                inserted = cursor.fetchone()
            if inserted is not None:
                self._insert_event(
                    incident_id=str(inserted[0]),
                    event_type=IncidentEventType.OPENED,
                    result=result,
                    from_status=None,
                    to_status=IncidentStatus.OPEN,
                    message=summary,
                    details={"impact_count": len(impacts)},
                )
                self._insert_impacts(str(inserted[0]), impacts, now)
                return str(inserted[0])

            active = self._active_for_update(int(result["dataset_id"]), int(result["rule_id"]))
            if active is None:
                raise RuntimeError("active incident disappeared after conflict")
            active_id, active_status, _severity, occurrence_count = active
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE incidents
                    SET last_seen_at = %s, latest_evaluation_run_id = %s,
                        latest_quality_result_id = %s, occurrence_count = %s,
                        summary = %s, evidence_json = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (
                        now,
                        result["evaluation_run_id"],
                        result["quality_result_id"],
                        int(occurrence_count) + 1,
                        summary,
                        Jsonb(dict(evidence)),
                        active_id,
                    ),
                )
            self._insert_event(
                incident_id=str(active_id),
                event_type=IncidentEventType.OBSERVED_AGAIN,
                result=result,
                from_status=str(active_status),
                to_status=str(active_status),
                message=summary,
                details={"impact_count": len(impacts)},
            )
            return str(active_id)

    def resolve_if_active(self, result: Mapping[str, Any], *, summary: str) -> str | None:
        now = result["evaluated_at"] or datetime.now(UTC)
        with self.connection.transaction():
            active = self._active_for_update(int(result["dataset_id"]), int(result["rule_id"]))
            if active is None:
                return None
            incident_id, from_status, severity, _occurrence_count = active
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE incidents
                    SET status = 'RESOLVED', resolved_at = %s,
                        latest_evaluation_run_id = %s, latest_quality_result_id = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (now, result["evaluation_run_id"], result["quality_result_id"], incident_id),
                )
            self._insert_event(
                incident_id=str(incident_id),
                event_type=IncidentEventType.RESOLVED,
                result=result,
                from_status=str(from_status),
                to_status=IncidentStatus.RESOLVED,
                message=summary,
                details={"recovered": True, "severity": severity},
            )
            return str(incident_id)

    def _insert_event(
        self,
        *,
        incident_id: str,
        event_type: IncidentEventType,
        result: Mapping[str, Any] | None,
        from_status: str | None,
        to_status: IncidentStatus | str,
        message: str,
        details: Mapping[str, Any],
    ) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO incident_events(
                    incident_id, event_type, evaluation_run_id, quality_result_id,
                    from_status, to_status, severity, message, details_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    incident_id,
                    event_type.value,
                    result["evaluation_run_id"] if result else None,
                    result["quality_result_id"] if result else None,
                    from_status,
                    to_status.value if isinstance(to_status, IncidentStatus) else to_status,
                    result["severity"] if result else "INFO",
                    message,
                    Jsonb(dict(details)),
                ),
            )

    def _insert_impacts(
        self, incident_id: str, impacts: Sequence[Mapping[str, Any]], captured_at: datetime
    ) -> None:
        with self.connection.cursor() as cursor:
            for impact in impacts:
                cursor.execute(
                    """
                    INSERT INTO incident_impacts(
                        incident_id, lineage_node_id, distance, path_json, captured_at
                    )
                    SELECT %s, node.id, %s, %s, %s
                    FROM lineage_nodes node WHERE node.key = %s
                    ON CONFLICT (incident_id, lineage_node_id) DO NOTHING
                    """,
                    (
                        incident_id,
                        int(impact["distance"]),
                        Jsonb(list(impact["path"])),
                        captured_at,
                        impact["key"],
                    ),
                )

    def acknowledge(self, incident_id: str) -> dict[str, Any]:
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE incidents
                    SET status = 'ACKNOWLEDGED', acknowledged_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND status = 'OPEN'
                    RETURNING id, severity
                    """,
                    (incident_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise ValueError("only OPEN incidents can be acknowledged")
                self._insert_event(
                    incident_id=incident_id,
                    event_type=IncidentEventType.ACKNOWLEDGED,
                    result=None,
                    from_status=IncidentStatus.OPEN.value,
                    to_status=IncidentStatus.ACKNOWLEDGED,
                    message="Incident acknowledged by trusted operator CLI.",
                    details={"source": "trusted_cli", "severity": str(row[1])},
                )
        return self.get_incident(incident_id)

    def list_incidents(
        self,
        *,
        status: str | None = None,
        dataset: str | None = None,
        severity: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        clauses = ["TRUE"]
        params: list[Any] = []
        if status:
            clauses.append("incident.status = %s")
            params.append(status.upper())
        if dataset:
            clauses.append("d.slug = %s")
            params.append(dataset)
        if severity:
            clauses.append("incident.severity = %s")
            params.append(severity.upper())
        params.append(max(1, min(limit, 100)))
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT incident.id, incident.incident_key, incident.incident_kind,
                       incident.dataset_id, d.slug, d.name, incident.rule_id,
                       rule.slug, rule.name, incident.status, incident.severity,
                       incident.opened_at, incident.last_seen_at, incident.resolved_at,
                       incident.acknowledged_at, incident.first_evaluation_run_id,
                       incident.latest_evaluation_run_id, incident.first_quality_result_id,
                       incident.latest_quality_result_id, incident.occurrence_count,
                       incident.summary, incident.evidence_json, incident.created_at,
                       incident.updated_at
                FROM incidents incident
                JOIN datasets d ON d.id = incident.dataset_id
                JOIN quality_rules rule ON rule.id = incident.rule_id
                WHERE {" AND ".join(clauses)}
                ORDER BY incident.opened_at DESC, incident.id DESC
                LIMIT %s
                """,
                params,
            )
            return [_row_to_incident(row) for row in cursor.fetchall()]

    def get_incident(self, incident_id: str) -> dict[str, Any]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT incident.id, incident.incident_key, incident.incident_kind,
                       incident.dataset_id, d.slug, d.name, incident.rule_id,
                       rule.slug, rule.name, incident.status, incident.severity,
                       incident.opened_at, incident.last_seen_at, incident.resolved_at,
                       incident.acknowledged_at, incident.first_evaluation_run_id,
                       incident.latest_evaluation_run_id, incident.first_quality_result_id,
                       incident.latest_quality_result_id, incident.occurrence_count,
                       incident.summary, incident.evidence_json, incident.created_at,
                       incident.updated_at
                FROM incidents incident
                JOIN datasets d ON d.id = incident.dataset_id
                JOIN quality_rules rule ON rule.id = incident.rule_id
                WHERE incident.id = %s
                """,
                (incident_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"incident not found: {incident_id}")
            incident = _row_to_incident(row)
            cursor.execute(
                """
                SELECT id, event_type, evaluation_run_id, quality_result_id,
                       from_status, to_status, severity, message, details_json, created_at
                FROM incident_events WHERE incident_id = %s ORDER BY id
                """,
                (incident_id,),
            )
            incident["events"] = [
                {
                    "id": int(event[0]),
                    "event_type": str(event[1]),
                    "evaluation_run_id": str(event[2]) if event[2] else None,
                    "quality_result_id": int(event[3]) if event[3] else None,
                    "from_status": event[4],
                    "to_status": str(event[5]),
                    "severity": str(event[6]),
                    "message": str(event[7]),
                    "details": dict(event[8] or {}),
                    "created_at": event[9],
                }
                for event in cursor.fetchall()
            ]
            cursor.execute(
                """
                SELECT impact.lineage_node_id, node.key, node.name, node.node_type,
                       impact.distance, impact.path_json, impact.captured_at
                FROM incident_impacts impact
                JOIN lineage_nodes node ON node.id = impact.lineage_node_id
                WHERE impact.incident_id = %s ORDER BY impact.distance, node.key
                """,
                (incident_id,),
            )
            incident["impacts"] = [
                {
                    "lineage_node_id": int(impact[0]),
                    "key": str(impact[1]),
                    "name": str(impact[2]),
                    "node_type": str(impact[3]),
                    "distance": int(impact[4]),
                    "path": list(impact[5]),
                    "captured_at": impact[6],
                }
                for impact in cursor.fetchall()
            ]
            return incident
