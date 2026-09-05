"""Null-rate rule for canonical fields."""

from __future__ import annotations

from opendq.quality.models import (
    QualityContext,
    QualityResult,
    QualityRuleDefinition,
    QualityStatus,
)
from opendq.quality.rules.common import result, skipped


def evaluate_completeness(context: QualityContext, rule: QualityRuleDefinition) -> QualityResult:
    if not context.observations:
        return skipped(context, rule, "NO_OBSERVATIONS")
    column = str(rule.config["column"])
    maximum = float(rule.config["max_null_rate"])
    null_records = sum(
        1 for observation in context.observations if observation.fields.get(column) is None
    )
    null_rate = null_records / len(context.observations)
    passed = null_rate <= maximum
    return result(
        context,
        rule,
        QualityStatus.PASS if passed else QualityStatus.FAIL,
        observed_value={
            "column": column,
            "null_records": null_records,
            "null_rate": round(null_rate, 6),
        },
        expected_value={"column": column, "max_null_rate": maximum},
        affected_records=null_records,
    )
