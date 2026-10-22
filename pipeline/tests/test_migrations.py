import hashlib

import psycopg
import pytest

from opendq.storage.migrations import (
    MigrationDriftError,
    _default_migrations_dir,
    apply_migrations,
)


def test_migrations_apply_from_empty_database(db_connection) -> None:
    with db_connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA public CASCADE")
        cursor.execute("CREATE SCHEMA public")
    db_connection.commit()

    applied = apply_migrations(db_connection)

    assert applied == [
        "001_initial.sql",
        "002_quality_engine.sql",
        "003_incidents_lineage.sql",
        "004_drift_rca.sql",
        "005_reclassify_drift_incidents.sql",
        "006_ai_incident_copilot.sql",
    ]
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' ORDER BY table_name
            """
        )
        assert [row[0] for row in cursor.fetchall()] == [
            "ai_incident_analyses",
            "dataset_versions",
            "datasets",
            "drift_baselines",
            "drift_evaluation_runs",
            "drift_results",
            "incident_events",
            "incident_impacts",
            "incidents",
            "ingestion_runs",
            "lineage_edges",
            "lineage_nodes",
            "quality_evaluation_runs",
            "quality_results",
            "quality_rules",
            "raw_observations",
            "root_cause_analyses",
            "root_cause_evidence",
            "schema_migrations",
            "sources",
        ]


def test_migrations_enforce_observation_identities(repository) -> None:
    with repository.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'raw_observations'
            ORDER BY indexname
            """
        )
        indexes = {row[0] for row in cursor.fetchall()}

    assert "raw_weather_identity" in indexes
    assert "raw_earthquake_identity" in indexes


def test_quality_tables_have_dataset_and_run_indexes(repository) -> None:
    with repository.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT indexname FROM pg_indexes
            WHERE tablename IN ('quality_rules', 'quality_evaluation_runs', 'quality_results')
            ORDER BY indexname
            """
        )
        indexes = {row[0] for row in cursor.fetchall()}

    assert "quality_rules_dataset_id_idx" in indexes
    assert "quality_evaluation_runs_dataset_started_idx" in indexes
    assert "quality_results_run_id_idx" in indexes


def test_incident_and_lineage_constraints_are_present(repository) -> None:
    with repository.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT indexname FROM pg_indexes
            WHERE tablename IN ('incidents', 'incident_impacts', 'lineage_edges')
            ORDER BY indexname
            """
        )
        indexes = {row[0] for row in cursor.fetchall()}

    assert "incidents_active_dataset_rule_idx" in indexes
    assert "incident_impacts_incident_node_idx" in indexes
    assert "lineage_edges_unique_idx" in indexes


def test_drift_and_rca_indexes_are_present(repository) -> None:
    with repository.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT indexname FROM pg_indexes
            WHERE tablename IN (
                'drift_baselines', 'drift_evaluation_runs', 'drift_results',
                'root_cause_analyses', 'root_cause_evidence'
            ) ORDER BY indexname
            """
        )
        indexes = {row[0] for row in cursor.fetchall()}

    assert "drift_baselines_active_idx" in indexes
    assert "drift_evaluation_runs_dataset_started_idx" in indexes
    assert "drift_results_dataset_evaluated_idx" in indexes
    assert "root_cause_analyses_incident_created_idx" in indexes

def test_schema_migration_checksum_ledger_is_populated(repository) -> None:
    with repository.connection.cursor() as cursor:
        cursor.execute("SELECT version, checksum FROM schema_migrations ORDER BY version")
        rows = cursor.fetchall()
    paths = sorted(_default_migrations_dir().glob("*.sql"))
    assert len(rows) == len(paths)
    assert rows == [
        (path.name, hashlib.sha256(path.read_bytes()).hexdigest()) for path in paths
    ]
    assert apply_migrations(repository.connection) == []


def test_migration_checksum_detects_changed_sql(repository, tmp_path) -> None:
    for source in _default_migrations_dir().glob("*.sql"):
        (tmp_path / source.name).write_bytes(source.read_bytes())
    changed = tmp_path / "006_ai_incident_copilot.sql"
    changed.write_text(
        changed.read_text(encoding="utf-8") + "\n-- changed after deployment\n",
        encoding="utf-8",
    )

    with pytest.raises(MigrationDriftError, match="checksum mismatch"):
        apply_migrations(repository.connection, tmp_path)


def test_migration_checksum_detects_missing_applied_file(repository, tmp_path) -> None:
    for source in _default_migrations_dir().glob("*.sql"):
        if source.name != "006_ai_incident_copilot.sql":
            (tmp_path / source.name).write_bytes(source.read_bytes())

    with pytest.raises(MigrationDriftError, match="are missing"):
        apply_migrations(repository.connection, tmp_path)


def test_migration_ledger_adopts_legacy_database_once(repository) -> None:
    with repository.connection.cursor() as cursor:
        cursor.execute("ALTER TABLE schema_migrations DROP COLUMN checksum")
    repository.connection.commit()

    assert apply_migrations(repository.connection) == []
    with repository.connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM schema_migrations WHERE checksum IS NULL")
        assert cursor.fetchone()[0] == 0


def test_migration_ledger_rejects_unexpected_null_checksum(repository) -> None:
    with repository.connection.cursor() as cursor:
        cursor.execute(
            "UPDATE schema_migrations SET checksum = NULL "
            "WHERE version = '006_ai_incident_copilot.sql'"
        )
    repository.connection.commit()

    with pytest.raises(MigrationDriftError, match="checksum mismatch"):
        apply_migrations(repository.connection)


def test_migration_failure_rolls_back_all_new_sql(repository, tmp_path) -> None:
    for source in _default_migrations_dir().glob("*.sql"):
        (tmp_path / source.name).write_bytes(source.read_bytes())
    (tmp_path / "998_test_create.sql").write_text(
        "CREATE TABLE migration_rollback_probe (id integer);\n", encoding="utf-8"
    )
    (tmp_path / "999_test_failure.sql").write_text(
        "SELECT 1 / 0;\n", encoding="utf-8"
    )

    with pytest.raises(psycopg.errors.DivisionByZero):
        apply_migrations(repository.connection, tmp_path)
    with repository.connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('public.migration_rollback_probe')")
        assert cursor.fetchone()[0] is None
        cursor.execute("SELECT count(*) FROM schema_migrations")
        assert cursor.fetchone()[0] == 6
