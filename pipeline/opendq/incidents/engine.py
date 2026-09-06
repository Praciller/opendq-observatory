"""Reconcile persisted quality evidence into deterministic incident state."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import psycopg

from opendq.drift.config import feature_for
from opendq.drift.repository import DriftRepository
from opendq.incidents.models import IncidentKind
from opendq.incidents.repository import IncidentRepository
from opendq.lineage.repository import LineageRepository
from opendq.lineage.traversal import downstream_blast_radius
from opendq.logging import log_event

LOGGER = logging.getLogger("opendq.incidents")


def _format_values(values: dict[str, Any]) -> str:
    if not values:
        return "none"
    return ", ".join(f"{key}={values[key]}" for key in sorted(values))


def _summary(result: dict[str, Any]) -> str:
    action = "evaluation error" if result["status"] == "ERROR" else "failed"
    return (
        f"{result['dataset_name']} {action} {result['rule_name']} quality rule. "
        f"Observed: {_format_values(result['observed_value'])}. "
        f"Expected: {_format_values(result['expected_value'])}."
    )


def _evidence(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "observed": result["observed_value"],
        "expected": result["expected_value"],
        "details": result["details"],
        "affected_records": result["affected_records"],
        "evaluated_records": result["evaluated_records"],
        "quality_result_id": result["quality_result_id"],
    }


def reconcile_quality_evaluation(
    connection: psycopg.Connection[Any], evaluation_run_id: UUID
) -> dict[str, int]:
    """Apply lifecycle transitions using only persisted quality results."""

    incidents = IncidentRepository(connection)
    lineage = LineageRepository(connection)
    opened = 0
    observed_again = 0
    resolved = 0
    for result in incidents.quality_results_for_run(evaluation_run_id):
        status = result["status"]
        summary = _summary(result)
        if status in {"FAIL", "ERROR"}:
            try:
                impacts = downstream_blast_radius(
                    lineage, f"dataset:{result['dataset_slug']}", max_depth=10
                )
            except ValueError:
                impacts = []
            before = incidents.list_incidents(
                dataset=result["dataset_slug"], severity=result["severity"]
            )
            incident_id = incidents.open_or_observe(
                result,
                incident_kind=(
                    IncidentKind.EVALUATION_ERROR
                    if status == "ERROR"
                    else IncidentKind.DATA_QUALITY
                ),
                summary=summary,
                evidence=_evidence(result),
                impacts=impacts,
            )
            try:
                from opendq.rca.service import analyze_incident

                analyze_incident(connection, incident_id)
            except Exception:
                LOGGER.exception("deterministic RCA failed", extra={"incident_id": incident_id})
                connection.rollback()
            if any(row["id"] == incident_id for row in before):
                observed_again += 1
            else:
                opened += 1
            log_event(
                LOGGER,
                incident_id=incident_id,
                incident_key=f"{result['dataset_slug']}:{result['rule_slug']}",
                dataset=result["dataset_slug"],
                rule=result["rule_slug"],
                event="incident_reconciled",
                status=status,
                severity=result["severity"],
                impact_count=len(impacts),
            )
        elif status == "PASS":
            resolved_id = incidents.resolve_if_active(
                result, summary=f"{result['rule_name']} recovered."
            )
            if resolved_id:
                resolved += 1
                log_event(
                    LOGGER,
                    incident_id=resolved_id,
                    incident_key=f"{result['dataset_slug']}:{result['rule_slug']}",
                    dataset=result["dataset_slug"],
                    rule=result["rule_slug"],
                    event="incident_resolved",
                    status="RESOLVED",
                    severity=result["severity"],
                )
    return {"opened": opened, "observed_again": observed_again, "resolved": resolved}


def reconcile_drift_evaluation(
    connection: psycopg.Connection[Any], evaluation_run_id: UUID
) -> dict[str, int]:
    """Open, observe, or resolve only DATA_DRIFT incidents from persisted drift results."""

    incidents = IncidentRepository(connection)
    drift = DriftRepository(connection)
    lineage = LineageRepository(connection)
    opened = 0
    observed_again = 0
    resolved = 0
    for result in drift.drift_results_for_run(evaluation_run_id):
        feature = feature_for(result["dataset_slug"], result["column_name"], result["method"])
        rule_id = drift.ensure_drift_rule(int(result["dataset_id"]), feature)
        summary = (
            f"{result['dataset_name']} {result['column_name']} {result['method']} drift detected. "
            f"Observed metric: {result['observed_metric']}; threshold: {result['threshold']}."
        )
        incident_key = f"{result['dataset_slug']}:drift:{result['column_name']}:{result['method']}"
        if result["status"] == "DRIFT":
            try:
                impacts = downstream_blast_radius(
                    lineage, f"dataset:{result['dataset_slug']}", max_depth=10
                )
            except ValueError:
                impacts = []
            before = incidents.list_incidents(dataset=result["dataset_slug"])
            incident_id = incidents.open_or_observe_drift(
                result, rule_id=rule_id, summary=summary, impacts=impacts
            )
            try:
                from opendq.rca.service import analyze_incident

                analyze_incident(connection, incident_id)
            except Exception:
                LOGGER.exception("deterministic RCA failed", extra={"incident_id": incident_id})
                connection.rollback()
            if any(
                row["id"] == incident_id and row["incident_key"] == incident_key for row in before
            ):
                observed_again += 1
            else:
                opened += 1
            log_event(
                LOGGER,
                incident_id=incident_id,
                incident_key=incident_key,
                dataset=result["dataset_slug"],
                feature=result["column_name"],
                event="drift_incident_reconciled",
                status=result["status"],
                impact_count=len(impacts),
            )
        elif result["status"] == "STABLE":
            resolved_id = incidents.resolve_drift_if_active(
                result, rule_id=rule_id, summary=f"{result['column_name']} drift recovered."
            )
            if resolved_id:
                resolved += 1
                log_event(
                    LOGGER,
                    incident_id=resolved_id,
                    incident_key=incident_key,
                    dataset=result["dataset_slug"],
                    feature=result["column_name"],
                    event="drift_incident_resolved",
                    status="STABLE",
                )
    return {"opened": opened, "observed_again": observed_again, "resolved": resolved}
