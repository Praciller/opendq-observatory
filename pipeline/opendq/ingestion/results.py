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

    @property
    def exit_code(self) -> int:
        return 0 if self.status in {"SUCCESS", "NO_CHANGE"} else 1

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
        }
