# Data quality roadmap

Phase 0–1 establishes contracts and rejection accounting, but does not implement the full Data Quality engine.

The next phase can add rules for completeness, validity, freshness, uniqueness, and referential integrity over the canonical observations. Rule results should be versioned, linked to `ingestion_runs`, and kept separate from raw provenance. Later drift and incident layers can consume those results without changing source adapters.

