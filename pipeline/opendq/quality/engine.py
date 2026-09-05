"""Evaluate configured quality rules and persist explainable results."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID

from opendq.incidents.engine import reconcile_quality_evaluation
from opendq.logging import log_event
from opendq.quality.models import (
    QualityEvaluationSummary,
    QualityResult,
    QualityStatus,
)
from opendq.quality.registry import RULE_EVALUATORS
from opendq.quality.rules.common import result
from opendq.quality.scoring import calculate_quality_score
from opendq.storage.repository import Repository

LOGGER = logging.getLogger("opendq.quality")


def _summary(
    evaluation_run_id: UUID,
    dataset_id: int,
    dataset_slug: str,
    evaluated_at: datetime,
    results: list[QualityResult],
) -> QualityEvaluationSummary:
    statuses = [quality_result.status for quality_result in results]
    return QualityEvaluationSummary(
        evaluation_run_id=evaluation_run_id,
        dataset_id=dataset_id,
        dataset_slug=dataset_slug,
        status="SUCCESS",
        score=calculate_quality_score(statuses),
        evaluated_at=evaluated_at,
        rules_evaluated=len(results),
        rules_passed=statuses.count(QualityStatus.PASS),
        rules_warned=statuses.count(QualityStatus.WARN),
        rules_failed=statuses.count(QualityStatus.FAIL),
        rules_errored=statuses.count(QualityStatus.ERROR),
        rules_skipped=statuses.count(QualityStatus.SKIPPED),
        results=tuple(results),
    )


def evaluate_dataset(
    repository: Repository,
    dataset_slug: str,
    *,
    triggered_by: str = "cli",
    evaluated_at: datetime | None = None,
) -> QualityEvaluationSummary:
    evaluated_at = (evaluated_at or datetime.now(UTC)).astimezone(UTC)
    dataset = repository.dataset_by_slug(dataset_slug)
    if dataset is None:
        raise ValueError(f"dataset not found: {dataset_slug}")
    dataset_id, dataset_slug = dataset
    rules = repository.ensure_default_quality_rules(dataset_id, dataset_slug)
    context = repository.quality_context(dataset_id, dataset_slug, evaluated_at)
    evaluation_run_id = repository.create_quality_evaluation_run(dataset_id, triggered_by)
    results: list[QualityResult] = []
    try:
        for rule in rules:
            started = perf_counter()
            evaluator = RULE_EVALUATORS.get(rule.rule_type)
            if evaluator is None:
                quality_result = result(
                    context,
                    rule,
                    QualityStatus.ERROR,
                    details={"reason": "UNSUPPORTED_RULE_TYPE"},
                )
            else:
                try:
                    quality_result = evaluator(context, rule)
                except Exception:
                    LOGGER.exception("quality rule evaluation failed", extra={"rule": rule.slug})
                    quality_result = result(
                        context,
                        rule,
                        QualityStatus.ERROR,
                        details={"reason": "RULE_EVALUATION_ERROR"},
                    )
            results.append(quality_result)
            log_event(
                LOGGER,
                evaluation_run_id=str(evaluation_run_id),
                dataset=dataset_slug,
                rule=rule.slug,
                status=quality_result.status.value,
                duration_ms=round((perf_counter() - started) * 1000, 2),
                affected_records=quality_result.affected_records,
            )
        summary = _summary(evaluation_run_id, dataset_id, dataset_slug, evaluated_at, results)
        repository.complete_quality_evaluation(evaluation_run_id, dataset_id, results, summary)
        reconcile_quality_evaluation(repository.connection, evaluation_run_id)
        return summary
    except Exception:
        try:
            repository.fail_quality_evaluation(
                evaluation_run_id,
                error_code="QUALITY_EVALUATION_ERROR",
                error_message="quality evaluation failed before completion",
            )
        except Exception:
            LOGGER.exception("failed to finish quality evaluation run")
        raise
