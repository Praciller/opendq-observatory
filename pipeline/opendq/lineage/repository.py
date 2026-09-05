"""Persistence helpers for the small deterministic lineage graph."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import psycopg
from psycopg.types.json import Jsonb


class LineageRepository:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self.connection = connection

    def ensure_node(
        self,
        *,
        key: str,
        name: str,
        node_type: str,
        dataset_id: int | None = None,
        description: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> int:
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO lineage_nodes(
                        key, name, node_type, dataset_id, description, metadata_json
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (key) DO UPDATE SET
                        name = EXCLUDED.name,
                        node_type = EXCLUDED.node_type,
                        dataset_id = COALESCE(EXCLUDED.dataset_id, lineage_nodes.dataset_id),
                        description = EXCLUDED.description,
                        metadata_json = EXCLUDED.metadata_json,
                        active = TRUE,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                    """,
                    (key, name, node_type, dataset_id, description, Jsonb(dict(metadata or {}))),
                )
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError("lineage node upsert did not return an id")
                return int(row[0])

    def ensure_edge(self, upstream_node_id: int, downstream_node_id: int, edge_type: str) -> None:
        if upstream_node_id == downstream_node_id:
            raise ValueError("lineage self-edge is not allowed")
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO lineage_edges(upstream_node_id, downstream_node_id, edge_type)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (upstream_node_id, downstream_node_id, edge_type) DO NOTHING
                    """,
                    (upstream_node_id, downstream_node_id, edge_type),
                )

    def add_edge(self, upstream_node_id: int, downstream_node_id: int, edge_type: str) -> None:
        if upstream_node_id == downstream_node_id:
            raise ValueError("lineage self-edge is not allowed")
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO lineage_edges(upstream_node_id, downstream_node_id, edge_type)
                    VALUES (%s, %s, %s)
                    """,
                    (upstream_node_id, downstream_node_id, edge_type),
                )

    def node_id(self, key: str) -> int:
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT id FROM lineage_nodes WHERE key = %s", (key,))
            row = cursor.fetchone()
        if row is None:
            raise ValueError(f"lineage node not found: {key}")
        return int(row[0])

    def dataset_id_for_slug(self, dataset_slug: str) -> int:
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT id FROM datasets WHERE slug = %s", (dataset_slug,))
            row = cursor.fetchone()
        if row is None:
            raise ValueError(f"dataset not found: {dataset_slug}")
        return int(row[0])

    def downstream(self, node_id: int) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT n.id, n.key, n.name, n.node_type, e.edge_type
                FROM lineage_edges e
                JOIN lineage_nodes n ON n.id = e.downstream_node_id
                WHERE e.upstream_node_id = %s AND n.active
                ORDER BY n.key, e.edge_type
                """,
                (node_id,),
            )
            return [
                {
                    "id": int(row[0]),
                    "key": str(row[1]),
                    "name": str(row[2]),
                    "node_type": str(row[3]),
                    "edge_type": str(row[4]),
                }
                for row in cursor.fetchall()
            ]

    def nodes_for_dataset(
        self, dataset_id: int, *, source_key: str | None = None
    ) -> list[dict[str, Any]]:
        source_filter = "'api:quality', 'ui:quality-dashboard'"
        params: tuple[Any, ...] = (dataset_id,)
        if source_key:
            source_filter = "%s, 'api:quality', 'ui:quality-dashboard'"
            params = (dataset_id, source_key)
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id, key, name, node_type, description, metadata_json
                FROM lineage_nodes
                WHERE dataset_id = %s OR key IN ({source_filter})
                ORDER BY id
                """,
                params,
            )
            return [
                {
                    "id": int(row[0]),
                    "key": str(row[1]),
                    "name": str(row[2]),
                    "node_type": str(row[3]),
                    "description": str(row[4]),
                    "metadata": dict(row[5] or {}),
                }
                for row in cursor.fetchall()
            ]

    def edges_for_nodes(self, node_ids: list[int]) -> list[dict[str, Any]]:
        if not node_ids:
            return []
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT e.upstream_node_id, e.downstream_node_id, e.edge_type,
                       upstream.key, downstream.key
                FROM lineage_edges e
                JOIN lineage_nodes upstream ON upstream.id = e.upstream_node_id
                JOIN lineage_nodes downstream ON downstream.id = e.downstream_node_id
                WHERE e.upstream_node_id = ANY(%s) OR e.downstream_node_id = ANY(%s)
                ORDER BY e.id
                """,
                (node_ids, node_ids),
            )
            return [
                {
                    "upstream_node_id": int(row[0]),
                    "downstream_node_id": int(row[1]),
                    "edge_type": str(row[2]),
                    "upstream_key": str(row[3]),
                    "downstream_key": str(row[4]),
                }
                for row in cursor.fetchall()
            ]
