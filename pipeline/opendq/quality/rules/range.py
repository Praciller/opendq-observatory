"""Numeric validity/range rule."""

from __future__ import annotations

import math
from typing import Any

from opendq.quality.models import (
    QualityContext,
    QualityResult,
    QualityRuleDefinition,
    QualityStatus,
)
from opendq.quality.rules.common import result, skipped


def evaluate_range(context: QualityContext, rule: QualityRuleDefinition) -> QualityResult:
    if not context.observations:
        return skipped(context, rule, "NO_OBSERVATIONS")
    column = str(rule.config["column"])
    minimum = rule.config.get("min")
    maximum = rule.config.get("max")
    values = [observation.fields.get(column) for observation in context.observations]
    invalid = []
    numeric = []
    for value in values:
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
        ):
            invalid.append(value)
            continue
        numeric.append(float(value))
        if (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
            invalid.append(value)
    passed = not invalid
    observed: dict[str, Any] = {"column": column, "invalid_records": len(invalid)}
    if numeric:
        observed.update({"minimum": min(numeric), "maximum": max(numeric)})
    return result(
        context,
        rule,
        QualityStatus.PASS if passed else QualityStatus.FAIL,
        observed_value=observed,
        expected_value={"column": column, "min": minimum, "max": maximum},
        affected_records=len(invalid),
    )
