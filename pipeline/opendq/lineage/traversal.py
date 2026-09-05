"""Bounded breadth-first downstream lineage traversal."""

from __future__ import annotations

from collections import deque
from typing import Any

from opendq.lineage.repository import LineageRepository


def downstream_blast_radius(
    repository: LineageRepository, start_key: str, *, max_depth: int = 10
) -> list[dict[str, Any]]:
    if max_depth < 1:
        return []
    start_id = repository.node_id(start_key)
    queue: deque[tuple[int, str, int, list[str]]] = deque([(start_id, start_key, 0, [start_key])])
    visited = {start_id}
    result: list[dict[str, Any]] = []
    while queue:
        node_id, _key, distance, path = queue.popleft()
        if distance >= max_depth:
            continue
        for downstream in repository.downstream(node_id):
            child_id = int(downstream["id"])
            if child_id in visited:
                continue
            visited.add(child_id)
            child_path = [*path, str(downstream["key"])]
            child_distance = distance + 1
            result.append(
                {
                    "key": downstream["key"],
                    "name": downstream["name"],
                    "node_type": downstream["node_type"],
                    "distance": child_distance,
                    "path": child_path,
                }
            )
            queue.append((child_id, str(downstream["key"]), child_distance, child_path))
    return result
