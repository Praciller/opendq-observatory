"""Read-only review of migration ledger evidence; never applies migrations."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import psycopg

from opendq.storage.migrations import _default_migrations_dir

PreflightState = Literal["VERIFIED", "LEGACY_REVIEW_REQUIRED", "PENDING_REVIEW", "BLOCKED"]


@dataclass(frozen=True)
class MigrationPreflight:
    state: PreflightState
    ledger: str
    applied_versions: list[str]
    pending_versions: list[str]
    unexpected_applied_versions: list[str]
    checksum_mismatches: list[str]
    notes: list[str]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def inspect_migrations(
    connection: psycopg.Connection[Any], migrations_dir: Path | None = None
) -> MigrationPreflight:
    """Read PostgreSQL migration metadata and compare known SQL hashes.

    Uses only SELECT queries. The calling CLI additionally forces a read-only
    PostgreSQL transaction *before* invoking this inspector.
    """
    directory = migrations_dir or _default_migrations_dir()
    files = sorted(directory.glob("*.sql"))
    if not files:
        return MigrationPreflight("BLOCKED", "unknown", [], [], [], [], ["No SQL files found."])

    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('public.schema_migrations')")
        row = cursor.fetchone()
        if not row or row[0] is None:
            return MigrationPreflight(
                "BLOCKED", "missing", [], sorted(hashes), [], [], ["Migration ledger is missing."]
            )
        cursor.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'schema_migrations'
            """
        )
        columns = {str(result[0]) for result in cursor.fetchall()}
        if "version" not in columns:
            return MigrationPreflight(
                "BLOCKED", "invalid", [], [], [], [], ["Migration version column is missing."]
            )
        has_checksum = "checksum" in columns
        if has_checksum:
            cursor.execute("SELECT version, checksum FROM public.schema_migrations")
            applied: dict[str, str | None] = {
                str(version): digest for version, digest in cursor.fetchall()
            }
        else:
            cursor.execute("SELECT version FROM public.schema_migrations")
            applied = {str(row[0]): None for row in cursor.fetchall()}

    unexpected = sorted(set(applied) - set(hashes))
    pending = sorted(set(hashes) - set(applied))
    mismatches = (
        sorted(name for name in applied if name in hashes and applied[name] != hashes[name])
        if has_checksum
        else []
    )
    notes: list[str] = []
    if unexpected:
        notes.append("Applied migrations are absent from the current SQL repository.")
    if mismatches:
        notes.append("Applied checksums do not match the repository SQL files.")
    if unexpected or mismatches:
        state: PreflightState = "BLOCKED"
    elif not has_checksum:
        state = "LEGACY_REVIEW_REQUIRED"
        notes.append("Legacy ledger has no checksums: this cannot verify historical executed SQL.")
    elif pending:
        state = "PENDING_REVIEW"
        notes.append("Unapplied migrations require a separate release and database review.")
    else:
        state = "VERIFIED"

    return MigrationPreflight(
        state=state,
        ledger="checksummed" if has_checksum else "legacy",
        applied_versions=sorted(applied),
        pending_versions=pending,
        unexpected_applied_versions=unexpected,
        checksum_mismatches=mismatches,
        notes=notes,
    )
