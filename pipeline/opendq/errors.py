"""Small, explicit ingestion error taxonomy."""

from enum import StrEnum


class ErrorCode(StrEnum):
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    SOURCE_TIMEOUT = "SOURCE_TIMEOUT"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    CONTRACT_VIOLATION = "CONTRACT_VIOLATION"
    DATABASE_ERROR = "DATABASE_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"


class IngestionError(Exception):
    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
