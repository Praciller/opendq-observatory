"""Groq OpenAI-compatible structured-output adapter."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from opendq.ai.models import AIExplanation, IncidentAIInput
from opendq.ai.prompts import OUTPUT_SCHEMA, build_prompt
from opendq.ai.providers.base import (
    AI_INVALID_RESPONSE,
    AI_OUTPUT_VALIDATION_FAILED,
    AI_PROVIDER_TIMEOUT,
    AIProviderError,
    ProviderResult,
    code_for_status,
)


class GroqProvider:
    name = "groq"
    endpoint = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(
        self,
        api_key: str,
        model: str,
        client: httpx.Client | None = None,
        *,
        timeout_seconds: float = 8.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self._client = client or httpx.Client(timeout=timeout_seconds)

    def generate(self, value: IncidentAIInput, *, max_output_tokens: int) -> ProviderResult:
        system_prompt, user_prompt = build_prompt(value)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "max_tokens": max_output_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "incident_copilot",
                    "strict": True,
                    "schema": OUTPUT_SCHEMA,
                },
            },
        }
        started = time.perf_counter()
        try:
            response = self._client.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise AIProviderError(
                AI_PROVIDER_TIMEOUT, provider=self.name, model=self.model
            ) from exc
        except httpx.RequestError as exc:
            raise AIProviderError(
                "AI_PROVIDER_UNAVAILABLE", provider=self.name, model=self.model
            ) from exc
        latency_ms = int((time.perf_counter() - started) * 1000)
        request_id = response.headers.get("x-request-id")
        if response.status_code >= 400:
            raise AIProviderError(
                code_for_status(response.status_code),
                provider=self.name,
                model=self.model,
                request_id=request_id,
            )
        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            explanation = AIExplanation.from_mapping(
                parsed, allowed_evidence_ids=value.evidence_ids()
            )
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            code = (
                AI_OUTPUT_VALIDATION_FAILED if isinstance(exc, ValueError) else AI_INVALID_RESPONSE
            )
            raise AIProviderError(
                code, provider=self.name, model=self.model, request_id=request_id
            ) from exc
        return ProviderResult(
            provider=self.name,
            model=self.model,
            explanation=explanation,
            latency_ms=latency_ms,
            request_id=request_id or body.get("id"),
            input_size=len(user_prompt),
            output_size=len(content),
        )
