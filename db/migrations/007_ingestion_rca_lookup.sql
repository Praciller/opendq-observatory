-- RCARepository.latest_ingestion reads latest ingestion per dataset.
-- The existing source_id/started_at index cannot serve this dataset-scoped lookup.
CREATE INDEX ingestion_runs_dataset_started_idx
    ON ingestion_runs(dataset_id, started_at DESC);
