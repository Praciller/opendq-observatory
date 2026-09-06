import json

import httpx
import pytest
from opendq.ai.models import IncidentAIInput
from opendq.ai.providers.base import AIProviderError
from opendq.ai.providers.gemini import GeminiProvider
from opendq.ai.providers.groq import GroqProvider
from opendq.ai.router import ProviderRouter
from opendq.config import Settings


def _input() -> IncidentAIInput:
    return IncidentAIInput.from_parts(
        incident={"kind": "DATA_DRIFT", "severity": "HIGH", "status": "OPEN", "dataset": "weather"},
        deterministic_rca={
            "top_cause": "DISTRIBUTION_SHIFT",
            "confidence": "HIGH",
            "algorithm_version": "deterministic-rca-v1",
        },
        quality_evidence=[],
        drift_evidence=[{"evidence_id": "drift-result:1", "text": "PSI exceeded threshold"}],
        lineage_impact=[],
        timeline=[],
    )


def _settings(monkeypatch, **values) -> Settings:
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    return Settings.from_env()


def test_groq_provider_parses_structured_output() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["response_format"]["type"] == "json_schema"
        assert body["messages"][0]["role"] == "system"
        assert "source data" in body["messages"][0]["content"]
        return httpx.Response(
            200,
            json={
                "id": "req-groq",
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "summary": "Distribution shift detected.",
                                    "probable_cause_explanation": (
                                        "The supplied PSI evidence supports a shift."
                                    ),
                                    "evidence_highlights": [
                                        {
                                            "evidence_id": "drift-result:1",
                                            "text": "PSI exceeded threshold.",
                                        }
                                    ],
                                    "investigation_steps": ["Review the latest source window."],
                                    "uncertainties": [],
                                }
                            )
                        }
                    }
                ],
            },
        )

    provider = GroqProvider(
        api_key="test-key",
        model="openai/gpt-oss-20b",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = provider.generate(_input(), max_output_tokens=300)

    assert result.provider == "groq"
    assert result.request_id == "req-groq"
    assert result.explanation.summary == "Distribution shift detected."


def test_groq_rate_limit_routes_to_gemini(monkeypatch) -> None:
    groq = GroqProvider(
        api_key="test-key",
        model="openai/gpt-oss-20b",
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(429, json={"error": "limited"})
            )
        ),
    )
    gemini = _successful_gemini()
    router = ProviderRouter(groq=groq, gemini=gemini)

    result = router.explain(_input(), _settings(monkeypatch, AI_COPILOT_ENABLED="true"))

    assert result.explanation is not None
    assert result.explanation.summary == "Gemini summary."
    assert [attempt.code for attempt in result.attempts] == ["AI_RATE_LIMITED"]
    assert result.provider == "gemini"


def test_both_provider_failures_return_attempts_without_raising(monkeypatch) -> None:
    groq = _failing_groq(401)
    gemini = GeminiProvider(
        api_key="test-key",
        model="gemini-3.5-flash-lite",
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(503, json={"error": "down"})
            )
        ),
    )
    result = ProviderRouter(groq=groq, gemini=gemini).explain(
        _input(), _settings(monkeypatch, AI_COPILOT_ENABLED="true")
    )

    assert result.explanation is None
    assert [attempt.code for attempt in result.attempts] == [
        "AI_AUTH_ERROR",
        "AI_PROVIDER_UNAVAILABLE",
    ]


def test_malformed_groq_output_is_rejected_without_response_body() -> None:
    provider = GroqProvider(
        api_key="test-key",
        model="openai/gpt-oss-20b",
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={"id": "req-bad", "choices": [{"message": {"content": "not-json"}}]},
                )
            )
        ),
    )

    with pytest.raises(AIProviderError) as error:
        provider.generate(_input(), max_output_tokens=300)

    assert error.value.code == "AI_OUTPUT_VALIDATION_FAILED"
    assert str(error.value) == "AI_OUTPUT_VALIDATION_FAILED"


def _successful_gemini() -> GeminiProvider:
    payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "summary": "Gemini summary.",
                                    "probable_cause_explanation": (
                                        "The drift evidence supports a shift."
                                    ),
                                    "evidence_highlights": [
                                        {"evidence_id": "drift-result:1", "text": "PSI evidence."}
                                    ],
                                    "investigation_steps": ["Inspect the source window."],
                                    "uncertainties": [],
                                }
                            )
                        }
                    ]
                }
            }
        ]
    }
    return GeminiProvider(
        api_key="test-key",
        model="gemini-3.5-flash-lite",
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ),
    )


def _failing_groq(status: int) -> GroqProvider:
    return GroqProvider(
        api_key="test-key",
        model="openai/gpt-oss-20b",
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(status, json={"error": "failed"})
            )
        ),
    )
