"""Transparent quality score aggregation."""

from __future__ import annotations

from collections.abc import Iterable

from opendq.quality.models import QualityStatus


def calculate_quality_score(statuses: Iterable[QualityStatus | str]) -> float | None:
    weights = {QualityStatus.PASS: 1.0, QualityStatus.WARN: 0.5, QualityStatus.FAIL: 0.0}
    scored = [
        weights[QualityStatus(status)] for status in statuses if QualityStatus(status) in weights
    ]
    if not scored:
        return None
    return round(sum(scored) / len(scored) * 100, 1)
