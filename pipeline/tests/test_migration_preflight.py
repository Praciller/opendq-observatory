"""Integration checks for the non-mutating migration ledger inspector."""

import hashlib

from opendq.storage.migration_preflight import inspect_migrations
from opendq.storage.migrations import _default_migrations_dir


def test_preflight_reports_verified_checksums(repository) -> None:
    result = inspect_migrations(repository.connection)
    assert result.state == "VERIFIED"
    assert result.ledger == "checksummed"
    assert len(result.applied_versions) == 6
    assert not result.pending_versions
    assert not result.checksum_mismatches


def test_preflight_requires_review_for_legacy_database(repository) -> None:
    with repository.connection.cursor() as cursor:
        cursor.execute("ALTER TABLE schema_migrations DROP COLUMN checksum")
    repository.connection.commit()

    result = inspect_migrations(repository.connection)
    assert result.state == "LEGACY_REVIEW_REQUIRED"
    assert result.ledger == "legacy"
    assert not result.checksum_mismatches


def test_preflight_blocks_unknown_applied_version(repository) -> None:
    with repository.connection.cursor() as cursor:
        cursor.execute("INSERT INTO schema_migrations(version, checksum) VALUES (%s, %s)", (
            "007_phase7_future.sql", hashlib.sha256(b"-- future").hexdigest()
        ))
    repository.connection.commit()

    result = inspect_migrations(repository.connection)
    assert result.state == "BLOCKED"
    assert result.unexpected_applied_versions == ["007_phase7_future.sql"]


def test_preflight_blocks_tampered_checksum(repository) -> None:
    with repository.connection.cursor() as cursor:
        cursor.execute("UPDATE schema_migrations SET checksum = %s WHERE version = %s", (
            "mismatched", "006_ai_incident_copilot.sql"
        ))
    repository.connection.commit()

    result = inspect_migrations(repository.connection)
    assert result.state == "BLOCKED"
    assert result.checksum_mismatches == ["006_ai_incident_copilot.sql"]


def test_preflight_detects_pending_files_without_applying_them(repository, tmp_path) -> None:
    for source in _default_migrations_dir().glob("*.sql"):
        (tmp_path / source.name).write_bytes(source.read_bytes())
    (tmp_path / "007_future.sql").write_text("-- pending\n", encoding="utf-8")

    result = inspect_migrations(repository.connection, tmp_path)
    assert result.state == "PENDING_REVIEW"
    assert result.pending_versions == ["007_future.sql"]

    with repository.connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('public.unknown_future_table')")
        assert cursor.fetchone()[0] is None


def test_preflight_blocks_missing_ledger(db_connection) -> None:
    with db_connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA public CASCADE")
        cursor.execute("CREATE SCHEMA public")
    db_connection.commit()

    result = inspect_migrations(db_connection)
    assert result.state == "BLOCKED"
    assert result.ledger == "missing"
