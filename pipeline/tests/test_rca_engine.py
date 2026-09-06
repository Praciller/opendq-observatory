from opendq.rca.engine import EvidenceSignal, rank_root_causes


def test_source_failure_ranks_above_downstream_symptom() -> None:
    ranked = rank_root_causes(
        [
            EvidenceSignal("SOURCE_FAILURE", "UPSTREAM_SOURCE_FAILURE", 10, "source_failed"),
            EvidenceSignal("QUALITY", "FRESHNESS_DELAY", 5, "freshness_failed"),
        ]
    )

    assert ranked[0].cause == "UPSTREAM_SOURCE_FAILURE"
    assert ranked[0].score > ranked[1].score


def test_ambiguous_multiple_signals_lower_confidence_deterministically() -> None:
    ranked = rank_root_causes(
        [
            EvidenceSignal("QUALITY", "FRESHNESS_DELAY", 5, "freshness_failed"),
            EvidenceSignal("QUALITY", "TIMESTAMP_GAP", 5, "gap_failed"),
        ]
    )

    assert ranked[0].confidence == "MEDIUM"
    assert ranked[0].cause == "FRESHNESS_DELAY"


def test_no_useful_evidence_is_unknown() -> None:
    ranked = rank_root_causes([])

    assert len(ranked) == 1
    assert ranked[0].cause == "UNKNOWN"
    assert ranked[0].confidence == "UNKNOWN"
