"""Incident contracts used by reconciliation and trusted CLI workflows."""

from __future__ import annotations

from enum import StrEnum


class IncidentKind(StrEnum):
    DATA_QUALITY = "DATA_QUALITY"
    EVALUATION_ERROR = "EVALUATION_ERROR"
    DATA_DRIFT = "DATA_DRIFT"


class IncidentStatus(StrEnum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class IncidentEventType(StrEnum):
    OPENED = "OPENED"
    OBSERVED_AGAIN = "OBSERVED_AGAIN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
