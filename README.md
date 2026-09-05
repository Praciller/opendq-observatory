# OpenDQ Observatory

Open-source data reliability, drift detection, lineage, and AI-assisted incident intelligence platform.

OpenDQ Observatory is a public portfolio project for AI Engineering, Data Engineering, Data Quality, Data Observability, Data Contracts, Lineage, and MLOps roles. It uses only public data and keeps the first release deterministic and free-tier aware.

> Screenshot placeholder: add a hosted dashboard capture after owner review.

## Project status

**Phase 1.5:** Production ingestion foundation is frozen at `v0.1.0`. The Vercel/Neon deployment, scheduled ingestion, and idempotent persistence are verified.

**Phase 2:** The deterministic Data Quality Engine is frozen at `v0.2.0`.

**Phase 3:** Deterministic incident detection, lineage, and blast-radius evidence are implemented on `main`.

### Hosted demo

- Public URL: [opendq-observatory.vercel.app](https://opendq-observatory.vercel.app/)
- The Vercel Hobby deployment is backed by a Vercel-managed Neon PostgreSQL Free resource and returns HTTP 200 from `/api/health` with a healthy database.
- `/api/sources` reports both Open-Meteo and USGS Earthquakes as enabled with successful ingestion metadata.
- `/api/quality`, `/api/quality/sources`, and `/quality` expose persisted production rule results; the current real datasets report quality scores of 100.0 with volume checks explicitly skipped until five baseline runs exist.
- `/api/incidents`, `/api/lineage`, `/incidents`, and `/lineage` expose read-only incident lifecycle and lineage evidence from Neon.
- GitHub Actions has a production `DATABASE_URL` secret and a scheduled ingestion workflow; the verified workflow is idempotent and reports `NO_CHANGE` when no new logical records are available.
- The deployed resource currently has Neon Auth provisioned by the marketplace integration, although this application does not use authentication. Disabling that extra service requires owner email verification in the provider UI and remains an explicit follow-up.
- The Vercel project is not connected to GitHub automatic deployments; production deployment is currently owner-triggered.
- Local Docker PostgreSQL, migrations, live-source smoke evidence, and seeded records remain local-only verification.

### Implemented

- Python 3.12+ ingestion package with structured logs, explicit error taxonomy, Pydantic contracts, and CLI.
- Open-Meteo hourly forecast ingestion for a fixed Bangkok demo location.
- USGS GeoJSON earthquake feed ingestion.
- PostgreSQL migrations, ingestion-run lifecycle, provenance-bearing observations, and database-enforced idempotency.
- Deterministic quality rules for freshness, completeness, uniqueness, validity/range, timestamp continuity, and volume baselines, with persisted explainable results and transparent scores.
- Deterministic incident lifecycle with database-enforced active deduplication, event history, automatic recovery, and trusted CLI acknowledgement.
- Idempotent provider-neutral lineage seed, bounded downstream traversal, and incident blast-radius snapshots.
- Next.js App Router status, quality, incident, and lineage pages with database-aware APIs.
- Next.js quality API/detail page, Docker Compose PostgreSQL, deterministic tests, GitHub Actions CI, and six-hour ingestion-plus-quality workflow.

### Planned

Drift detection, deterministic root-cause evidence, optional AI explanations, and streaming remain later-phase work. Kafka/Redpanda, authentication, notifications, billing, and multi-tenancy are also deferred.

## Architecture

```text
Open-Meteo / USGS → fetch → parse → normalize → Pydantic contract
                                      ↓
                              PostgreSQL + run record
                                      ↓
                         quality evaluation + incidents
                                      ↓
                         lineage-aware read-only APIs/UI
```

Production uses Vercel Hobby for the web app, a Vercel-managed Neon PostgreSQL Free resource for storage, and GitHub Actions for scheduled micro-batches. Local development uses Docker Compose PostgreSQL. Cloudflare is not part of this project.

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
pipeline/.venv/Scripts/python.exe -m opendq lineage seed
```

Repeated ingestion is safe: weather uses dataset/location/timestamp uniqueness and USGS uses the canonical event ID. A repeat with no new logical records is reported as `NO_CHANGE` and exits successfully.

## Incidents and lineage

```powershell
pipeline/.venv/Scripts/python.exe -m opendq incident list
pipeline/.venv/Scripts/python.exe -m opendq incident list --status open
pipeline/.venv/Scripts/python.exe -m opendq incident show <incident-id>
pipeline/.venv/Scripts/python.exe -m opendq incident acknowledge <incident-id>
pipeline/.venv/Scripts/python.exe -m opendq lineage show open-meteo
pipeline/.venv/Scripts/python.exe -m opendq lineage impact open-meteo
```

The public app is read-only for incident state. A trusted operator CLI may acknowledge an OPEN incident; quality PASS results resolve OPEN or ACKNOWLEDGED incidents automatically. See [incident semantics](docs/incidents.md) and [lineage](docs/lineage.md).

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

The project favors scheduled micro-batches, public endpoints without credentials, one small PostgreSQL service, bounded raw provenance, and portable business logic. Provider settings that require owner verification, including disabling the unintended Neon Auth add-on and enabling GitHub automatic deployments, are reported separately from the verified production path.
