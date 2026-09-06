# Lineage

Phase 3 uses a small provider-neutral graph that matches implemented OpenDQ Observatory surfaces:

```text
SOURCE → DATASET → PROCESS → API → DASHBOARD
```

The seed contains Open-Meteo and USGS source APIs, their normalized datasets, their deterministic quality processes, the shared quality API, and the shared quality dashboard. It does not invent warehouses, streams, models, feature stores, or infrastructure that the application does not use.

## Identity and edges

Stable `key` values provide identity; names are display text. The controlled edge vocabulary is `PRODUCES`, `FEEDS`, `EVALUATED_BY`, `SERVED_BY`, and `VISUALIZED_BY`. Exact duplicate edges and self-edges are rejected by database constraints. The seed may be run repeatedly and remains idempotent.

## Traversal and snapshots

Downstream impact uses a breadth-first traversal with visited-node protection and a maximum depth of ten. Each result contains the node, type, shortest distance, and path. A new incident stores one impact row per reachable node with its shortest path. This is a snapshot rather than a live join so historical incidents remain explainable after future lineage edits.

The trusted CLI provides `lineage seed`, `lineage show <dataset>`, and `lineage impact <dataset>`. Read-only APIs are `/api/lineage` and `/api/lineage/<dataset>`, with `/lineage` and `/lineage/<dataset>` as the public UI.

RCA uses lineage as context, not as proof of causality. Upstream source nodes can strengthen a source-failure candidate; downstream reachability describes affected assets and is shown from the incident impact snapshot. A dashboard or API node is never ranked as the cause merely because it is reachable downstream.
