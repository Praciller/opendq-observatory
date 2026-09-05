# OpenDQ Observatory Phase 0–1 Design

## Status

Approved for implementation on 2026-09-06.

## Goal

Build a public, reproducible foundation for OpenDQ Observatory and two reliable public-data ingestion paths: Open-Meteo weather observations and USGS earthquake events. The result must run locally with PostgreSQL, expose an honest minimal web status surface, pass deterministic tests and static quality gates, and remain ready for Vercel Hobby plus Neon Free without requiring paid or always-on infrastructure.

## Scope

### Implemented in Phase 0–1

- Python 3.12+ package with configuration, structured logging, source adapters, canonical Pydantic contracts, explicit errors, PostgreSQL persistence, migration runner, and CLI.
- Open-Meteo adapter for a documented Bangkok location and USGS GeoJSON adapter.
- UTC normalization, compact provenance-bearing raw observations, database-enforced uniqueness, upsert-based idempotency, and ingestion-run lifecycle tracking.
- Visible SQL migrations for `sources`, `datasets`, `dataset_versions`, `ingestion_runs`, and `raw_observations`.
- Next.js App Router status page with `/api/health` and `/api/sources`.
- Docker Compose PostgreSQL, GitHub Actions CI with disposable PostgreSQL, and six-hour scheduled ingestion with concurrency protection.
- Deterministic fixtures, unit/integration tests, documentation, ADRs, and conservative secret scanning.

### Explicitly deferred

Full data-quality rules, drift, incidents, lineage visualization, AI analysis, streaming infrastructure, authentication, notifications, billing, multi-tenancy, and complex dashboards are not implemented. Database extension points are limited to indexes, metadata, and documented future tables; no speculative Phase 2 engine is added.

## Architecture

```text
Open-Meteo / USGS
        ↓
  async source adapter fetch
        ↓
  source transport parse
        ↓
  canonical Pydantic normalize
        ↓
  PostgreSQL transaction + upsert
        ↓
  ingestion_run terminal status
        ↓
  Next.js read-only status/API surface
```

The Python pipeline is the owner of ingestion behavior. `httpx` transport is injected into adapters so tests use deterministic fixture responses without public-network calls. PostgreSQL is the single schema authority. The web app uses a lightweight `pg` driver only for read-only status queries and shares the same environment variable and SQL schema, without ORM models.

Phase 0–1 uses scheduled micro-batches because the two selected sources publish bounded snapshots/feeds and the project must remain free-tier efficient. A future streaming adapter can be added behind the source/normalization boundary, but Kafka, Redpanda, and other always-on services are deliberately absent now.

## Configuration and observability

Python configuration is centralized in `opendq.config.Settings`. `DATABASE_URL` is required for database operations; public endpoint URLs have safe defaults. `APP_ENV` and `LOG_LEVEL` are configurable. Structured JSON-friendly log records include `run_id`, `source`, `event`, `status`, record counters, duration, and sanitized error fields. Secrets and connection strings are never logged or persisted.

All persisted timestamps are timezone-aware UTC. Source-specific timestamp formats are converted at the normalization boundary. Web responses may format timestamps for display but never change stored database values.

## Database design

The initial migration is deterministic and applies to an empty PostgreSQL database. Runtime table creation is not used.

- `sources`: stable slug, public metadata, enabled flag, and timestamps.
- `datasets`: source-owned dataset slug, description, and schema version.
- `dataset_versions`: schema hash and reviewable schema JSON for contract evolution.
- `ingestion_runs`: source/dataset, explicit lifecycle status, timestamps, counters, sanitized error code/message, and bounded metadata.
- `raw_observations`: dataset/run provenance, canonical observation identity, observed/event timestamp, selected normalized columns, source payload JSON, and source URL. It is a compact reproducibility record, not an unlimited payload archive.

Database constraints include unique source/dataset slugs, foreign keys, indexes for status and time queries, and partial uniqueness for logical records:

- weather: dataset plus location latitude/longitude plus observed UTC timestamp;
- earthquakes: dataset plus canonical USGS event ID.

Persistence uses parameterized SQL and `INSERT ... ON CONFLICT DO NOTHING` inside a transaction. The second identical ingestion therefore produces zero inserted logical records and maps to `NO_CHANGE` while remaining a successful process outcome.

## Ingestion lifecycle and failure semantics

`ingestion_runs` is created before source processing. Every started run is finalized in a `finally` path. Successful writes produce `SUCCESS`; a successful fetch with no new rows produces `NO_CHANGE`; rejected records alongside accepted rows produce `PARTIAL`; handled source, contract, or database failures produce `FAILED`. `ingest all` attempts both sources even if one fails, reports each outcome, and exits non-zero if any source has an actual failure. `NO_CHANGE` is exit code zero.

The small error taxonomy is `SOURCE_UNAVAILABLE`, `SOURCE_TIMEOUT`, `INVALID_RESPONSE`, `CONTRACT_VIOLATION`, `DATABASE_ERROR`, and `CONFIGURATION_ERROR`. Error messages are sanitized before persistence and CLI display.

## Source contracts

Open-Meteo canonical records contain `observed_at`, `temperature_c`, `relative_humidity_pct`, `precipitation_mm`, `wind_speed_kmh`, `latitude`, and `longitude`. The adapter defaults to Bangkok coordinates and a small forecast window.

USGS canonical records contain `event_id`, `occurred_at`, `magnitude`, `place`, `longitude`, `latitude`, `depth_km`, and `source_url`. The USGS GeoJSON `feature.id` is the canonical identity. Missing or malformed required values are rejected and counted; they never silently enter the valid set.

## Web behavior

The landing page communicates the product identity and shows a minimal status view. It displays real persisted source and latest-run data, with honest empty states before ingestion. `/api/health` returns application availability separately from database availability and uses a short database statement timeout. Database errors are sanitized to public status values; connection strings, SQL, stack traces, and credentials are never returned. `/api/sources` returns persisted source rows and latest successful/terminal ingestion information, or an empty collection if the database is reachable but unseeded.

## Verification strategy

Deterministic tests cover configuration, parsing, normalization, contract rejection, error/status mapping, migration application, schema constraints, run lifecycle, idempotent weather and USGS persistence, duplicate protection, failure finalization, and `ingest all` partial failure. HTTP calls are fixture-backed/mocked. CI runs against disposable PostgreSQL and never Neon or live public APIs.

Live source smoke checks are separate from CI and run at most one controlled request per source when network access is available. Unavailable or unexecuted live checks are reported as `NOT_RUN`.

The final report distinguishes locally verified behavior from owner-authorized Neon/Vercel deployment. Cloudflare is forbidden and is verified with dependency/configuration searches.

