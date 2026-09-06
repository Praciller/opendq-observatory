from opendq.failure_scenarios import SCENARIO_NAMES, run_scenario


def test_failure_catalog_covers_phase_six_evidence() -> None:
    assert set(SCENARIO_NAMES) == {
        "source_timeout",
        "source_invalid_payload",
        "database_unavailable",
        "weather_timestamp_gap",
        "weather_invalid_range",
        "schema_change",
        "distribution_shift",
        "quality_failure",
        "drift_incident_open",
        "incident_resolution",
        "ai_primary_failure",
        "ai_all_providers_failure",
    }


def test_scenario_evidence_is_structured_and_deterministic() -> None:
    evidence = run_scenario("quality_failure", lambda: "FAIL")

    assert evidence.scenario == "quality_failure"
    assert evidence.expected_state == "FAIL"
    assert evidence.observed_state == "FAIL"
    assert evidence.result == "PASS"
    assert evidence.duration_ms >= 0


def test_unexpected_scenario_state_is_a_failed_evidence_record() -> None:
    evidence = run_scenario("drift_incident_open", lambda: "STABLE")

    assert evidence.result == "FAIL"
    assert evidence.expected_state == "OPEN"
