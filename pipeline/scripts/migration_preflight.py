"""Safe, explicit migration preflight: SELECT-only, never applies SQL files."""

from __future__ import annotations

import json
import os

import psycopg
from opendq.storage.migration_preflight import inspect_migrations


def main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print(json.dumps({"state": "BLOCKED", "message": "DATABASE_URL is not set."}))
        return 2

    try:
        with psycopg.connect(database_url, autocommit=True, connect_timeout=10) as connection:
            with connection.transaction():
                # Force PostgreSQL to reject writes as well as inspecting via SELECT only.
                connection.execute("SET TRANSACTION READ ONLY")
                report = inspect_migrations(connection)
    except (psycopg.Error, OSError, UnicodeError):
        # Do not print server exceptions; they can contain connection details.
        print(json.dumps({"state": "BLOCKED", "message": "Preflight could not be completed."}))
        return 2

    print(json.dumps(report.as_dict(), sort_keys=True))
    return 0 if report.state == "VERIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
