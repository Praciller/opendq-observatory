"""Baseline creation and bounded drift evaluation orchestration."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from opendq.drift.config import SCHEMA_COLUMN, features_for_dataset
from opendq.drift.engine import (
    DriftStatus,
    compare_schema,
    evaluate_numeric_distribution,
    numeric_baseline_summary,
)
from opendq.drift.models import DriftEvaluationSummary, DriftFeature, DriftResult
from opendq.drift.repository import DriftRepository
from opendq.incidents.engine import reconcile_drift_evaluation
from opendq.logging import log_event

LOGGER = logging.getLogger("opendq.drift")


def _baseline_type(feature: DriftFeature) -> str:
    return "SCHEMA" if feature.method == "SCHEMA_DIFF" else "NUMERIC"


def create_baselines(connection: Any, dataset_slug: str) -> list[dict[str, Any]]:
    repository = DriftRepository(connection)
    dataset = repository.dataset(dataset_slug)
    if dataset is None:
        raise ValueError(f"dataset not found: {dataset_slug}")
    dataset_id, _ = dataset
    if not repository.current_schema(dataset_id):
        repository.ensure_schema_version(dataset_id, dataset_slug)
    output: list[dict[str, Any]] = []
    for feature in features_for_dataset(dataset_slug):
        if not feature.enabled:
            continue
        baseline_type = _baseline_type(feature)
        if feature.method == "SCHEMA_DIFF":
            schema = repository.current_schema(dataset_id)
            if not schema:
                output.append({"column_name": feature.column_name, "status": "INSUFFICIENT_DATA"})
                continue
            created = repository.create_baseline(
                dataset_id,
                column_name=SCHEMA_COLUMN,
                baseline_type=baseline_type,
                window_start=None,
                window_end=None,
                sample_count=1,
                statistics={"schema_hash": "deterministic-current"},
                distribution={"schema": schema},
                created_from_run_id=repository.latest_ingestion_run(dataset_id),
            )
            output.append(
                {"column_name": feature.column_name, "status": "BASELINE_CREATED", **created}
            )
            continue
        rows = repository.observations(dataset_id, feature.column_name, limit=1000)
        values = [row[1] for row in rows]
        if len(values) < feature.minimum_samples:
            output.append(
                {
                    "column_name": feature.column_name,
                    "status": "INSUFFICIENT_DATA",
                    "sample_count": len(values),
                }
            )
            continue
        statistics, distribution = numeric_baseline_summary(values)
        created = repository.create_baseline(
            dataset_id,
            column_name=feature.column_name,
            baseline_type=baseline_type,
            window_start=rows[0][0],
            window_end=rows[-1][0],
            sample_count=len(values),
            statistics=statistics,
            distribution=distribution,
            created_from_run_id=repository.latest_ingestion_run(dataset_id),
        )
        output.append(
            {
                "column_name": feature.column_name,
                "status": "BASELINE_CREATED",
                "sample_count": len(values),
                **created,
            }
        )
    return output


def _skipped_result(feature: DriftFeature, reason: str, **details: Any) -> DriftResult:
    return DriftResult(
        column_name=feature.column_name,
        method=feature.method,
        status=DriftStatus.SKIPPED,
        severity=feature.severity,
        baseline_id=None,
        baseline_version=None,
        observed_metric=None,
        threshold=feature.threshold,
        baseline_sample_count=0,
        current_sample_count=0,
        details={"reason": reason, **details},
    )


def evaluate_dataset(
    connection: Any,
    dataset_slug: str,
    *,
    triggered_by: str = "cli",
    evaluated_at: datetime | None = None,
) -> DriftEvaluationSummary:
    evaluated_at = (evaluated_at or datetime.now(UTC)).astimezone(UTC)
    repository = DriftRepository(connection)
    dataset = repository.dataset(dataset_slug)
    if dataset is None:
        raise ValueError(f"dataset not found: {dataset_slug}")
    dataset_id, _ = dataset
    run_id = repository.create_evaluation_run(dataset_id, triggered_by)
    results: list[DriftResult] = []
    try:
        for feature in features_for_dataset(dataset_slug):
            baseline = repository.active_baseline(
                dataset_id, feature.column_name, _baseline_type(feature)
            )
            if baseline is None:
                result = _skipped_result(feature, "BASELINE_UNAVAILABLE")
            elif feature.method == "SCHEMA_DIFF":
                current_schema = repository.current_schema(dataset_id)
                baseline_schema = dict(baseline["distribution"].get("schema", {}))
                differences = compare_schema(baseline_schema, current_schema)
                result = DriftResult(
                    column_name=feature.column_name,
                    method=feature.method,
                    status=DriftStatus.DRIFT if differences else DriftStatus.STABLE,
                    severity=feature.severity,
                    baseline_id=baseline["id"],
                    baseline_version=baseline["baseline_version"],
                    observed_metric=float(len(differences)),
                    threshold=0.0,
                    baseline_sample_count=baseline["sample_count"],
                    current_sample_count=1,
                    details={"differences": differences},
                )
            else:
                rows = repository.observations(
                    dataset_id,
                    feature.column_name,
                    after=baseline["window_end"],
                    limit=100,
                    latest=True,
                )
                evaluation = evaluate_numeric_distribution(
                    baseline_statistics=baseline["statistics"],
                    baseline_distribution=baseline["distribution"],
                    current=[row[1] for row in rows],
                    threshold=feature.threshold,
                    minimum_samples=feature.minimum_samples,
                )
                result = DriftResult(
                    column_name=feature.column_name,
                    method=feature.method,
                    status=evaluation.status,
                    severity=feature.severity,
                    baseline_id=baseline["id"],
                    baseline_version=baseline["baseline_version"],
                    observed_metric=evaluation.metric,
                    threshold=evaluation.threshold,
                    baseline_sample_count=baseline["sample_count"],
                    current_sample_count=evaluation.sample_count,
                    details=evaluation.details,
                    baseline_window_start=baseline["window_start"],
                    baseline_window_end=baseline["window_end"],
                    current_window_start=rows[0][0] if rows else None,
                    current_window_end=rows[-1][0] if rows else None,
                )
            results.append(result)
            log_event(
                LOGGER,
                drift_run_id=str(run_id),
                dataset=dataset_slug,
                feature=feature.column_name,
                method=feature.method,
                status=result.status.value,
                metric=result.observed_metric,
                threshold=result.threshold,
                baseline_version=result.baseline_version,
                sample_count=result.current_sample_count,
            )
        status = (
            "NO_BASELINE"
            if all(
                result.status is DriftStatus.SKIPPED
                and result.details.get("reason") == "BASELINE_UNAVAILABLE"
                for result in results
            )
            else "PARTIAL"
            if any(result.status in {DriftStatus.SKIPPED, DriftStatus.ERROR} for result in results)
            else "SUCCESS"
        )
        repository.complete_evaluation(
            run_id, dataset_id, results, status=status, evaluated_at=evaluated_at
        )
        reconciliation = reconcile_drift_evaluation(connection, run_id)
        log_event(
            LOGGER,
            drift_run_id=str(run_id),
            dataset=dataset_slug,
            event="drift_reconciled",
            **reconciliation,
        )
        return DriftEvaluationSummary(
            evaluation_run_id=run_id,
            dataset_id=dataset_id,
            dataset_slug=dataset_slug,
            status=status,
            evaluated_at=evaluated_at,
            checks_evaluated=len(results),
            checks_stable=sum(result.status is DriftStatus.STABLE for result in results),
            checks_warned=sum(result.status is DriftStatus.WARN for result in results),
            checks_drifted=sum(result.status is DriftStatus.DRIFT for result in results),
            checks_skipped=sum(result.status is DriftStatus.SKIPPED for result in results),
            checks_errored=sum(result.status is DriftStatus.ERROR for result in results),
            results=tuple(results),
        )
    except Exception as exc:
        repository.fail_evaluation(run_id, str(exc))
        raise
