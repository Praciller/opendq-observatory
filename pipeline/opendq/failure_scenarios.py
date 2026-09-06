"""Small deterministic failure evidence helpers for local and CI verification."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter


@dataclass(frozen=True, slots=True)
class ScenarioEvidence:
    scenario: str
    expected_state: str
    observed_state: str
    result: str
    duration_ms: int

    def as_dict(self) -> dict[str, str | int]:
        return {
            "scenario": self.scenario,
            "expectedState": self.expected_state,
            "observedState": self.observed_state,
            "result": self.result,
            "durationMs": self.duration_ms,
        }


_EXPECTED_STATES = {
    "source_timeout": "FAILED",
    "source_invalid_payload": "FAILED",
    "database_unavailable": "ERROR",
    "weather_timestamp_gap": "FAIL",
    "weather_invalid_range": "FAIL",
    "schema_change": "DRIFT",
    "distribution_shift": "DRIFT",
    "quality_failure": "FAIL",
    "drift_incident_open": "OPEN",
    "incident_resolution": "RESOLVED",
    "ai_primary_failure": "FALLBACK",
    "ai_all_providers_failure": "FALLBACK",
}
SCENARIO_NAMES = tuple(_EXPECTED_STATES)


def run_scenario(scenario: str, observe: Callable[[], str]) -> ScenarioEvidence:
    if scenario not in _EXPECTED_STATES:
        raise ValueError(f"unknown failure scenario: {scenario}")
    started = perf_counter()
    observed = observe()
    duration_ms = max(0, int((perf_counter() - started) * 1000))
    expected = _EXPECTED_STATES[scenario]
    return ScenarioEvidence(
        scenario=scenario,
        expected_state=expected,
        observed_state=observed,
        result="PASS" if observed == expected else "FAIL",
        duration_ms=duration_ms,
    )
