"""Integration tests for migration inspection with the existing legacy schema."""

import hashlib

from opendq.storage.migration_preflight import inspect_migrations
from opendq.storage.migrations import _default_migrations_dir


def test_legacy_ledger_requires_manual_review_without_schema_changes(repository) -> None:
    with repository.connection.cursor() as cursor:
        cursor.execute("ALTER TABLE schema_migrations DROP COLUMN checksum")
    repository.connection.commit()
    result = inspect_migrations(repository.connection)
    assert result.state == "LEGACY_REVIEW_REQUIRED"
    assert result.ledger == "legacy"
    assert len(result.applied_versions) == len(list(_default_migrations_dir().glob("*.sql")))
    assert not result.pending_versions
    assert not result.checksum_mismatches
    with repository.connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_name = 'schema_migrations' AND column_name = 'checksum'"
        )
        assert cursor.fetchone()[0] == 0


def test_unknown_applied_007_blocks_inspection(repository) -> None:
    with repository.connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO schema_migrations(version) VALUES (%s)", ("007_phase7_unknown.sql",)
        )
    repository.connection.commit()
    result = inspect_migrations(repository.connection)
    assert result.state == "BLOCKED"
    assert result.unexpected_applied_versions == ["007_phase7_unknown.sql"]


def test_missing_applied_sql_file_blocks_inspection(repository, tmp_path) -> None:
    for path in _default_migrations_dir().glob("*.sql"):
        if path.name != "006_ai_incident_copilot.sql":
            (tmp_path / path.name).write_bytes(path.read_bytes())
    result = inspect_migrations(repository.connection, tmp_path)
    assert result.state == "BLOCKED"
    assert result.unexpected_applied_versions == ["006_ai_incident_copilot.sql"]


def test_extra_pending_sql_is_reported_without_execution(repository, tmp_path) -> None:
    for path in _default_migrations_dir().glob("*.sql"):
        (tmp_path / path.name).write_bytes(path.read_bytes())
    (tmp_path / "007_new.sql").write_text("-- preflight-only test", encoding="utf-8")
    result = inspect_migrations(repository.connection, tmp_path)
    assert result.state == "PENDING_REVIEW"
    assert result.pending_versions == ["007_new.sql"]


def test_checksum_validation_when_ledger_already_has_hashes(repository) -> None:
    with repository.connection.cursor() as cursor:
        for path in _default_migrations_dir().glob("*.sql"):
            cursor.execute(
                "UPDATE schema_migrations SET checksum = %s WHERE version = %s",
                (hashlib.sha256(path.read_bytes()).hexdigest(), path.name),
            )
    repository.connection.commit()
    assert inspect_migrations(repository.connection).state == "VERIFIED"

    with repository.connection.cursor() as cursor:
        cursor.execute(
            "UPDATE schema_migrations SET checksum = %s WHERE version = %s",
            ("bad-checksum", "006_ai_incident_copilot.sql"),
        )
    repository.connection.commit()
    changed = inspect_migrations(repository.connection)
    assert changed.state == "BLOCKED"
    assert changed.checksum_mismatches == ["006_ai_incident_copilot.sql"]


def test_missing_ledger_blocks_inspection(db_connection) -> None:
    with db_connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA public CASCADE")
        cursor.execute("CREATE SCHEMA public")
    db_connection.commit()
    result = inspect_migrations(db_connection)
    assert result.state == "BLOCKED"
    assert result.ledger == "missing"


def test_inspector_works_in_postgres_read_only_transaction(repository) -> None:
    connection = repository.connection
    connection.commit()
    with connection.transaction():
        connection.execute("SET TRANSACTION READ ONLY")
        report = inspect_migrations(connection)
        assert report.state == "VERIFIED"
        with connection.cursor() as cursor:
            cursor.execute("SHOW transaction_read_only")
            assert cursor.fetchone()[0] == "on"
