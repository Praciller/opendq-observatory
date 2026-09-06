CREATE TABLE drift_baselines (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dataset_id BIGINT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    column_name TEXT NOT NULL,
    baseline_type TEXT NOT NULL CHECK (baseline_type IN ('NUMERIC', 'CATEGORICAL', 'SCHEMA')),
    baseline_version INTEGER NOT NULL CHECK (baseline_version >= 1),
    window_start TIMESTAMPTZ,
    window_end TIMESTAMPTZ,
    sample_count INTEGER NOT NULL CHECK (sample_count >= 0),
    statistics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    distribution_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_from_run_id UUID REFERENCES ingestion_runs(run_id) ON DELETE SET NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (dataset_id, column_name, baseline_type, baseline_version)
);

CREATE UNIQUE INDEX drift_baselines_active_idx
    ON drift_baselines(dataset_id, column_name, baseline_type) WHERE active;
CREATE INDEX drift_baselines_dataset_lookup_idx
    ON drift_baselines(dataset_id, baseline_type, column_name, baseline_version DESC);

CREATE TABLE drift_evaluation_runs (
    evaluation_run_id UUID PRIMARY KEY,
    dataset_id BIGINT NOT NULL REFERENCES datasets(id) ON DELETE RESTRICT,
    triggered_by TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('RUNNING', 'SUCCESS', 'PARTIAL', 'FAILED', 'NO_BASELINE')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMPTZ,
    checks_evaluated INTEGER NOT NULL DEFAULT 0 CHECK (checks_evaluated >= 0),
    checks_stable INTEGER NOT NULL DEFAULT 0 CHECK (checks_stable >= 0),
    checks_warned INTEGER NOT NULL DEFAULT 0 CHECK (checks_warned >= 0),
    checks_drifted INTEGER NOT NULL DEFAULT 0 CHECK (checks_drifted >= 0),
    checks_skipped INTEGER NOT NULL DEFAULT 0 CHECK (checks_skipped >= 0),
    checks_errored INTEGER NOT NULL DEFAULT 0 CHECK (checks_errored >= 0),
    error_code TEXT,
    error_message TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CHECK ((status = 'RUNNING' AND finished_at IS NULL) OR (status <> 'RUNNING' AND finished_at IS NOT NULL))
);

CREATE INDEX drift_evaluation_runs_dataset_started_idx
    ON drift_evaluation_runs(dataset_id, started_at DESC);

CREATE TABLE drift_results (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    evaluation_run_id UUID NOT NULL REFERENCES drift_evaluation_runs(evaluation_run_id) ON DELETE CASCADE,
    dataset_id BIGINT NOT NULL REFERENCES datasets(id) ON DELETE RESTRICT,
    column_name TEXT NOT NULL,
    method TEXT NOT NULL CHECK (method IN ('PSI', 'QUANTILE_SHIFT', 'CATEGORICAL_TVD', 'SCHEMA_DIFF')),
    status TEXT NOT NULL CHECK (status IN ('STABLE', 'WARN', 'DRIFT', 'ERROR', 'SKIPPED')),
    severity TEXT NOT NULL CHECK (severity IN ('INFO', 'WARNING', 'HIGH', 'CRITICAL')),
    baseline_id BIGINT REFERENCES drift_baselines(id) ON DELETE RESTRICT,
    baseline_version INTEGER,
    baseline_window_start TIMESTAMPTZ,
    baseline_window_end TIMESTAMPTZ,
    current_window_start TIMESTAMPTZ,
    current_window_end TIMESTAMPTZ,
    observed_metric DOUBLE PRECISION,
    threshold DOUBLE PRECISION,
    baseline_sample_count INTEGER NOT NULL DEFAULT 0 CHECK (baseline_sample_count >= 0),
    current_sample_count INTEGER NOT NULL DEFAULT 0 CHECK (current_sample_count >= 0),
    details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (evaluation_run_id, column_name, method)
);

CREATE INDEX drift_results_dataset_evaluated_idx
    ON drift_results(dataset_id, evaluated_at DESC);
CREATE INDEX drift_results_run_id_idx ON drift_results(evaluation_run_id);

ALTER TABLE quality_rules DROP CONSTRAINT IF EXISTS quality_rules_dimension_check;
ALTER TABLE quality_rules ADD CONSTRAINT quality_rules_dimension_check CHECK (
    dimension IN ('freshness', 'completeness', 'uniqueness', 'validity', 'timestamp_gap', 'volume', 'drift')
);

ALTER TABLE incidents DROP CONSTRAINT IF EXISTS incidents_incident_kind_check;
ALTER TABLE incidents ADD CONSTRAINT incidents_incident_kind_check CHECK (
    incident_kind IN ('DATA_QUALITY', 'EVALUATION_ERROR', 'DATA_DRIFT')
);
ALTER TABLE incidents
    ALTER COLUMN first_evaluation_run_id DROP NOT NULL,
    ALTER COLUMN latest_evaluation_run_id DROP NOT NULL,
    ALTER COLUMN first_quality_result_id DROP NOT NULL,
    ALTER COLUMN latest_quality_result_id DROP NOT NULL,
    ADD COLUMN first_drift_evaluation_run_id UUID REFERENCES drift_evaluation_runs(evaluation_run_id) ON DELETE RESTRICT,
    ADD COLUMN latest_drift_evaluation_run_id UUID REFERENCES drift_evaluation_runs(evaluation_run_id) ON DELETE RESTRICT,
    ADD COLUMN first_drift_result_id BIGINT REFERENCES drift_results(id) ON DELETE RESTRICT,
    ADD COLUMN latest_drift_result_id BIGINT REFERENCES drift_results(id) ON DELETE RESTRICT;

CREATE INDEX incidents_kind_key_idx ON incidents(dataset_id, incident_kind, incident_key, opened_at DESC);

ALTER TABLE incident_events
    ADD COLUMN drift_evaluation_run_id UUID REFERENCES drift_evaluation_runs(evaluation_run_id) ON DELETE RESTRICT,
    ADD COLUMN drift_result_id BIGINT REFERENCES drift_results(id) ON DELETE RESTRICT;

CREATE TABLE root_cause_analyses (
    id UUID PRIMARY KEY,
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('SUCCESS', 'FAILED')),
    top_cause TEXT NOT NULL CHECK (top_cause IN (
        'UPSTREAM_SOURCE_FAILURE', 'SCHEMA_CHANGE', 'FRESHNESS_DELAY', 'TIMESTAMP_GAP',
        'INVALID_VALUES', 'VOLUME_CHANGE', 'DISTRIBUTION_SHIFT',
        'DATABASE_OR_PIPELINE_ERROR', 'UNKNOWN'
    )),
    confidence TEXT NOT NULL CHECK (confidence IN ('HIGH', 'MEDIUM', 'LOW', 'UNKNOWN')),
    algorithm_version TEXT NOT NULL,
    evidence_fingerprint TEXT NOT NULL,
    summary TEXT NOT NULL,
    details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (incident_id, algorithm_version, evidence_fingerprint)
);

CREATE INDEX root_cause_analyses_incident_created_idx
    ON root_cause_analyses(incident_id, created_at DESC);

CREATE TABLE root_cause_evidence (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    analysis_id UUID NOT NULL REFERENCES root_cause_analyses(id) ON DELETE CASCADE,
    evidence_type TEXT NOT NULL,
    source_table TEXT NOT NULL,
    source_id TEXT,
    reason_code TEXT NOT NULL,
    weight DOUBLE PRECISION NOT NULL,
    details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX root_cause_evidence_analysis_idx ON root_cause_evidence(analysis_id, weight DESC, id);
