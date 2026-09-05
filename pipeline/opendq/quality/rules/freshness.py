"""Newest-observation age rule."""

from __future__ import annotations

from opendq.quality.models import (
    QualityContext,
    QualityResult,
    QualityRuleDefinition,
    QualityStatus,
)
from opendq.quality.rules.common import result, skipped


def evaluate_freshness(context: QualityContext, rule: QualityRuleDefinition) -> QualityResult:
    if not context.observations:
        return skipped(context, rule, "NO_OBSERVATIONS")
    maximum_age = float(rule.config["max_age_minutes"])
    latest = max(observation.observed_at for observation in context.observations)
    age_minutes = max(0.0, (context.evaluated_at - latest).total_seconds() / 60)
    passed = age_minutes <= maximum_age
    return result(
        context,
        rule,
        QualityStatus.PASS if passed else QualityStatus.FAIL,
        observed_value={
            "latest_observation_at": latest.isoformat(),
            "observed_age_minutes": round(age_minutes, 2),
        },
        expected_value={"maximum_age_minutes": maximum_age},
        affected_records=0 if passed else 1,
        details={"evaluated_at": context.evaluated_at.isoformat()},
    )
