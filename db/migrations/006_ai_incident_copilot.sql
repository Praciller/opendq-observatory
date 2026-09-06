CREATE TABLE ai_incident_analyses (
    id UUID PRIMARY KEY,
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    input_fingerprint TEXT NOT NULL,
    deterministic_rca_analysis_id UUID REFERENCES root_cause_analyses(id) ON DELETE SET NULL,
    status TEXT NOT NULL CHECK (status IN ('SUCCESS', 'FALLBACK', 'FAILED', 'SKIPPED')),
    summary TEXT NOT NULL,
    probable_cause_explanation TEXT NOT NULL,
    evidence_highlights_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    investigation_steps_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    uncertainties_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    latency_ms INTEGER NOT NULL DEFAULT 0 CHECK (latency_ms >= 0),
    input_size INTEGER NOT NULL DEFAULT 0 CHECK (input_size >= 0),
    output_size INTEGER NOT NULL DEFAULT 0 CHECK (output_size >= 0),
    provider_request_id TEXT,
    cache_hit BOOLEAN NOT NULL DEFAULT FALSE,
    attempts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    error_code TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (incident_id, prompt_version, input_fingerprint)
);

CREATE INDEX ai_incident_analyses_incident_created_idx
    ON ai_incident_analyses(incident_id, created_at DESC);
CREATE INDEX ai_incident_analyses_status_created_idx
    ON ai_incident_analyses(status, created_at DESC);
