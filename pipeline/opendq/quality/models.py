"""Small, serializable contracts shared by quality rules and persistence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class QualityStatus(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


class QualitySeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class Observation:
    observed_at: datetime
    fields: Mapping[str, Any]
    source_event_id: str | None = None


@dataclass(frozen=True, slots=True)
class IngestionVolume:
    finished_at: datetime
    records_received: int
    records_written: int
    status: str


@dataclass(frozen=True, slots=True)
class QualityContext:
    dataset_id: int
    dataset_slug: str
    observation_type: str
    evaluated_at: datetime
    observations: tuple[Observation, ...]
    ingestion_volumes: tuple[IngestionVolume, ...] = ()


@dataclass(frozen=True, slots=True)
class QualityRuleDefinition:
    id: int
    dataset_id: int
    slug: str
    name: str
    dimension: str
    rule_type: str
    severity: str
    enabled: bool = True
    config: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class QualityResult:
    rule_id: int
    rule_slug: str
    dimension: str
    severity: str
    status: QualityStatus
    observed_value: Mapping[str, Any]
    expected_value: Mapping[str, Any]
    affected_records: int
    evaluated_records: int
    details: Mapping[str, Any] = field(default_factory=dict)
    evaluated_at: datetime | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_slug": self.rule_slug,
            "dimension": self.dimension,
            "severity": self.severity,
            "status": self.status.value,
            "observed_value": dict(self.observed_value),
            "expected_value": dict(self.expected_value),
            "affected_records": self.affected_records,
            "evaluated_records": self.evaluated_records,
            "details": dict(self.details),
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
        }


@dataclass(frozen=True, slots=True)
class QualityEvaluationSummary:
    evaluation_run_id: UUID
    dataset_id: int
    dataset_slug: str
    status: str
    score: float | None
    evaluated_at: datetime
    rules_evaluated: int
    rules_passed: int
    rules_warned: int
    rules_failed: int
    rules_errored: int
    rules_skipped: int
    results: tuple[QualityResult, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "evaluation_run_id": str(self.evaluation_run_id),
            "dataset_id": self.dataset_id,
            "dataset_slug": self.dataset_slug,
            "status": self.status,
            "score": self.score,
            "evaluated_at": self.evaluated_at.isoformat(),
            "rules_evaluated": self.rules_evaluated,
            "rules_passed": self.rules_passed,
            "rules_warned": self.rules_warned,
            "rules_failed": self.rules_failed,
            "rules_errored": self.rules_errored,
            "rules_skipped": self.rules_skipped,
            "results": [result.as_dict() for result in self.results],
        }
