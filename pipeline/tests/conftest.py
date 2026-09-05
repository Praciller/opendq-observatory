import os
from collections.abc import Iterator

import psycopg
import pytest
from opendq.storage.migrations import apply_migrations
from opendq.storage.repository import Repository

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://opendq:opendq@localhost:5432/opendq")


@pytest.fixture()
def db_connection() -> Iterator[psycopg.Connection[object]]:
    with psycopg.connect(DATABASE_URL) as connection:
        yield connection


@pytest.fixture()
def repository(db_connection: psycopg.Connection[object]) -> Repository:
    with db_connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA public CASCADE")
        cursor.execute("CREATE SCHEMA public")
    db_connection.commit()
    apply_migrations(db_connection)
    return Repository(db_connection)
