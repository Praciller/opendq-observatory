"""Apply versioned SQL migrations with a checksum ledger and transaction lock."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import psycopg

# A stable, project-specific PostgreSQL transaction advisory lock ID.
_MIGRATION_LOCK_ID = 684251197638726145


class MigrationDriftError(RuntimeError):
    """Applied migration history differs from the repository's SQL files."""


def _default_migrations_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "db" / "migrations"


def apply_migrations(
    connection: psycopg.Connection[Any], migrations_dir: Path | None = None
) -> list[str]:
    """Apply pending SQL atomically; reject changed or missing applied migrations.

    A database created before checksums were introduced receives a one-time
    checksum baseline for its already-applied migrations. This baseline trusts
    the current reviewed migration files; it cannot reconstruct historical SQL.
    """
    directory = migrations_dir or _default_migrations_dir()
    files = sorted(directory.glob("*.sql"))
    if not files:
        raise FileNotFoundError(f"No SQL migrations found in {directory}")

    # Read and hash before opening the transaction so executed SQL is identical
    # to the bytes whose hash is recorded in the ledger.
    sql_bytes = {path.name: path.read_bytes() for path in files}
    sql_files = {
        name: (data.decode("utf-8"), hashlib.sha256(data).hexdigest())
        for name, data in sql_bytes.items()
    }
    completed: list[str] = []

    with connection.transaction():
        with connection.cursor() as cursor:
            # Serializes concurrent migration runners, including the first one
            # before schema_migrations exists. Released at transaction end.
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", (_MIGRATION_LOCK_ID,))
            cursor.execute("SELECT to_regclass('public.schema_migrations')")
            table_row = cursor.fetchone()
            has_table = bool(table_row and table_row[0] is not None)
            has_checksum = False
            applied: dict[str, str | None] = {}

            if has_table:
                cursor.execute(
                    """
                    SELECT EXISTS (
                      SELECT 1 FROM information_schema.columns
                      WHERE table_schema = 'public'
                        AND table_name = 'schema_migrations'
                        AND column_name = 'checksum'
                    )
                    """
                )
                column_row = cursor.fetchone()
                has_checksum = bool(column_row and column_row[0])
                if has_checksum:
                    cursor.execute("SELECT version, checksum FROM public.schema_migrations")
                    applied = {version: digest for version, digest in cursor.fetchall()}
                else:
                    cursor.execute("SELECT version FROM public.schema_migrations")
                    applied = {row[0]: None for row in cursor.fetchall()}

            missing = sorted(set(applied) - set(sql_files))
            if missing:
                raise MigrationDriftError(
                    f"Applied migration SQL files are missing: {', '.join(missing)}"
                )

            for version, digest in applied.items():
                expected = sql_files[version][1]
                if has_checksum and digest != expected:
                    raise MigrationDriftError(f"Migration checksum mismatch: {version}")

            if has_table and not has_checksum:
                # Backward-compatible, one-time adoption for existing v1 databases.
                # If the original SQL differs from current files, manual review of
                # the historic schema is required; no such claim is inferred here.
                cursor.execute("ALTER TABLE public.schema_migrations ADD COLUMN checksum TEXT")
                for version in sorted(applied):
                    cursor.execute(
                        "UPDATE public.schema_migrations SET checksum = %s WHERE version = %s",
                        (sql_files[version][1], version),
                    )

            for version, (sql, digest) in sql_files.items():
                if version in applied:
                    continue
                cursor.execute(sql)
                if not has_table:
                    # 001_initial.sql creates schema_migrations in fresh databases.
                    cursor.execute("SELECT to_regclass('public.schema_migrations')")
                    table_row = cursor.fetchone()
                    if not table_row or table_row[0] is None:
                        raise MigrationDriftError(
                            f"Initial migration did not create schema_migrations: {version}"
                        )
                    cursor.execute("ALTER TABLE public.schema_migrations ADD COLUMN checksum TEXT")
                    has_table = True
                cursor.execute(
                    "INSERT INTO public.schema_migrations(version, checksum) VALUES (%s, %s)",
                    (version, digest),
                )
                completed.append(version)

    return completed
