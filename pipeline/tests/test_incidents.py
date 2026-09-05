from datetime import UTC, datetime

from opendq.incidents.engine import reconcile_quality_evaluation
from opendq.incidents.repository import IncidentRepository
from opendq.lineage.seed import seed_lineage
from opendq.quality.models import QualityEvaluationSummary, QualityResult, QualityStatus


def _dataset_and_rule(repository):
    _, dataset_id = repository.ensure_source_dataset(
        source_slug="open-meteo",
        source_name="Open-Meteo",
        description="Fixture source",
        base_url="https://example.test",
        dataset_slug="hourly-weather",
        dataset_name="Hourly weather",
        schema_version="1",
    )
    rule = repository.ensure_default_quality_rules(dataset_id, "hourly-weather")[0]
    return dataset_id, rule


def _persist_quality(repository, status: QualityStatus, evaluated_at: datetime):
    dataset_id, rule = _dataset_and_rule(repository)
    run_id = repository.create_quality_evaluation_run(dataset_id, "test")
    quality_result = QualityResult(
        rule_id=rule.id,
        rule_slug=rule.slug,
        dimension=rule.dimension,
        severity=rule.severity,
        status=status,
        observed_value={"gap_count": 1} if status is QualityStatus.FAIL else {},
        expected_value={"maximum_allowed_gap_minutes": 90},
        affected_records=1 if status is QualityStatus.FAIL else 0,
        evaluated_records=24,
        details={"reason": "fixture"},
        evaluated_at=evaluated_at,
    )
    summary = QualityEvaluationSummary(
        evaluation_run_id=run_id,
        dataset_id=dataset_id,
        dataset_slug="hourly-weather",
        status="SUCCESS",
        score=0 if status is QualityStatus.FAIL else 100,
        evaluated_at=evaluated_at,
        rules_evaluated=1,
        rules_passed=int(status is QualityStatus.PASS),
        rules_warned=int(status is QualityStatus.WARN),
        rules_failed=int(status is QualityStatus.FAIL),
        rules_errored=int(status is QualityStatus.ERROR),
        rules_skipped=int(status is QualityStatus.SKIPPED),
        results=(quality_result,),
    )
    repository.complete_quality_evaluation(run_id, dataset_id, [quality_result], summary)
    return run_id


def test_fail_opens_and_repeated_fail_updates_one_incident(repository) -> None:
    seed_lineage(repository.connection)
    incidents = IncidentRepository(repository.connection)
    first_run = _persist_quality(
        repository, QualityStatus.FAIL, datetime(2026, 9, 6, 1, tzinfo=UTC)
    )
    reconcile_quality_evaluation(repository.connection, first_run)
    first = incidents.list_incidents()

    second_run = _persist_quality(
        repository, QualityStatus.FAIL, datetime(2026, 9, 6, 2, tzinfo=UTC)
    )
    reconcile_quality_evaluation(repository.connection, second_run)
    second = incidents.list_incidents()

    assert len(first) == len(second) == 1
    assert first[0]["id"] == second[0]["id"]
    assert second[0]["status"] == "OPEN"
    assert second[0]["occurrence_count"] == 2
    assert len(incidents.get_incident(second[0]["id"])["events"]) == 2
    assert len(incidents.get_incident(second[0]["id"])["impacts"]) == 3


def test_pass_resolves_and_later_fail_creates_new_incident(repository) -> None:
    seed_lineage(repository.connection)
    incidents = IncidentRepository(repository.connection)
    first_run = _persist_quality(
        repository, QualityStatus.FAIL, datetime(2026, 9, 6, 1, tzinfo=UTC)
    )
    reconcile_quality_evaluation(repository.connection, first_run)
    pass_run = _persist_quality(repository, QualityStatus.PASS, datetime(2026, 9, 6, 2, tzinfo=UTC))
    reconcile_quality_evaluation(repository.connection, pass_run)
    fail_run = _persist_quality(repository, QualityStatus.FAIL, datetime(2026, 9, 6, 3, tzinfo=UTC))
    reconcile_quality_evaluation(repository.connection, fail_run)

    rows = incidents.list_incidents()
    assert [row["status"] for row in rows] == ["OPEN", "RESOLVED"]
    assert rows[0]["id"] != rows[1]["id"]


def test_skipped_and_warn_preserve_state_and_error_opens_error_incident(repository) -> None:
    seed_lineage(repository.connection)
    incidents = IncidentRepository(repository.connection)
    fail_run = _persist_quality(repository, QualityStatus.FAIL, datetime(2026, 9, 6, 1, tzinfo=UTC))
    reconcile_quality_evaluation(repository.connection, fail_run)
    skipped_run = _persist_quality(
        repository, QualityStatus.SKIPPED, datetime(2026, 9, 6, 2, tzinfo=UTC)
    )
    reconcile_quality_evaluation(repository.connection, skipped_run)
    warn_run = _persist_quality(repository, QualityStatus.WARN, datetime(2026, 9, 6, 3, tzinfo=UTC))
    reconcile_quality_evaluation(repository.connection, warn_run)

    active = incidents.list_incidents(status="OPEN")
    assert len(active) == 1
    assert active[0]["occurrence_count"] == 1

    recovery_run = _persist_quality(
        repository, QualityStatus.PASS, datetime(2026, 9, 6, 4, tzinfo=UTC)
    )
    reconcile_quality_evaluation(repository.connection, recovery_run)
    error_run = _persist_quality(
        repository, QualityStatus.ERROR, datetime(2026, 9, 6, 4, tzinfo=UTC)
    )
    reconcile_quality_evaluation(repository.connection, error_run)
    rows = incidents.list_incidents()
    assert [row["incident_kind"] for row in rows] == ["EVALUATION_ERROR", "DATA_QUALITY"]
    assert rows[0]["status"] == "OPEN"
    assert rows[1]["status"] == "RESOLVED"


def test_acknowledgement_is_trusted_and_pass_resolves_acknowledged(repository) -> None:
    seed_lineage(repository.connection)
    incidents = IncidentRepository(repository.connection)
    fail_run = _persist_quality(repository, QualityStatus.FAIL, datetime(2026, 9, 6, 1, tzinfo=UTC))
    reconcile_quality_evaluation(repository.connection, fail_run)
    incident_id = incidents.list_incidents()[0]["id"]
    incidents.acknowledge(incident_id)
    assert incidents.get_incident(incident_id)["status"] == "ACKNOWLEDGED"
    pass_run = _persist_quality(repository, QualityStatus.PASS, datetime(2026, 9, 6, 2, tzinfo=UTC))
    reconcile_quality_evaluation(repository.connection, pass_run)
    assert incidents.get_incident(incident_id)["status"] == "RESOLVED"
