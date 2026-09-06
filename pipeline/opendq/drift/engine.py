"""Small, explainable drift algorithms with bounded inputs."""

from __future__ import annotations

from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite, log, sqrt
from statistics import mean
from typing import Any


class DriftStatus(StrEnum):
    STABLE = "STABLE"
    WARN = "WARN"
    DRIFT = "DRIFT"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True, slots=True)
class NumericDriftResult:
    status: DriftStatus
    metric: float | None
    threshold: float
    sample_count: int
    details: dict[str, Any] = field(default_factory=dict)


def _clean_numeric(values: list[float | int]) -> list[float]:
    cleaned = [float(value) for value in values if isfinite(float(value))]
    return cleaned


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("cannot calculate a quantile without values")
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _bin_edges(values: list[float]) -> list[float]:
    edges = sorted(
        {
            round(_quantile(values, probability), 12)
            for probability in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
        }
    )
    return edges


def _distribution(values: list[float], edges: list[float]) -> list[float]:
    counts = [0] * (len(edges) + 1)
    for value in values:
        counts[bisect_right(edges, value)] += 1
    total = len(values)
    return [count / total for count in counts]


def _psi(expected: list[float], actual: list[float], epsilon: float) -> float:
    return sum(
        (actual_pct - expected_pct) * log((actual_pct + epsilon) / (expected_pct + epsilon))
        for expected_pct, actual_pct in zip(expected, actual, strict=True)
    )


def location_shift(baseline: list[float | int], current: list[float | int]) -> dict[str, float]:
    baseline_values = _clean_numeric(baseline)
    current_values = _clean_numeric(current)
    if not baseline_values or not current_values:
        raise ValueError("location shift requires two non-empty samples")
    baseline_median = _quantile(baseline_values, 0.5)
    current_median = _quantile(current_values, 0.5)
    baseline_p95 = _quantile(baseline_values, 0.95)
    current_p95 = _quantile(current_values, 0.95)
    baseline_mean = mean(baseline_values)
    current_mean = mean(current_values)
    spread = max(_quantile(baseline_values, 0.75) - _quantile(baseline_values, 0.25), 1e-9)
    return {
        "baseline_mean": baseline_mean,
        "current_mean": current_mean,
        "mean_shift": current_mean - baseline_mean,
        "baseline_median": baseline_median,
        "current_median": current_median,
        "median_shift": current_median - baseline_median,
        "baseline_p95": baseline_p95,
        "current_p95": current_p95,
        "p95_shift": current_p95 - baseline_p95,
        "normalized_median_shift": (current_median - baseline_median) / spread,
    }


def evaluate_numeric_drift(
    *,
    baseline: list[float | int],
    current: list[float | int],
    threshold: float,
    minimum_samples: int = 5,
    epsilon: float = 1e-6,
) -> NumericDriftResult:
    baseline_values = _clean_numeric(baseline)
    current_values = _clean_numeric(current)
    if len(baseline_values) < minimum_samples:
        return NumericDriftResult(
            DriftStatus.SKIPPED,
            None,
            threshold,
            len(current_values),
            {"reason": "INSUFFICIENT_BASELINE", "baseline_sample_count": len(baseline_values)},
        )
    if len(current_values) < minimum_samples:
        return NumericDriftResult(
            DriftStatus.SKIPPED,
            None,
            threshold,
            len(current_values),
            {"reason": "INSUFFICIENT_CURRENT", "current_sample_count": len(current_values)},
        )
    edges = _bin_edges(baseline_values)
    baseline_distribution = _distribution(baseline_values, edges)
    current_distribution = _distribution(current_values, edges)
    metric = _psi(baseline_distribution, current_distribution, epsilon)
    warning_threshold = threshold / 2
    status = (
        DriftStatus.DRIFT
        if metric >= threshold
        else DriftStatus.WARN
        if metric >= warning_threshold
        else DriftStatus.STABLE
    )
    return NumericDriftResult(
        status,
        metric,
        threshold,
        len(current_values),
        {
            "baseline_bins": edges,
            "baseline_distribution": baseline_distribution,
            "current_distribution": current_distribution,
            "warning_threshold": warning_threshold,
            "epsilon": epsilon,
            "location_shift": location_shift(baseline_values, current_values),
        },
    )


def numeric_baseline_summary(values: list[float | int]) -> tuple[dict[str, Any], dict[str, Any]]:
    cleaned = _clean_numeric(values)
    if not cleaned:
        raise ValueError("numeric baseline requires values")
    edges = _bin_edges(cleaned)
    return {
        "mean": mean(cleaned),
        "median": _quantile(cleaned, 0.5),
        "p25": _quantile(cleaned, 0.25),
        "p75": _quantile(cleaned, 0.75),
        "p95": _quantile(cleaned, 0.95),
        "minimum": min(cleaned),
        "maximum": max(cleaned),
        "standard_deviation": (
            sqrt(sum((value - mean(cleaned)) ** 2 for value in cleaned) / (len(cleaned) - 1))
            if len(cleaned) > 1
            else 0.0
        ),
        "quantiles": {
            str(probability): _quantile(cleaned, probability)
            for probability in (0.25, 0.5, 0.75, 0.95)
        },
        "sample_count": len(cleaned),
    }, {"bins": edges, "distribution": _distribution(cleaned, edges)}


def evaluate_numeric_distribution(
    *,
    baseline_statistics: dict[str, Any],
    baseline_distribution: dict[str, Any],
    current: list[float | int],
    threshold: float,
    minimum_samples: int = 5,
    epsilon: float = 1e-6,
) -> NumericDriftResult:
    current_values = _clean_numeric(current)
    baseline_sample_count = int(baseline_statistics.get("sample_count", 0))
    if baseline_sample_count < minimum_samples:
        return NumericDriftResult(
            DriftStatus.SKIPPED,
            None,
            threshold,
            len(current_values),
            {"reason": "INSUFFICIENT_BASELINE", "baseline_sample_count": baseline_sample_count},
        )
    if len(current_values) < minimum_samples:
        return NumericDriftResult(
            DriftStatus.SKIPPED,
            None,
            threshold,
            len(current_values),
            {"reason": "INSUFFICIENT_CURRENT", "current_sample_count": len(current_values)},
        )
    edges = [float(value) for value in baseline_distribution.get("bins", [])]
    expected = [float(value) for value in baseline_distribution.get("distribution", [])]
    if len(expected) != len(edges) + 1:
        raise ValueError("baseline distribution bins are inconsistent")
    actual = _distribution(current_values, edges)
    metric = _psi(expected, actual, epsilon)
    warning_threshold = threshold / 2
    status = (
        DriftStatus.DRIFT
        if metric >= threshold
        else DriftStatus.WARN
        if metric >= warning_threshold
        else DriftStatus.STABLE
    )
    baseline_median = float(baseline_statistics["median"])
    baseline_p95 = float(baseline_statistics["p95"])
    baseline_mean = float(baseline_statistics["mean"])
    baseline_spread = max(
        float(baseline_statistics.get("p75", baseline_median))
        - float(baseline_statistics.get("p25", baseline_median)),
        1e-9,
    )
    current_median = _quantile(current_values, 0.5)
    current_p95 = _quantile(current_values, 0.95)
    current_mean = mean(current_values)
    return NumericDriftResult(
        status,
        metric,
        threshold,
        len(current_values),
        {
            "baseline_bins": edges,
            "baseline_distribution": expected,
            "current_distribution": actual,
            "warning_threshold": warning_threshold,
            "epsilon": epsilon,
            "location_shift": {
                "baseline_mean": baseline_mean,
                "current_mean": current_mean,
                "mean_shift": current_mean - baseline_mean,
                "baseline_median": baseline_median,
                "current_median": current_median,
                "median_shift": current_median - baseline_median,
                "baseline_p95": baseline_p95,
                "current_p95": current_p95,
                "p95_shift": current_p95 - baseline_p95,
                "normalized_median_shift": (current_median - baseline_median) / baseline_spread,
            },
        },
    )


def categorical_tvd(baseline: list[str], current: list[str]) -> float:
    if not baseline or not current:
        raise ValueError("categorical TVD requires two non-empty samples")
    baseline_counts = Counter(baseline)
    current_counts = Counter(current)
    categories = sorted(set(baseline_counts) | set(current_counts))
    baseline_total = len(baseline)
    current_total = len(current)
    return 0.5 * sum(
        abs(
            baseline_counts.get(category, 0) / baseline_total
            - current_counts.get(category, 0) / current_total
        )
        for category in categories
    )


def compare_schema(
    baseline: dict[str, dict[str, Any]], current: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    differences: list[dict[str, Any]] = []
    for field_name in sorted(set(baseline) | set(current)):
        if field_name not in baseline:
            differences.append(
                {"field": field_name, "kind": "ADDED", "current": current[field_name]}
            )
        elif field_name not in current:
            differences.append(
                {"field": field_name, "kind": "REMOVED", "baseline": baseline[field_name]}
            )
        elif baseline[field_name] != current[field_name]:
            differences.append(
                {
                    "field": field_name,
                    "kind": "TYPE_CHANGED"
                    if baseline[field_name].get("type") != current[field_name].get("type")
                    else "NULLABILITY_CHANGED",
                    "baseline": baseline[field_name],
                    "current": current[field_name],
                }
            )
    return differences
