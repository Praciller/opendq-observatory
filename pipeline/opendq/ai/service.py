"""Application service for cached, bounded incident explanations."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import psycopg

from opendq.ai.fallback import build_fallback
from opendq.ai.models import AICopilotStatus
from opendq.ai.prompts import PROMPT_VERSION
from opendq.ai.providers.gemini import GeminiProvider
from opendq.ai.providers.groq import GroqProvider
from opendq.ai.repository import AIAnalysisRecord, AIIncidentContext, AIIncidentRepository
from opendq.ai.router import ProviderRouter, RouteResult
from opendq.config import Settings
from opendq.rca.service import analyze_incident as analyze_deterministic_rca


@dataclass(frozen=True, slots=True)
class AIServiceResult:
    analysis: AIAnalysisRecord
    cache_hit: bool
    fallback_used: bool


def _fingerprint(context: AIIncidentContext) -> str:
    payload = {
        "prompt_version": PROMPT_VERSION,
        "rca_id": context.deterministic_rca_id,
        "input": context.input.to_dict(),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _router(settings: Settings) -> ProviderRouter:
    groq = (
        GroqProvider(
            settings.groq_api_key, settings.groq_model, timeout_seconds=settings.ai_timeout_seconds
        )
        if settings.groq_api_key
        else None
    )
    gemini = (
        GeminiProvider(
            settings.gemini_api_key,
            settings.gemini_model,
            timeout_seconds=settings.ai_timeout_seconds,
        )
        if settings.gemini_api_key
        else None
    )
    return ProviderRouter(groq=groq, gemini=gemini)


def _attempts(result: RouteResult) -> list[dict[str, Any]]:
    return [
        {
            "provider": attempt.provider,
            "model": attempt.model,
            "code": attempt.code,
            "latencyMs": attempt.latency_ms,
        }
        for attempt in result.attempts
    ]


def analyze_incident(
    connection: psycopg.Connection[Any],
    incident_id: str,
    settings: Settings,
    *,
    force: bool = False,
) -> AIServiceResult:
    repository = AIIncidentRepository(connection)
    context = repository.context(incident_id)
    if context is None:
        raise ValueError(f"incident not found: {incident_id}")
    if context.deterministic_rca_id is None:
        analyze_deterministic_rca(connection, incident_id)
        context = repository.context(incident_id)
        if context is None:
            raise RuntimeError("incident context disappeared after deterministic RCA")
    fingerprint = _fingerprint(context)
    if not force:
        cached = repository.find_cached(incident_id, PROMPT_VERSION, fingerprint)
        if cached is not None:
            return AIServiceResult(
                analysis=cached,
                cache_hit=True,
                fallback_used=cached.status is AICopilotStatus.FALLBACK,
            )

    route = _router(settings).explain(context.input, settings)
    if route.explanation is not None:
        explanation = route.explanation
        provider = route.provider or "unknown"
        model = route.model or "unknown"
        status = AICopilotStatus.SUCCESS
        fallback_used = False
        error_code = None
        error_message = None
    else:
        explanation = build_fallback(context.input, context.deterministic_rca)
        provider = "deterministic-fallback"
        model = str(context.deterministic_rca.get("algorithm_version") or "deterministic-rca-v1")
        status = AICopilotStatus.FALLBACK
        fallback_used = True
        error_code = route.attempts[-1].code if route.attempts else None
        error_message = "AI provider unavailable; deterministic explanation persisted."

    stored = repository.persist(
        incident_id=incident_id,
        provider=provider,
        model=model,
        prompt_version=PROMPT_VERSION,
        input_fingerprint=fingerprint,
        deterministic_rca_analysis_id=context.deterministic_rca_id,
        status=status,
        explanation=explanation,
        latency_ms=route.latency_ms,
        input_size=route.input_size,
        output_size=route.output_size,
        provider_request_id=route.request_id,
        attempts=_attempts(route),
        error_code=error_code,
        error_message=error_message,
    )
    return AIServiceResult(analysis=stored, cache_hit=False, fallback_used=fallback_used)
