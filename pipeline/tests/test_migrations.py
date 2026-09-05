from opendq.storage.migrations import apply_migrations


def test_migrations_apply_from_empty_database(db_connection) -> None:
    with db_connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA public CASCADE")
        cursor.execute("CREATE SCHEMA public")
    db_connection.commit()

    applied = apply_migrations(db_connection)

    assert applied == ["001_initial.sql", "002_quality_engine.sql"]
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
            "quality_evaluation_runs",
            "quality_results",
            "quality_rules",
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
