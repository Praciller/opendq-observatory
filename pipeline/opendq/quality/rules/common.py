"""Shared result construction for quality rules."""

from __future__ import annotations

from typing import Any

from opendq.quality.models import (
    QualityContext,
    QualityResult,
    QualityRuleDefinition,
    QualityStatus,
)


def result(
    context: QualityContext,
    rule: QualityRuleDefinition,
    status: QualityStatus,
    *,
    observed_value: dict[str, Any] | None = None,
    expected_value: dict[str, Any] | None = None,
    affected_records: int = 0,
    evaluated_records: int | None = None,
    details: dict[str, Any] | None = None,
) -> QualityResult:
    return QualityResult(
        rule_id=rule.id,
        rule_slug=rule.slug,
        dimension=rule.dimension,
        severity=rule.severity,
        status=status,
        observed_value=observed_value or {},
        expected_value=expected_value or {},
        affected_records=affected_records,
        evaluated_records=(
            len(context.observations) if evaluated_records is None else evaluated_records
        ),
        details=details or {},
        evaluated_at=context.evaluated_at,
    )


def skipped(
    context: QualityContext,
    rule: QualityRuleDefinition,
    reason: str,
    *,
    details: dict[str, Any] | None = None,
) -> QualityResult:
    return result(
        context,
        rule,
        QualityStatus.SKIPPED,
        details={"reason": reason, **(details or {})},
    )
