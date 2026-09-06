"""Shared provider result and error contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Protocol

from opendq.ai.models import AIExplanation, IncidentAIInput

AI_PROVIDER_UNAVAILABLE: Final = "AI_PROVIDER_UNAVAILABLE"
AI_PROVIDER_TIMEOUT: Final = "AI_PROVIDER_TIMEOUT"
AI_RATE_LIMITED: Final = "AI_RATE_LIMITED"
AI_AUTH_ERROR: Final = "AI_AUTH_ERROR"
AI_INVALID_RESPONSE: Final = "AI_INVALID_RESPONSE"
AI_OUTPUT_VALIDATION_FAILED: Final = "AI_OUTPUT_VALIDATION_FAILED"
AI_DISABLED: Final = "AI_DISABLED"


@dataclass(frozen=True, slots=True)
class ProviderResult:
    provider: str
    model: str
    explanation: AIExplanation
    latency_ms: int
    request_id: str | None
    input_size: int
    output_size: int


@dataclass(frozen=True, slots=True)
class ProviderAttempt:
    provider: str
    model: str
    code: str
    latency_ms: int


class AIProvider(Protocol):
    name: str
    model: str

    def generate(self, value: IncidentAIInput, *, max_output_tokens: int) -> ProviderResult: ...


class AIProviderError(Exception):
    """Safe-to-record provider failure without retaining response bodies."""

    def __init__(
        self,
        code: str,
        *,
        provider: str,
        model: str,
        request_id: str | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.provider = provider
        self.model = model
        self.request_id = request_id


def code_for_status(status_code: int) -> str:
    if status_code == 401 or status_code == 403:
        return AI_AUTH_ERROR
    if status_code == 408 or status_code == 504:
        return AI_PROVIDER_TIMEOUT
    if status_code == 429:
        return AI_RATE_LIMITED
    if status_code >= 500:
        return AI_PROVIDER_UNAVAILABLE
    return AI_INVALID_RESPONSE
