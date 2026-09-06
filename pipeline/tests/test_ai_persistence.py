from datetime import UTC, datetime

from opendq.ai.models import AICopilotStatus
from opendq.ai.service import analyze_incident
from opendq.config import Settings
from opendq.incidents.engine import reconcile_quality_evaluation
from opendq.incidents.repository import IncidentRepository
from opendq.lineage.seed import seed_lineage
from opendq.quality.models import QualityEvaluationSummary, QualityResult, QualityStatus


def _create_incident(repository) -> str:
    seed_lineage(repository.connection)
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
    run_id = repository.create_quality_evaluation_run(dataset_id, "test")
    evaluated_at = datetime(2026, 9, 6, 1, tzinfo=UTC)
    result = QualityResult(
        rule_id=rule.id,
        rule_slug=rule.slug,
        dimension=rule.dimension,
        severity=rule.severity,
        status=QualityStatus.FAIL,
        observed_value={"gap_count": 1},
        expected_value={"maximum_allowed_gap_minutes": 90},
        affected_records=1,
        evaluated_records=24,
        details={"reason": "fixture"},
        evaluated_at=evaluated_at,
    )
    summary = QualityEvaluationSummary(
        evaluation_run_id=run_id,
        dataset_id=dataset_id,
        dataset_slug="hourly-weather",
        status="SUCCESS",
        score=0,
        evaluated_at=evaluated_at,
        rules_evaluated=1,
        rules_passed=0,
        rules_warned=0,
        rules_failed=1,
        rules_errored=0,
        rules_skipped=0,
        results=(result,),
    )
    repository.complete_quality_evaluation(run_id, dataset_id, [result], summary)
    reconcile_quality_evaluation(repository.connection, run_id)
    return IncidentRepository(repository.connection).list_incidents()[0]["id"]


def test_ai_fallback_persists_and_reuses_cached_analysis(repository, monkeypatch) -> None:
    incident_id = _create_incident(repository)
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("AI_COPILOT_ENABLED", "false")
    settings = Settings.from_env()

    first = analyze_incident(repository.connection, incident_id, settings)
    second = analyze_incident(repository.connection, incident_id, settings)

    assert first.analysis.status is AICopilotStatus.FALLBACK
    assert first.analysis.cache_hit is False
    assert first.analysis.deterministic_rca_analysis_id is not None
    assert second.cache_hit is True
    assert second.analysis.id == first.analysis.id
    with repository.connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM ai_incident_analyses WHERE incident_id = %s",
            (incident_id,),
        )
        assert cursor.fetchone()[0] == 1
