"""Deterministic rolling-median volume anomaly rule."""

from __future__ import annotations

from statistics import median

from opendq.quality.models import (
    QualityContext,
    QualityResult,
    QualityRuleDefinition,
    QualityStatus,
)
from opendq.quality.rules.common import result, skipped


def evaluate_volume(context: QualityContext, rule: QualityRuleDefinition) -> QualityResult:
    minimum_runs = int(rule.config.get("minimum_baseline_runs", 5))
    lower_ratio = float(rule.config.get("lower_ratio", 0.5))
    upper_ratio = float(rule.config.get("upper_ratio", 2.0))
    if len(context.ingestion_volumes) < minimum_runs + 1:
        return skipped(
            context,
            rule,
            "INSUFFICIENT_BASELINE",
            details={
                "minimum_baseline_runs": minimum_runs,
                "available_baseline_runs": max(0, len(context.ingestion_volumes) - 1),
            },
        )
    latest, *history = context.ingestion_volumes
    baseline = float(median(volume.records_received for volume in history[:minimum_runs]))
    observed = float(latest.records_received)
    ratio = observed / baseline if baseline else None
    passed = ratio is not None and lower_ratio <= ratio <= upper_ratio
    return result(
        context,
        rule,
        QualityStatus.PASS if passed else QualityStatus.FAIL,
        observed_value={
            "latest_records_received": latest.records_received,
            "baseline_median": baseline,
            "ratio": ratio,
        },
        expected_value={
            "lower_ratio": lower_ratio,
            "upper_ratio": upper_ratio,
            "minimum_baseline_runs": minimum_runs,
        },
        affected_records=0 if passed else 1,
    )
