CREATE TABLE incidents (
    id UUID PRIMARY KEY,
    incident_key TEXT NOT NULL,
    incident_kind TEXT NOT NULL CHECK (incident_kind IN ('DATA_QUALITY', 'EVALUATION_ERROR')),
    dataset_id BIGINT NOT NULL REFERENCES datasets(id) ON DELETE RESTRICT,
    rule_id BIGINT NOT NULL REFERENCES quality_rules(id) ON DELETE RESTRICT,
    status TEXT NOT NULL CHECK (status IN ('OPEN', 'ACKNOWLEDGED', 'RESOLVED')),
    severity TEXT NOT NULL CHECK (severity IN ('INFO', 'WARNING', 'HIGH', 'CRITICAL')),
    opened_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    acknowledged_at TIMESTAMPTZ,
    first_evaluation_run_id UUID NOT NULL REFERENCES quality_evaluation_runs(evaluation_run_id) ON DELETE RESTRICT,
    latest_evaluation_run_id UUID NOT NULL REFERENCES quality_evaluation_runs(evaluation_run_id) ON DELETE RESTRICT,
    first_quality_result_id BIGINT NOT NULL REFERENCES quality_results(id) ON DELETE RESTRICT,
    latest_quality_result_id BIGINT NOT NULL REFERENCES quality_results(id) ON DELETE RESTRICT,
    occurrence_count INTEGER NOT NULL DEFAULT 1 CHECK (occurrence_count >= 1),
    summary TEXT NOT NULL,
    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX incidents_active_dataset_rule_idx
    ON incidents(dataset_id, rule_id)
    WHERE status IN ('OPEN', 'ACKNOWLEDGED');
CREATE INDEX incidents_status_opened_idx ON incidents(status, opened_at DESC);
CREATE INDEX incidents_dataset_rule_idx ON incidents(dataset_id, rule_id, opened_at DESC);

CREATE TABLE incident_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (event_type IN ('OPENED', 'OBSERVED_AGAIN', 'ACKNOWLEDGED', 'RESOLVED')),
    evaluation_run_id UUID REFERENCES quality_evaluation_runs(evaluation_run_id) ON DELETE RESTRICT,
    quality_result_id BIGINT REFERENCES quality_results(id) ON DELETE RESTRICT,
    from_status TEXT CHECK (from_status IS NULL OR from_status IN ('OPEN', 'ACKNOWLEDGED', 'RESOLVED')),
    to_status TEXT NOT NULL CHECK (to_status IN ('OPEN', 'ACKNOWLEDGED', 'RESOLVED')),
    severity TEXT NOT NULL CHECK (severity IN ('INFO', 'WARNING', 'HIGH', 'CRITICAL')),
    message TEXT NOT NULL,
    details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX incident_events_incident_created_idx ON incident_events(incident_id, created_at DESC);

CREATE TABLE lineage_nodes (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    node_type TEXT NOT NULL CHECK (node_type IN ('SOURCE', 'DATASET', 'PROCESS', 'API', 'DASHBOARD')),
    dataset_id BIGINT REFERENCES datasets(id) ON DELETE SET NULL,
    description TEXT NOT NULL DEFAULT '',
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX lineage_nodes_dataset_idx ON lineage_nodes(dataset_id);
CREATE INDEX lineage_nodes_type_idx ON lineage_nodes(node_type);

CREATE TABLE lineage_edges (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    upstream_node_id BIGINT NOT NULL REFERENCES lineage_nodes(id) ON DELETE CASCADE,
    downstream_node_id BIGINT NOT NULL REFERENCES lineage_nodes(id) ON DELETE CASCADE,
    edge_type TEXT NOT NULL CHECK (edge_type IN ('PRODUCES', 'FEEDS', 'EVALUATED_BY', 'SERVED_BY', 'VISUALIZED_BY')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (upstream_node_id <> downstream_node_id),
    UNIQUE (upstream_node_id, downstream_node_id, edge_type)
);

CREATE UNIQUE INDEX lineage_edges_unique_idx
    ON lineage_edges(upstream_node_id, downstream_node_id, edge_type);
CREATE INDEX lineage_edges_upstream_idx ON lineage_edges(upstream_node_id);
CREATE INDEX lineage_edges_downstream_idx ON lineage_edges(downstream_node_id);

CREATE TABLE incident_impacts (
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    lineage_node_id BIGINT NOT NULL REFERENCES lineage_nodes(id) ON DELETE RESTRICT,
    distance INTEGER NOT NULL CHECK (distance >= 1),
    path_json JSONB NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (incident_id, lineage_node_id)
);

CREATE UNIQUE INDEX incident_impacts_incident_node_idx
    ON incident_impacts(incident_id, lineage_node_id);
