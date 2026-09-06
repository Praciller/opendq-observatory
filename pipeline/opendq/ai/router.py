"""Bounded Groq-first, Gemini-second provider routing."""

from __future__ import annotations

from dataclasses import dataclass

from opendq.ai.models import AIExplanation, IncidentAIInput
from opendq.ai.providers.base import (
    AI_DISABLED,
    AIProvider,
    AIProviderError,
    ProviderAttempt,
)
from opendq.config import Settings


@dataclass(frozen=True, slots=True)
class RouteResult:
    explanation: AIExplanation | None
    provider: str | None
    model: str | None
    attempts: list[ProviderAttempt]
    latency_ms: int
    input_size: int = 0
    output_size: int = 0
    request_id: str | None = None


class ProviderRouter:
    def __init__(self, *, groq: AIProvider | None, gemini: AIProvider | None) -> None:
        self.groq = groq
        self.gemini = gemini

    def explain(self, value: IncidentAIInput, settings: Settings) -> RouteResult:
        if not settings.ai_copilot_enabled:
            return RouteResult(
                explanation=None,
                provider=None,
                model=None,
                attempts=[ProviderAttempt("router", "none", AI_DISABLED, 0)],
                latency_ms=0,
                input_size=len(str(value.to_dict())),
            )

        attempts: list[ProviderAttempt] = []
        for provider_name, provider in (("groq", self.groq), ("gemini", self.gemini)):
            if provider is None:
                continue
            try:
                result = provider.generate(value, max_output_tokens=settings.ai_max_output_tokens)
            except AIProviderError as exc:
                attempts.append(
                    ProviderAttempt(
                        provider=provider_name,
                        model=getattr(provider, "model", "unknown"),
                        code=exc.code,
                        latency_ms=0,
                    )
                )
                continue
            return RouteResult(
                explanation=result.explanation,
                provider=result.provider,
                model=result.model,
                attempts=attempts,
                latency_ms=result.latency_ms,
                input_size=result.input_size,
                output_size=result.output_size,
                request_id=result.request_id,
            )
        if not attempts:
            attempts = [ProviderAttempt("router", "none", AI_DISABLED, 0)]
        return RouteResult(
            explanation=None,
            provider=None,
            model=None,
            attempts=attempts,
            latency_ms=sum(item.latency_ms for item in attempts),
            input_size=len(str(value.to_dict())),
        )
