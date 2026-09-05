"""Idempotent lineage seed for the implemented OpenDQ Observatory flow."""

from __future__ import annotations

from typing import Any

import psycopg

from opendq.lineage.repository import LineageRepository


def seed_lineage(connection: psycopg.Connection[Any]) -> dict[str, int]:
    lineage = LineageRepository(connection)
    datasets: dict[str, int | None] = {}
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, slug FROM datasets WHERE slug IN ('hourly-weather', 'earthquake-events')"
        )
        datasets = {str(row[1]): int(row[0]) for row in cursor.fetchall()}

    node_specs = [
        ("source:open-meteo", "Open-Meteo API", "SOURCE", None, "Public Open-Meteo source API."),
        (
            "source:usgs",
            "USGS Earthquakes API",
            "SOURCE",
            None,
            "Public USGS earthquake source API.",
        ),
        (
            "dataset:hourly-weather",
            "Hourly Weather Dataset",
            "DATASET",
            datasets.get("hourly-weather"),
            "Normalized hourly weather observations.",
        ),
        (
            "dataset:earthquake-events",
            "Earthquake Events Dataset",
            "DATASET",
            datasets.get("earthquake-events"),
            "Normalized USGS earthquake observations.",
        ),
        (
            "process:quality-open-meteo",
            "Open-Meteo Quality Evaluation",
            "PROCESS",
            datasets.get("hourly-weather"),
            "Deterministic quality evaluation for hourly weather.",
        ),
        (
            "process:quality-usgs",
            "USGS Quality Evaluation",
            "PROCESS",
            datasets.get("earthquake-events"),
            "Deterministic quality evaluation for earthquake events.",
        ),
        ("api:quality", "Quality API", "API", None, "Read-only quality and incident evidence API."),
        (
            "ui:quality-dashboard",
            "Quality Dashboard",
            "DASHBOARD",
            None,
            "Public read-only observability dashboard.",
        ),
    ]
    node_ids: dict[str, int] = {}
    for key, name, node_type, dataset_id, description in node_specs:
        node_ids[key] = lineage.ensure_node(
            key=key,
            name=name,
            node_type=node_type,
            dataset_id=dataset_id,
            description=description,
        )

    edges = [
        ("source:open-meteo", "dataset:hourly-weather", "PRODUCES"),
        ("dataset:hourly-weather", "process:quality-open-meteo", "EVALUATED_BY"),
        ("process:quality-open-meteo", "api:quality", "SERVED_BY"),
        ("source:usgs", "dataset:earthquake-events", "PRODUCES"),
        ("dataset:earthquake-events", "process:quality-usgs", "EVALUATED_BY"),
        ("process:quality-usgs", "api:quality", "SERVED_BY"),
        ("api:quality", "ui:quality-dashboard", "VISUALIZED_BY"),
        ("api:quality", "ui:quality-dashboard", "SERVED_BY"),
    ]
    for upstream, downstream, edge_type in edges:
        lineage.ensure_edge(node_ids[upstream], node_ids[downstream], edge_type)

    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM lineage_nodes")
        node_row = cursor.fetchone()
        if node_row is None:
            raise RuntimeError("lineage node count query returned no row")
        node_count = int(node_row[0])
        cursor.execute("SELECT count(*) FROM lineage_edges")
        edge_row = cursor.fetchone()
        if edge_row is None:
            raise RuntimeError("lineage edge count query returned no row")
        edge_count = int(edge_row[0])
    return {"nodes": node_count, "edges": edge_count}
