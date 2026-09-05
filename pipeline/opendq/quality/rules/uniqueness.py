"""Logical uniqueness rule complementary to database constraints."""

from __future__ import annotations

from typing import Any

from opendq.quality.models import (
    QualityContext,
    QualityResult,
    QualityRuleDefinition,
    QualityStatus,
)
from opendq.quality.rules.common import result, skipped


def _key(context: QualityContext, observation: Any) -> tuple[Any, ...]:
    if context.observation_type == "earthquake":
        return (observation.source_event_id,)
    return (
        observation.fields.get("latitude"),
        observation.fields.get("longitude"),
        observation.observed_at,
    )


def evaluate_uniqueness(context: QualityContext, rule: QualityRuleDefinition) -> QualityResult:
    if not context.observations:
        return skipped(context, rule, "NO_OBSERVATIONS")
    keys = [_key(context, observation) for observation in context.observations]
    duplicate_records = len(keys) - len(set(keys))
    passed = duplicate_records == 0
    return result(
        context,
        rule,
        QualityStatus.PASS if passed else QualityStatus.FAIL,
        observed_value={"unique_keys": len(set(keys)), "duplicate_records": duplicate_records},
        expected_value={"duplicate_records": 0},
        affected_records=duplicate_records,
    )
