"""Bounded incident context loading and persisted AI analysis storage."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb

from opendq.ai.models import AICopilotStatus, AIExplanation, IncidentAIInput
from opendq.rca.repository import RCARepository


@dataclass(frozen=True, slots=True)
class AIIncidentContext:
    incident_id: str
    deterministic_rca_id: str | None
    deterministic_rca: dict[str, Any]
    input: IncidentAIInput


@dataclass(frozen=True, slots=True)
class AIAnalysisRecord:
    id: str
    incident_id: str
    provider: str
    model: str
    prompt_version: str
    input_fingerprint: str
    deterministic_rca_analysis_id: str | None
    status: AICopilotStatus
    explanation: AIExplanation
    latency_ms: int
    input_size: int
    output_size: int
    provider_request_id: str | None
    cache_hit: bool
    attempts: list[dict[str, Any]]
    error_code: str | None
    error_message: str | None
    created_at: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "incidentId": self.incident_id,
            "provider": self.provider,
            "model": self.model,
            "promptVersion": self.prompt_version,
            "status": self.status.value,
            "explanation": self.explanation.to_dict(),
            "latencyMs": self.latency_ms,
            "inputSize": self.input_size,
            "outputSize": self.output_size,
            "providerRequestId": self.provider_request_id,
            "cacheHit": self.cache_hit,
            "attempts": self.attempts,
            "errorCode": self.error_code,
            "errorMessage": self.error_message,
            "createdAt": self.created_at.isoformat()
            if hasattr(self.created_at, "isoformat")
            else None,
        }


def _record(row: tuple[Any, ...], *, cache_hit: bool | None = None) -> AIAnalysisRecord:
    explanation = AIExplanation(
        summary=str(row[8]),
        probable_cause_explanation=str(row[9]),
        evidence_highlights=list(row[10] or []),
        investigation_steps=list(row[11] or []),
        uncertainties=list(row[12] or []),
    )
    return AIAnalysisRecord(
        id=str(row[0]),
        incident_id=str(row[1]),
        provider=str(row[2]),
        model=str(row[3]),
        prompt_version=str(row[4]),
        input_fingerprint=str(row[5]),
        deterministic_rca_analysis_id=str(row[6]) if row[6] else None,
        status=AICopilotStatus(str(row[7])),
        explanation=explanation,
        latency_ms=int(row[13]),
        input_size=int(row[14]),
        output_size=int(row[15]),
        provider_request_id=str(row[16]) if row[16] else None,
        cache_hit=bool(row[17]) if cache_hit is None else cache_hit,
        attempts=list(row[18] or []),
        error_code=str(row[19]) if row[19] else None,
        error_message=str(row[20]) if row[20] else None,
        created_at=row[21],
    )


class AIIncidentRepository:
    _SELECT = """
        SELECT id, incident_id, provider, model, prompt_version, input_fingerprint,
               deterministic_rca_analysis_id, status, summary, probable_cause_explanation,
               evidence_highlights_json, investigation_steps_json, uncertainties_json,
               latency_ms, input_size, output_size, provider_request_id, cache_hit,
               attempts_json, error_code, error_message, created_at
        FROM ai_incident_analyses
    """

    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self.connection = connection
        self.rca = RCARepository(connection)

    def context(self, incident_id: str) -> AIIncidentContext | None:
        base = self.rca.incident_context(incident_id)
        if base is None:
            return None
        rca = self.rca.latest(incident_id)
        quality = (
            self.rca.quality_result(base["latest_quality_result_id"])
            if base["latest_quality_result_id"]
            else None
        )
        drift = (
            self.rca.drift_result(base["latest_drift_result_id"])
            if base["latest_drift_result_id"]
            else None
        )
        severity = self._severity(incident_id)
        timeline = self._timeline(incident_id)
        quality_evidence = [self._quality_evidence(quality)] if quality else []
        drift_evidence = [self._drift_evidence(drift)] if drift else []
        deterministic_rca = rca or {
            "top_cause": "UNKNOWN",
            "confidence": "UNKNOWN",
            "algorithm_version": "deterministic-rca-v1",
        }
        value = IncidentAIInput.from_parts(
            incident={
                "kind": base["incident_kind"],
                "severity": severity,
                "status": base["status"],
                "dataset": base["dataset_slug"],
            },
            deterministic_rca=deterministic_rca,
            quality_evidence=quality_evidence,
            drift_evidence=drift_evidence,
            lineage_impact=base["impacts"],
            timeline=timeline,
        )
        return AIIncidentContext(
            incident_id=incident_id,
            deterministic_rca_id=str(rca["id"]) if rca else None,
            deterministic_rca=deterministic_rca,
            input=value,
        )

    def _severity(self, incident_id: str) -> str:
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT severity FROM incidents WHERE id = %s", (incident_id,))
            row = cursor.fetchone()
        if row is None:
            raise ValueError(f"incident not found: {incident_id}")
        return str(row[0])

    def _timeline(self, incident_id: str) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT event_type, message, created_at
                FROM incident_events WHERE incident_id = %s
                ORDER BY created_at DESC, id DESC LIMIT 20
                """,
                (incident_id,),
            )
            return [
                {"event": str(row[0]), "message": str(row[1]), "created_at": row[2].isoformat()}
                for row in cursor.fetchall()
            ]

    @staticmethod
    def _quality_evidence(value: dict[str, Any]) -> dict[str, Any]:
        return {
            "evidence_id": f"quality-result:{value['id']}",
            "source_table": "quality_results",
            "source_id": str(value["id"]),
            "reason_code": str(value["status"]),
            "text": json.dumps(
                {
                    "status": value["status"],
                    "observed": value["observed"],
                    "expected": value["expected"],
                },
                sort_keys=True,
                default=str,
            ),
        }

    @staticmethod
    def _drift_evidence(value: dict[str, Any]) -> dict[str, Any]:
        return {
            "evidence_id": f"drift-result:{value['id']}",
            "source_table": "drift_results",
            "source_id": str(value["id"]),
            "reason_code": str(value["status"]),
            "column_name": value["column_name"],
            "method": value["method"],
            "metric": value["observed_metric"],
            "threshold": value["threshold"],
            "text": json.dumps(
                {
                    "status": value["status"],
                    "column": value["column_name"],
                    "method": value["method"],
                    "metric": value["observed_metric"],
                    "threshold": value["threshold"],
                },
                sort_keys=True,
                default=str,
            ),
        }

    def find_cached(
        self, incident_id: str, prompt_version: str, fingerprint: str
    ) -> AIAnalysisRecord | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                self._SELECT
                + " WHERE incident_id = %s AND prompt_version = %s AND input_fingerprint = %s",
                (incident_id, prompt_version, fingerprint),
            )
            row = cursor.fetchone()
        return _record(row, cache_hit=True) if row else None

    def latest(self, incident_id: str) -> AIAnalysisRecord | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                self._SELECT + " WHERE incident_id = %s ORDER BY created_at DESC LIMIT 1",
                (incident_id,),
            )
            row = cursor.fetchone()
        return _record(row) if row else None

    def pending_incidents(self, limit: int) -> list[str]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT incidents.id
                FROM incidents
                LEFT JOIN LATERAL (
                    SELECT id FROM root_cause_analyses
                    WHERE incident_id = incidents.id ORDER BY created_at DESC LIMIT 1
                ) rca ON TRUE
                WHERE incidents.status IN ('OPEN', 'ACKNOWLEDGED')
                  AND NOT EXISTS (
                      SELECT 1 FROM ai_incident_analyses ai
                      WHERE ai.incident_id = incidents.id
                        AND ai.deterministic_rca_analysis_id IS NOT DISTINCT FROM rca.id
                  )
                ORDER BY CASE incidents.severity
                    WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2
                    WHEN 'WARNING' THEN 3 ELSE 4 END,
                    incidents.last_seen_at DESC
                LIMIT %s
                """,
                (max(0, min(limit, 100)),),
            )
            return [str(row[0]) for row in cursor.fetchall()]

    def persist(
        self,
        *,
        incident_id: str,
        provider: str,
        model: str,
        prompt_version: str,
        input_fingerprint: str,
        deterministic_rca_analysis_id: str | None,
        status: AICopilotStatus,
        explanation: AIExplanation,
        latency_ms: int,
        input_size: int,
        output_size: int,
        provider_request_id: str | None,
        attempts: list[dict[str, Any]],
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> AIAnalysisRecord:
        analysis_id = uuid4()
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO ai_incident_analyses(
                        id, incident_id, provider, model, prompt_version, input_fingerprint,
                        deterministic_rca_analysis_id, status, summary, probable_cause_explanation,
                        evidence_highlights_json, investigation_steps_json, uncertainties_json,
                        latency_ms, input_size, output_size, provider_request_id, attempts_json,
                        error_code, error_message
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (incident_id, prompt_version, input_fingerprint) DO NOTHING
                    """,
                    (
                        analysis_id,
                        incident_id,
                        provider,
                        model,
                        prompt_version,
                        input_fingerprint,
                        deterministic_rca_analysis_id,
                        status.value,
                        explanation.summary,
                        explanation.probable_cause_explanation,
                        Jsonb(explanation.evidence_highlights),
                        Jsonb(explanation.investigation_steps),
                        Jsonb(explanation.uncertainties),
                        max(0, latency_ms),
                        max(0, input_size),
                        max(0, output_size),
                        provider_request_id,
                        Jsonb(attempts),
                        error_code,
                        error_message,
                    ),
                )
        stored = self.find_cached(incident_id, prompt_version, input_fingerprint)
        if stored is None:
            raise RuntimeError("AI analysis was not persisted")
        return replace(stored, cache_hit=False)
