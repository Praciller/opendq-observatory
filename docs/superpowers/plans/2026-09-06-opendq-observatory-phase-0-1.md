# OpenDQ Observatory Phase 0–1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and locally verify the public OpenDQ Observatory foundation and reliable Open-Meteo/USGS ingestion paths.

**Architecture:** A Python 3.12 package owns async source fetch, parsing, canonical Pydantic normalization, explicit PostgreSQL persistence, and the `python -m opendq` CLI. A minimal Next.js App Router app reads the same PostgreSQL schema through `pg` and exposes honest health/source status. SQL migrations are the single schema authority.

**Tech Stack:** Python 3.12+, httpx, Pydantic, psycopg, pytest, pytest-asyncio, Ruff, mypy, PostgreSQL, Next.js, TypeScript, Tailwind CSS, npm lockfile, Docker Compose, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-06-opendq-observatory-design.md`

## Global Constraints

- Implement only Phase 0–1; defer quality engine, drift, incidents, lineage UI, AI, streaming, authentication, notifications, billing, and complex dashboards.
- Persist timestamps in UTC and normalize source timestamps before persistence.
- Enforce weather and earthquake idempotency in PostgreSQL with unique constraints and upserts.
- Apply deterministic visible migrations from an empty PostgreSQL database; never create tables at runtime.
- Create ingestion runs before processing and finalize every started run.
- `ingest all` attempts every source and exits non-zero when any source fails; `NO_CHANGE` is successful.
- CI uses disposable PostgreSQL and deterministic fixtures; live smoke tests stay outside deterministic CI.
- Cloudflare dependencies/configuration are forbidden.
- Never commit secrets, credentials, database URLs, or generated secret-bearing files.

### Task 1: Repository foundation and configuration

**Files:**
- Create: `README.md`, `LICENSE`, `.gitignore`, `.env.example`, `docker-compose.yml`
- Create: `pipeline/pyproject.toml`, `pipeline/opendq/__init__.py`, `pipeline/opendq/config.py`, `pipeline/opendq/errors.py`, `pipeline/opendq/logging.py`
- Create: `pipeline/tests/test_config.py`, `pipeline/tests/test_errors.py`
- Create: `docs/architecture.md`, `docs/data-model.md`, `docs/ingestion.md`, `docs/data-quality.md`, `docs/deployment.md`
- Create: `docs/decisions/0001-free-tier-architecture.md`, `0002-batch-before-streaming.md`, `0003-deterministic-first.md`, `0004-neon-postgresql.md`

**Interfaces:** `Settings.from_env()`, `ErrorCode`, `IngestionError`, and `log_event()` establish the shared configuration/error/logging contracts.

- [x] Write failing tests for required `DATABASE_URL`, endpoint defaults, and public-safe error codes.
- [x] Run `pytest pipeline/tests/test_config.py pipeline/tests/test_errors.py -q` and confirm the missing package/config failure.
- [x] Implement minimal settings, error taxonomy, JSON-friendly logging, ignore rules, Compose PostgreSQL healthcheck, and truthful foundational docs.
- [x] Re-run the focused tests and confirm they pass.

### Task 2: PostgreSQL migrations and persistence primitives

**Files:**
- Create: `db/migrations/001_initial.sql`, `pipeline/opendq/storage/__init__.py`, `pipeline/opendq/storage/migrations.py`, `pipeline/opendq/storage/repository.py`
- Create: `pipeline/tests/test_migrations.py`, `pipeline/tests/test_repository.py`, `pipeline/tests/conftest.py`

**Interfaces:** `apply_migrations(conn)`, `Repository.create_ingestion_run(...)`, `Repository.finish_ingestion_run(...)`, `Repository.upsert_observations(...)`, and `Repository.source_statuses()`.

- [x] Write failing repository tests for schema creation, FK/unique constraints, run lifecycle, and duplicate upserts.
- [x] Run focused tests against a disposable PostgreSQL and confirm the expected missing migration/repository failures.
- [x] Implement deterministic SQL migration application and parameterized repository operations with transaction-safe `ON CONFLICT DO NOTHING`.
- [x] Re-run migration and repository tests, including an empty-database migration.

### Task 3: Canonical contracts and deterministic source adapters

**Files:**
- Create: `pipeline/opendq/contracts/models.py`, `pipeline/opendq/sources/base.py`, `pipeline/opendq/sources/open_meteo.py`, `pipeline/opendq/sources/usgs.py`
- Create: `pipeline/tests/fixtures/open_meteo.json`, `pipeline/tests/fixtures/usgs_earthquakes.json`
- Create: `pipeline/tests/test_open_meteo.py`, `pipeline/tests/test_usgs.py`, `pipeline/tests/test_contracts.py`

**Interfaces:** `SourceAdapter`, `OpenMeteoAdapter.fetch()`, `OpenMeteoAdapter.normalize(payload)`, `USGSAdapter.fetch()`, `USGSAdapter.normalize(payload)`, `WeatherObservation`, and `EarthquakeObservation`.

- [x] Write failing fixture-backed tests for parsing, UTC normalization, canonical field names, and malformed-record rejection.
- [x] Run source-focused tests and confirm they fail because adapters/contracts are absent.
- [x] Implement injected async HTTP adapters, transport parsing, Pydantic models, compact provenance data, and explicit rejected-record reporting.
- [x] Run source/contract tests and confirm all valid/invalid cases behave as designed.

### Task 4: Ingestion orchestration and CLI

**Files:**
- Create: `pipeline/opendq/ingestion/runner.py`, `pipeline/opendq/ingestion/results.py`, `pipeline/opendq/__main__.py`
- Create: `pipeline/tests/test_ingestion.py`, `pipeline/tests/test_cli.py`

**Interfaces:** `run_source(source_slug, repository, adapter) -> IngestionResult`, `run_all(...) -> list[IngestionResult]`, and CLI commands `python -m opendq ingest open-meteo|usgs|all`.

- [x] Write failing tests for first ingestion, identical second ingestion mapping to `NO_CHANGE`, handled timeout mapping to `FAILED`, and `all` partial failure.
- [x] Run focused orchestration tests and confirm expected missing-runner failures.
- [x] Implement run-before-fetch, terminal finalization in `finally`, sanitized errors, per-source reporting, and correct exit codes.
- [x] Re-run orchestration/CLI tests with fixture adapters and confirm deterministic behavior.

### Task 5: Minimal Next.js web and APIs

**Files:**
- Create: `apps/web/package.json`, `apps/web/package-lock.json`, `apps/web/tsconfig.json`, `apps/web/next.config.ts`, `apps/web/postcss.config.mjs`, `apps/web/tailwind.config.ts`
- Create: `apps/web/app/layout.tsx`, `apps/web/app/page.tsx`, `apps/web/app/globals.css`, `apps/web/app/api/health/route.ts`, `apps/web/app/api/sources/route.ts`
- Create: `apps/web/lib/config.ts`, `apps/web/lib/db.ts`, `apps/web/lib/status.ts`, `apps/web/tests/status.test.ts`

**Interfaces:** GET `/api/health` returns application plus database status; GET `/api/sources` returns persisted source status and honest empty data.

- [x] Write failing status tests for healthy DB, unavailable DB, and empty source state.
- [x] Run the web test/lint/typecheck command and confirm failure due to missing app files.
- [x] Implement a compact responsive status page, short-timeout parameterized read queries, sanitized route responses, and no fake metrics.
- [x] Run web tests, lint, typecheck, and production build.

### Task 6: CI, scheduled ingestion, fixtures, and final documentation

**Files:**
- Create: `.github/workflows/ci.yml`, `.github/workflows/ingest.yml`, `scripts/secret-scan.ps1`, `scripts/migrate.ps1`, `scripts/verify.ps1`
- Modify: `README.md`, `docs/deployment.md`, `docs/ingestion.md`

- [x] Write workflow/config checks for pinned action majors, PostgreSQL service use, no PR ingestion, six-hour schedule, and concurrency group.
- [x] Run local config/secret scans and confirm they detect forbidden Cloudflare or secret patterns if introduced.
- [x] Implement CI gates (`ruff check`, `ruff format --check`, `mypy`, `pytest`, web lint/typecheck/build), manual/scheduled ingestion requiring `DATABASE_URL`, and bounded verification helpers.
- [x] Run the full local verification matrix: Git status, Docker config/start/health, empty migration, schema constraints, deterministic test suite with exact count, Python gates, web gates, fixture first/second ingestion, malformed rejection, timeout/failure, partial `all`, web healthy/unavailable DB, secret scan, and Cloudflare zero search.
- [x] Review all changed files for dead code, stale template text, misleading claims, and accidental secrets; record `NOT_RUN` for unavailable owner-gated deployment/live checks.
