from opendq.storage.migrations import apply_migrations


def test_migrations_apply_from_empty_database(db_connection) -> None:
    with db_connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA public CASCADE")
        cursor.execute("CREATE SCHEMA public")
    db_connection.commit()

    applied = apply_migrations(db_connection)

    assert applied == ["001_initial.sql"]
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' ORDER BY table_name
            """
        )
        assert [row[0] for row in cursor.fetchall()] == [
            "dataset_versions",
            "datasets",
            "ingestion_runs",
            "raw_observations",
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
