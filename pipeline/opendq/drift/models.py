"""Serializable contracts for drift runs and results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from opendq.drift.engine import DriftStatus


@dataclass(frozen=True, slots=True)
class DriftFeature:
    dataset_slug: str
    column_name: str
    method: str
    threshold: float
    severity: str = "WARNING"
    minimum_samples: int = 5
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class DriftResult:
    column_name: str
    method: str
    status: DriftStatus
    severity: str
    baseline_id: int | None
    baseline_version: int | None
    observed_metric: float | None
    threshold: float | None
    baseline_sample_count: int
    current_sample_count: int
    details: dict[str, Any] = field(default_factory=dict)
    baseline_window_start: datetime | None = None
    baseline_window_end: datetime | None = None
    current_window_start: datetime | None = None
    current_window_end: datetime | None = None


@dataclass(frozen=True, slots=True)
class DriftEvaluationSummary:
    evaluation_run_id: UUID
    dataset_id: int
    dataset_slug: str
    status: str
    evaluated_at: datetime
    checks_evaluated: int
    checks_stable: int
    checks_warned: int
    checks_drifted: int
    checks_skipped: int
    checks_errored: int
    results: tuple[DriftResult, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "evaluation_run_id": str(self.evaluation_run_id),
            "dataset_id": self.dataset_id,
            "dataset_slug": self.dataset_slug,
            "status": self.status,
            "evaluated_at": self.evaluated_at.isoformat(),
            "checks_evaluated": self.checks_evaluated,
            "checks_stable": self.checks_stable,
            "checks_warned": self.checks_warned,
            "checks_drifted": self.checks_drifted,
            "checks_skipped": self.checks_skipped,
            "checks_errored": self.checks_errored,
            "results": [
                {
                    "column_name": result.column_name,
                    "method": result.method,
                    "status": result.status.value,
                    "severity": result.severity,
                    "baseline_id": result.baseline_id,
                    "baseline_version": result.baseline_version,
                    "observed_metric": result.observed_metric,
                    "threshold": result.threshold,
                    "baseline_sample_count": result.baseline_sample_count,
                    "current_sample_count": result.current_sample_count,
                    "details": result.details,
                    "baseline_window_start": result.baseline_window_start.isoformat()
                    if result.baseline_window_start
                    else None,
                    "baseline_window_end": result.baseline_window_end.isoformat()
                    if result.baseline_window_end
                    else None,
                    "current_window_start": result.current_window_start.isoformat()
                    if result.current_window_start
                    else None,
                    "current_window_end": result.current_window_end.isoformat()
                    if result.current_window_end
                    else None,
                }
                for result in self.results
            ],
        }
