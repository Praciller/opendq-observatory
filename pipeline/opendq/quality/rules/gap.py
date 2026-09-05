"""Timestamp continuity rule for regularly sampled datasets."""

from __future__ import annotations

from opendq.quality.models import (
    QualityContext,
    QualityResult,
    QualityRuleDefinition,
    QualityStatus,
)
from opendq.quality.rules.common import result, skipped


def evaluate_timestamp_gap(context: QualityContext, rule: QualityRuleDefinition) -> QualityResult:
    if context.observation_type != "weather":
        return skipped(context, rule, "NOT_APPLICABLE_TO_IRREGULAR_EVENTS")
    if len(context.observations) < 2:
        return skipped(context, rule, "INSUFFICIENT_OBSERVATIONS")
    expected = float(rule.config["expected_interval_minutes"])
    maximum = float(rule.config["maximum_allowed_gap_minutes"])
    timestamps = sorted(observation.observed_at for observation in context.observations)
    gaps = [
        (right - left).total_seconds() / 60
        for left, right in zip(timestamps, timestamps[1:], strict=False)
    ]
    violations = [gap for gap in gaps if gap > maximum]
    largest = max(gaps)
    passed = not violations
    return result(
        context,
        rule,
        QualityStatus.PASS if passed else QualityStatus.FAIL,
        observed_value={"largest_gap_minutes": round(largest, 2), "gap_count": len(violations)},
        expected_value={
            "expected_interval_minutes": expected,
            "maximum_allowed_gap_minutes": maximum,
        },
        affected_records=len(violations),
        details={"gaps_minutes": [round(gap, 2) for gap in violations]},
    )
