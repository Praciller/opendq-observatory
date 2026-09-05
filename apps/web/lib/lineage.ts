import { queryValues } from "./db";

export type LineageNode = {
  id: number;
  key: string;
  name: string;
  nodeType: string;
  description: string;
};

export type LineageEdge = {
  upstreamKey: string;
  downstreamKey: string;
  edgeType: string;
};

export type LineageImpact = {
  key: string;
  name: string;
  nodeType: string;
  distance: number;
  path: string[];
};

export type LineageResponse = {
  dataset: string;
  nodes: LineageNode[];
  edges: LineageEdge[];
  impact: LineageImpact[];
  message?: string;
};

export function lineageEmptyState(dataset: string): LineageResponse {
  return { dataset, nodes: [], edges: [], impact: [], message: "Lineage is unavailable." };
}

export function computeDownstreamImpact(
  nodes: Array<Pick<LineageNode, "key" | "name" | "nodeType">>,
  edges: LineageEdge[],
  startKey: string,
  maxDepth = 10,
): LineageImpact[] {
  const nodeMap = new Map(nodes.map((node) => [node.key, node]));
  const adjacency = new Map<string, string[]>();
  for (const edge of edges) {
    const next = adjacency.get(edge.upstreamKey) ?? [];
    next.push(edge.downstreamKey);
    adjacency.set(edge.upstreamKey, next.sort());
  }
  const queue: Array<{ key: string; distance: number; path: string[] }> = [
    { key: startKey, distance: 0, path: [startKey] },
  ];
  const visited = new Set([startKey]);
  const impact: LineageImpact[] = [];
  while (queue.length > 0) {
    const current = queue.shift();
    if (!current || current.distance >= maxDepth) continue;
    for (const nextKey of adjacency.get(current.key) ?? []) {
      if (visited.has(nextKey)) continue;
      const nextNode = nodeMap.get(nextKey);
      if (!nextNode) continue;
      visited.add(nextKey);
      const path = [...current.path, nextKey];
      impact.push({
        key: nextNode.key,
        name: nextNode.name,
        nodeType: nextNode.nodeType,
        distance: current.distance + 1,
        path,
      });
      queue.push({ key: nextKey, distance: current.distance + 1, path });
    }
  }
  return impact;
}

function normalizeDataset(dataset: string): string {
  return { "open-meteo": "hourly-weather", usgs: "earthquake-events", "usgs-earthquakes": "earthquake-events" }[dataset] ?? dataset;
}

export async function getLineage(dataset: string): Promise<LineageResponse> {
  const datasetSlug = normalizeDataset(dataset);
  const sourceKey = datasetSlug === "earthquake-events" ? "source:usgs" : "source:open-meteo";
  try {
    const nodes = await queryValues<{
      id: number; key: string; name: string; node_type: string; description: string;
    }>(
      `SELECT id, key, name, node_type, description
       FROM lineage_nodes
       WHERE dataset_id = (SELECT id FROM datasets WHERE slug = $1)
          OR key IN ($2, 'api:quality', 'ui:quality-dashboard')
       ORDER BY id`,
      [datasetSlug, sourceKey],
    );
    const nodeIds = nodes.map((node) => node.id);
    const edges = nodeIds.length === 0 ? [] : await queryValues<{
      upstream_key: string; downstream_key: string; edge_type: string;
    }>(
      `SELECT upstream.key AS upstream_key, downstream.key AS downstream_key, e.edge_type
       FROM lineage_edges e
       JOIN lineage_nodes upstream ON upstream.id = e.upstream_node_id
       JOIN lineage_nodes downstream ON downstream.id = e.downstream_node_id
       WHERE e.upstream_node_id = ANY($1::bigint[]) OR e.downstream_node_id = ANY($1::bigint[])
       ORDER BY e.id`,
      [nodeIds],
    );
    const mappedNodes = nodes.map((node) => ({
      id: node.id,
      key: node.key,
      name: node.name,
      nodeType: node.node_type,
      description: node.description,
    }));
    const mappedEdges = edges.map((edge) => ({
      upstreamKey: edge.upstream_key,
      downstreamKey: edge.downstream_key,
      edgeType: edge.edge_type,
    }));
    return {
      dataset: datasetSlug,
      nodes: mappedNodes,
      edges: mappedEdges,
      impact: computeDownstreamImpact(mappedNodes, mappedEdges, `dataset:${datasetSlug}`),
    };
  } catch {
    return lineageEmptyState(datasetSlug);
  }
}
