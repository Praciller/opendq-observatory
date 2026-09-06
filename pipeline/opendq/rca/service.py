"""Deterministic RCA over persisted quality, drift, ingestion, and lineage evidence."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import psycopg

from opendq.logging import log_event
from opendq.rca.engine import EvidenceSignal, rank_root_causes
from opendq.rca.repository import RCARepository

ALGORITHM_VERSION = "deterministic-rca-v1"


def _quality_signal(context: dict[str, Any], result: dict[str, Any]) -> EvidenceSignal:
    rule_slug = context["rule_slug"]
    if "freshness" in rule_slug:
        cause, reason, weight = "FRESHNESS_DELAY", "freshness_rule_failed", 10.0
    elif "gap" in rule_slug:
        cause, reason, weight = "TIMESTAMP_GAP", "timestamp_gap_rule_failed", 10.0
    elif "volume" in rule_slug:
        cause, reason, weight = "VOLUME_CHANGE", "volume_rule_failed", 10.0
    elif context["incident_kind"] == "EVALUATION_ERROR":
        cause, reason, weight = "DATABASE_OR_PIPELINE_ERROR", "quality_evaluation_error", 12.0
    else:
        cause, reason, weight = "INVALID_VALUES", "quality_contract_failed", 10.0
    return EvidenceSignal(
        "QUALITY_RESULT",
        cause,
        weight,
        reason,
        {
            "source_table": "quality_results",
            "observed": result["observed"],
            "expected": result["expected"],
            "details": result["details"],
        },
        str(result["id"]),
    )


def _signals(repository: RCARepository, context: dict[str, Any]) -> list[EvidenceSignal]:
    signals: list[EvidenceSignal] = []
    quality = (
        repository.quality_result(context["latest_quality_result_id"])
        if context["latest_quality_result_id"]
        else None
    )
    if quality is not None:
        signals.append(_quality_signal(context, quality))
    drift = (
        repository.drift_result(context["latest_drift_result_id"])
        if context["latest_drift_result_id"]
        else None
    )
    if drift is not None and drift["status"] == "DRIFT":
        cause = "SCHEMA_CHANGE" if drift["method"] == "SCHEMA_DIFF" else "DISTRIBUTION_SHIFT"
        signals.append(
            EvidenceSignal(
                "DRIFT_RESULT",
                cause,
                12.0 if cause == "SCHEMA_CHANGE" else 10.0,
                "schema_difference_detected"
                if cause == "SCHEMA_CHANGE"
                else "psi_distribution_shift",
                {
                    "source_table": "drift_results",
                    "column_name": drift["column_name"],
                    "metric": drift["observed_metric"],
                    "threshold": drift["threshold"],
                    "details": drift["details"],
                },
                str(drift["id"]),
            )
        )
    ingestion = repository.latest_ingestion(context["dataset_id"])
    if ingestion is not None and ingestion["status"] == "FAILED":
        signals.append(
            EvidenceSignal(
                "INGESTION_RUN",
                "UPSTREAM_SOURCE_FAILURE",
                12.0,
                "ingestion_failed",
                {"source_table": "ingestion_runs", "error_code": ingestion["error_code"]},
                ingestion["run_id"],
            )
        )
        if repository.upstream_sources(context["dataset_slug"]):
            signals.append(
                EvidenceSignal(
                    "LINEAGE_CONTEXT",
                    "UPSTREAM_SOURCE_FAILURE",
                    2.0,
                    "upstream_source_in_lineage",
                    {
                        "source_table": "lineage_edges",
                        "upstream_sources": repository.upstream_sources(context["dataset_slug"]),
                    },
                )
            )
    if not signals:
        signals.append(
            EvidenceSignal("INCIDENT", "UNKNOWN", 0.0, "no_persisted_supporting_evidence")
        )
    return signals


def _summary(top: Any, candidates: list[Any], context: dict[str, Any]) -> str:
    evidence_lines = [signal.reason_code.replace("_", " ").lower() for signal in top.evidence]
    evidence = "; ".join(evidence_lines) if evidence_lines else "no supporting evidence"
    return (
        f"Probable cause: {top.cause.replace('_', ' ').lower()}. "
        f"Evidence: {evidence}. Confidence: {top.confidence}. "
        f"Affected downstream assets: {len(context['impacts'])}."
    )


def analyze_incident(connection: psycopg.Connection[Any], incident_id: str) -> dict[str, Any]:
    repository = RCARepository(connection)
    context = repository.incident_context(incident_id)
    if context is None:
        raise ValueError(f"incident not found: {incident_id}")
    signals = _signals(repository, context)
    candidates = rank_root_causes(signals)
    top = candidates[0]
    fingerprint_payload = [
        [signal.cause, signal.reason_code, signal.weight, signal.details] for signal in signals
    ]
    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "incident": incident_id,
                "algorithm": ALGORITHM_VERSION,
                "signals": sorted(fingerprint_payload),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    summary = _summary(top, candidates, context)
    analysis_id = repository.persist(
        incident_id=incident_id,
        top_cause=top,
        candidates=candidates,
        algorithm_version=ALGORITHM_VERSION,
        fingerprint=fingerprint,
        summary=summary,
        details={
            "candidates": [
                {
                    "cause": item.cause,
                    "score": item.score,
                    "rank": item.rank,
                    "confidence": item.confidence,
                }
                for item in candidates
            ],
            "affected_asset_count": len(context["impacts"]),
        },
    )
    log_event(
        __import__("logging").getLogger("opendq.rca"),
        analysis_id=analysis_id,
        incident_id=incident_id,
        top_cause=top.cause,
        confidence=top.confidence,
        candidate_count=len(candidates),
        evidence_count=len(signals),
        algorithm_version=ALGORITHM_VERSION,
    )
    result = repository.latest(incident_id)
    if result is None:
        raise RuntimeError("RCA analysis was not persisted")
    return result
