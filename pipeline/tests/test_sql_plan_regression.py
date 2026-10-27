"""Stable SQL access-path checks; no shared-runner timing thresholds."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from opendq.rca.repository import RCARepository
from opendq.storage.repository import Repository
from scripts.sql_plan_benchmark import guarded_database_url, summarize_plan


@pytest.mark.parametrize(
    ("url", "environment"),
    [
        ("postgresql://demo:demo@neon.example.com:5432/opendq_sqlperf_ci", "test"),
        ("postgresql://demo:demo@localhost:5432/opendq", "test"),
        ("postgresql://demo:demo@localhost:5432/opendq_sqlperf_ci", "production"),
        ("", "test"),
    ],
)
def test_sql_plan_benchmark_refuses_unsafe_databases(
    monkeypatch: pytest.MonkeyPatch, url: str, environment: str
) -> None:
    monkeypatch.setenv("APP_ENV", environment)
    monkeypatch.setenv("SQL_PLAN_DATABASE_URL", url)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="dedicated local"):
        guarded_database_url()


def test_sql_plan_benchmark_allows_dedicated_local_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = "postgresql://demo:demo@localhost:5432/opendq_sqlperf_ci"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("SQL_PLAN_DATABASE_URL", url)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert guarded_database_url() == url

    monkeypatch.setenv("DATABASE_URL", url)
    with pytest.raises(ValueError, match="dedicated local"):
        guarded_database_url()


def test_plan_summary_reports_access_path_without_time_assertions() -> None:
    plan = {
        "Execution Time": 0.04,
        "Planning Time": 0.02,
        "Plan": {
            "Node Type": "Limit",
            "Plans": [
                {
                    "Node Type": "Index Scan",
                    "Relation Name": "ingestion_runs",
                    "Index Name": "ingestion_runs_dataset_started_idx",
                    "Actual Rows": 1,
                    "Actual Loops": 1,
                }
            ],
        },
    }
    result = summarize_plan(plan)
    assert result["indices"] == ["ingestion_runs_dataset_started_idx"]
    assert result["scans"] == [
        {
            "node": "Index Scan",
            "relation": "ingestion_runs",
            "index": "ingestion_runs_dataset_started_idx",
            "rows": 1,
            "rowsFiltered": 0,
        }
    ]


def test_rca_latest_ingestion_preserves_order_and_index_capability(
    repository: Repository, db_connection: psycopg.Connection[object]
) -> None:
    source_id, dataset_id = repository.ensure_source_dataset(
        source_slug="sqlplan-source",
        source_name="SQL plan source",
        description="",
        base_url="https://example.test",
        dataset_slug="sqlplan-dataset",
        dataset_name="SQL plan dataset",
        schema_version="1",
    )
    other_source_id, other_dataset_id = repository.ensure_source_dataset(
        source_slug="sqlplan-other-source",
        source_name="SQL plan other source",
        description="",
        base_url="https://example.test",
        dataset_slug="sqlplan-other-dataset",
        dataset_name="SQL plan other dataset",
        schema_version="1",
    )
    now = datetime(2026, 1, 1, tzinfo=UTC)
    with db_connection.cursor() as cursor:
        for source, dataset, hour, received in (
            (source_id, dataset_id, 0, 5),
            (source_id, dataset_id, 2, 9),
            (other_source_id, other_dataset_id, 10, 99),
            (source_id, dataset_id, 1, 7),
        ):
            cursor.execute(
                """INSERT INTO ingestion_runs(
                       run_id, source_id, dataset_id, status, started_at,
                       finished_at, records_received)
                   VALUES (gen_random_uuid(), %s, %s, 'SUCCESS', %s, %s, %s)""",
                (
                    source,
                    dataset,
                    now + timedelta(hours=hour),
                    now + timedelta(hours=hour, minutes=1),
                    received,
                ),
            )

    latest = RCARepository(db_connection).latest_ingestion(dataset_id)
    assert latest is not None
    assert latest["records_received"] == 9
    assert latest["status"] == "SUCCESS"
    assert latest["finished_at"] == now + timedelta(hours=2, minutes=1)

    with db_connection.cursor() as cursor:
        cursor.execute(
            """SELECT indexdef FROM pg_indexes
               WHERE schemaname = 'public'
                 AND tablename = 'ingestion_runs'
                 AND indexname = 'ingestion_runs_dataset_started_idx'"""
        )
        index = cursor.fetchone()
        assert index is not None
        assert "(dataset_id, started_at DESC)" in str(index[0])

        # Disable sequential scans only for verifying index *capability*.
        # PostgreSQL is free to choose a seq scan for small tables in production.
        cursor.execute("SET LOCAL enable_seqscan = off")
        cursor.execute("SET LOCAL enable_bitmapscan = off")
        cursor.execute(
            """EXPLAIN (FORMAT JSON)
               SELECT run_id, status, records_received, records_written, records_rejected,
                      error_code, error_message, finished_at
               FROM ingestion_runs WHERE dataset_id = %s
               ORDER BY started_at DESC LIMIT 1""",
            (dataset_id,),
        )
        plan = cursor.fetchone()[0][0]["Plan"]

    def index_names(node: dict[str, object]) -> list[str]:
        names = [str(node["Index Name"])] if "Index Name" in node else []
        for nested in node.get("Plans", []):
            names.extend(index_names(nested))
        return names

    assert "ingestion_runs_dataset_started_idx" in index_names(plan)
