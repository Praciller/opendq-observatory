CREATE TABLE quality_rules (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dataset_id BIGINT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    slug TEXT NOT NULL,
    name TEXT NOT NULL,
    dimension TEXT NOT NULL CHECK (
        dimension IN ('freshness', 'completeness', 'uniqueness', 'validity', 'timestamp_gap', 'volume')
    ),
    rule_type TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    severity TEXT NOT NULL CHECK (severity IN ('INFO', 'WARNING', 'HIGH', 'CRITICAL')),
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (dataset_id, slug)
);

CREATE INDEX quality_rules_dataset_id_idx ON quality_rules(dataset_id);

CREATE TABLE quality_evaluation_runs (
    evaluation_run_id UUID PRIMARY KEY,
    dataset_id BIGINT NOT NULL REFERENCES datasets(id) ON DELETE RESTRICT,
    triggered_by TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('RUNNING', 'SUCCESS', 'FAILED')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMPTZ,
    rules_evaluated INTEGER NOT NULL DEFAULT 0 CHECK (rules_evaluated >= 0),
    rules_passed INTEGER NOT NULL DEFAULT 0 CHECK (rules_passed >= 0),
    rules_warned INTEGER NOT NULL DEFAULT 0 CHECK (rules_warned >= 0),
    rules_failed INTEGER NOT NULL DEFAULT 0 CHECK (rules_failed >= 0),
    rules_errored INTEGER NOT NULL DEFAULT 0 CHECK (rules_errored >= 0),
    rules_skipped INTEGER NOT NULL DEFAULT 0 CHECK (rules_skipped >= 0),
    score DOUBLE PRECISION CHECK (score IS NULL OR (score >= 0 AND score <= 100)),
    error_code TEXT,
    error_message TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CHECK ((status = 'RUNNING' AND finished_at IS NULL) OR (status <> 'RUNNING' AND finished_at IS NOT NULL))
);

CREATE INDEX quality_evaluation_runs_dataset_started_idx
    ON quality_evaluation_runs(dataset_id, started_at DESC);

CREATE TABLE quality_results (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    evaluation_run_id UUID NOT NULL REFERENCES quality_evaluation_runs(evaluation_run_id) ON DELETE CASCADE,
    rule_id BIGINT NOT NULL REFERENCES quality_rules(id) ON DELETE RESTRICT,
    dataset_id BIGINT NOT NULL REFERENCES datasets(id) ON DELETE RESTRICT,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'WARN', 'FAIL', 'ERROR', 'SKIPPED')),
    observed_value JSONB NOT NULL DEFAULT '{}'::jsonb,
    expected_value JSONB NOT NULL DEFAULT '{}'::jsonb,
    affected_records INTEGER NOT NULL DEFAULT 0 CHECK (affected_records >= 0),
    evaluated_records INTEGER NOT NULL DEFAULT 0 CHECK (evaluated_records >= 0),
    details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (evaluation_run_id, rule_id)
);

CREATE INDEX quality_results_run_id_idx ON quality_results(evaluation_run_id);
CREATE INDEX quality_results_dataset_status_idx ON quality_results(dataset_id, status);
