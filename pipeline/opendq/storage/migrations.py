"""Apply visible SQL migrations in deterministic filename order."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import psycopg


def _default_migrations_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "db" / "migrations"


def apply_migrations(
    connection: psycopg.Connection[Any], migrations_dir: Path | None = None
) -> list[str]:
    directory = migrations_dir or _default_migrations_dir()
    files = sorted(directory.glob("*.sql"))
    if not files:
        raise FileNotFoundError(f"No SQL migrations found in {directory}")

    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('public.schema_migrations')")
        tracking_row = cursor.fetchone()
        has_tracking_table = tracking_row is not None and tracking_row[0] is not None
        applied = set()
        if has_tracking_table:
            cursor.execute("SELECT version FROM schema_migrations")
            applied = {row[0] for row in cursor.fetchall()}

    completed: list[str] = []
    for migration in files:
        if migration.name in applied:
            continue
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(migration.read_text(encoding="utf-8"))
                cursor.execute(
                    "INSERT INTO schema_migrations(version) VALUES (%s)", (migration.name,)
                )
        completed.append(migration.name)
    return completed
