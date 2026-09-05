import pytest
from opendq.lineage.repository import LineageRepository
from opendq.lineage.seed import seed_lineage
from opendq.lineage.traversal import downstream_blast_radius
from psycopg.errors import UniqueViolation


def test_lineage_seed_is_idempotent(repository) -> None:
    first = seed_lineage(repository.connection)
    second = seed_lineage(repository.connection)

    assert first == second
    with repository.connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM lineage_nodes")
        node_count = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM lineage_edges")
        edge_count = cursor.fetchone()[0]
    assert node_count == 8
    assert edge_count == 8


def test_downstream_blast_radius_returns_shortest_paths(repository) -> None:
    seed_lineage(repository.connection)

    impact = downstream_blast_radius(
        LineageRepository(repository.connection), "dataset:hourly-weather"
    )

    assert [(item["key"], item["distance"]) for item in impact] == [
        ("process:quality-open-meteo", 1),
        ("api:quality", 2),
        ("ui:quality-dashboard", 3),
    ]
    assert impact[-1]["path"] == [
        "dataset:hourly-weather",
        "process:quality-open-meteo",
        "api:quality",
        "ui:quality-dashboard",
    ]


def test_lineage_traversal_handles_cycles_and_max_depth(repository) -> None:
    seed_lineage(repository.connection)
    lineage = LineageRepository(repository.connection)
    process_id = lineage.node_id("process:quality-open-meteo")
    dataset_id = lineage.node_id("dataset:hourly-weather")
    lineage.add_edge(dataset_id, process_id, "FEEDS")

    impact = downstream_blast_radius(lineage, "dataset:hourly-weather", max_depth=1)

    assert [item["key"] for item in impact] == ["process:quality-open-meteo"]


def test_lineage_rejects_self_edges(repository) -> None:
    seed_lineage(repository.connection)
    lineage = LineageRepository(repository.connection)
    node_id = lineage.node_id("dataset:hourly-weather")

    with pytest.raises(ValueError, match="self"):
        lineage.add_edge(node_id, node_id, "FEEDS")


def test_lineage_rejects_duplicate_edges(repository) -> None:
    seed_lineage(repository.connection)
    lineage = LineageRepository(repository.connection)

    with pytest.raises(UniqueViolation):
        lineage.add_edge(
            lineage.node_id("source:open-meteo"),
            lineage.node_id("dataset:hourly-weather"),
            "PRODUCES",
        )
