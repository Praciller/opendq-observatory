"""Stable result types for CLI and scheduled callers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class IngestionResult:
    source_slug: str
    status: str
    run_id: UUID | None
    records_received: int = 0
    records_written: int = 0
    records_rejected: int = 0
    error_code: str | None = None
    error_message: str | None = None
    quality_evaluation_run_id: UUID | None = None
    quality_status: str | None = None
    quality_score: float | None = None
    quality_error: str | None = None
    drift_evaluation_run_id: UUID | None = None
    drift_status: str | None = None
    drift_error: str | None = None

    @property
    def exit_code(self) -> int:
        return (
            0
            if self.status in {"SUCCESS", "NO_CHANGE"}
            and self.quality_error is None
            and self.drift_error is None
            else 1
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source_slug,
            "status": self.status,
            "run_id": str(self.run_id) if self.run_id else None,
            "records_received": self.records_received,
            "records_written": self.records_written,
            "records_rejected": self.records_rejected,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "quality_evaluation_run_id": (
                str(self.quality_evaluation_run_id) if self.quality_evaluation_run_id else None
            ),
            "quality_status": self.quality_status,
            "quality_score": self.quality_score,
            "quality_error": self.quality_error,
            "drift_evaluation_run_id": str(self.drift_evaluation_run_id)
            if self.drift_evaluation_run_id
            else None,
            "drift_status": self.drift_status,
            "drift_error": self.drift_error,
        }
