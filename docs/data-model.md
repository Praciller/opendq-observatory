# Data model

The initial migration creates five tables:

- `sources` stores stable source slugs and public metadata.
- `datasets` belongs to a source and identifies a logical normalized dataset.
- `dataset_versions` records schema version, hash, and reviewable JSON.
- `ingestion_runs` records the lifecycle, counters, timestamps, and sanitized failure details for every started run.
- `raw_observations` stores selected canonical fields plus compact source payload/provenance for reproducibility.

Foreign keys and indexes support source-to-dataset lookup, recent run queries, and observation time queries. Unique constraints prevent duplicate source/dataset slugs, duplicate weather records for a dataset/location/timestamp, and duplicate USGS event IDs for a dataset. Upserts rely on these database constraints rather than application-only checks.

The model leaves clear extension points for future `quality_results`, `incidents`, `lineage_edges`, and `drift_results` tables. Those tables are not created until their Phase 2 contracts are designed.

