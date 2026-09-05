# OpenDQ Observatory

Open-source data reliability, drift detection, lineage, and AI-assisted incident intelligence platform.

OpenDQ Observatory is a public portfolio project for AI Engineering, Data Engineering, Data Quality, Data Observability, Data Contracts, Lineage, and MLOps roles. It uses only public data and keeps the first release deterministic and free-tier aware.

> Screenshot placeholder: add a hosted dashboard capture after the production database baseline is established.

## Project status

**Phase 0–1:** Foundation and two public-data ingestion adapters are implemented in this repository. The web surface is intentionally a small system/source status page.

### Hosted demo (limited)

- Public URL: [opendq-observatory.vercel.app](https://opendq-observatory.vercel.app/)
- The Next.js web surface is deployed and renders the honest degraded state.
- Neon production storage, the GitHub Actions `DATABASE_URL` secret, and live scheduled ingestion are not configured in this environment. Until those owner-authenticated steps are completed, `/api/health` returns `503` with `database: unavailable` and `/api/sources` returns an unavailable empty state.
- Local Docker PostgreSQL, migrations, live-source smoke evidence, and seeded records remain local-only verification.

### Implemented

- Python 3.12+ ingestion package with structured logs, explicit error taxonomy, Pydantic contracts, and CLI.
- Open-Meteo hourly forecast ingestion for a fixed Bangkok demo location.
- USGS GeoJSON earthquake feed ingestion.
- PostgreSQL migrations, ingestion-run lifecycle, provenance-bearing observations, and database-enforced idempotency.
- Next.js App Router status page with database-aware `/api/health` and `/api/sources` endpoints.
- Docker Compose PostgreSQL, deterministic tests, GitHub Actions CI, and six-hour scheduled ingestion workflow.

### Planned

Data-quality rules, drift detection, incident lifecycle, lineage/blast-radius views, deterministic root-cause evidence, and optional AI explanations are Phase 2+ work. Kafka/Redpanda, authentication, notifications, billing, and multi-tenancy are also deferred.

## Architecture

```text
Open-Meteo / USGS → fetch → parse → normalize → Pydantic contract
                                      ↓
                              PostgreSQL + run record
                                      ↓
                              Next.js status/API
```

Production targets are Vercel Hobby for the web app, Neon PostgreSQL Free for storage, and GitHub Actions for scheduled micro-batches. Local development uses Docker Compose PostgreSQL. Cloudflare is not part of this project.

## Local setup

Requirements: Python 3.12+, Node.js 22+, npm, and Docker Desktop.

```powershell
Copy-Item .env.example .env
docker compose up -d postgres
uv venv pipeline/.venv
uv pip install --python pipeline/.venv/Scripts/python.exe -e ".[dev]" --directory pipeline
pipeline/.venv/Scripts/python.exe -m opendq migrate
```

The `.env` file is local-only and ignored by Git. The Compose credentials are demo-only local credentials, not production secrets.

## Ingestion

```powershell
pipeline/.venv/Scripts/python.exe -m opendq ingest open-meteo
pipeline/.venv/Scripts/python.exe -m opendq ingest usgs
pipeline/.venv/Scripts/python.exe -m opendq ingest all
```

Repeated ingestion is safe: weather uses dataset/location/timestamp uniqueness and USGS uses the canonical event ID. A repeat with no new logical records is reported as `NO_CHANGE` and exits successfully.

## Web app

```powershell
cd apps/web
npm ci
npm run dev
```

Open `http://localhost:3000`. Without a database, the page reports a degraded/unavailable state; it does not invent operational metrics.

## Tests and quality gates

```powershell
cd pipeline
.venv/Scripts/python.exe -m pytest
.venv/Scripts/ruff.exe check opendq tests
.venv/Scripts/ruff.exe format --check opendq tests
.venv/Scripts/mypy.exe opendq
cd ../apps/web
npm ci
npm run lint
npm run typecheck
npm run build
```

CI uses disposable PostgreSQL and deterministic fixtures. It does not call public APIs. Live source smoke checks are separate and are reported as `NOT_RUN` when unavailable.

## Documentation

- [Architecture](docs/architecture.md)
- [Data model](docs/data-model.md)
- [Ingestion](docs/ingestion.md)
- [Data quality roadmap](docs/data-quality.md)
- [Deployment](docs/deployment.md)
- [Architecture decisions](docs/decisions/)

## Free-tier philosophy

The project favors scheduled micro-batches, public endpoints without credentials, one small PostgreSQL service, bounded raw provenance, and portable business logic. Neon/Vercel deployment remains owner-authenticated work and is reported separately from local verification.
