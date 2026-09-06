# OpenDQ Observatory

Deterministic data reliability and observability for public-data pipelines—with quality validation, drift detection, incident lifecycle, lineage-aware blast radius, deterministic RCA, and optional AI-assisted incident explanations.

## Live demo

[OpenDQ Observatory](https://opendq-observatory.vercel.app/)

The live dashboard is read-only and backed by persisted Vercel/Neon production evidence. Start with the system health panel, then follow the reviewer path below.

## Production console

These screenshots show real read-only production state captured for the v1.0.1 UI hardening release; live values continue to evolve with scheduled runs.

![OpenDQ operational overview](docs/screenshots/v1.0.1/overview-desktop.png)

| Drift evidence | Lineage and downstream impact |
| --- | --- |
| ![OpenDQ drift view](docs/screenshots/v1.0.1/drift-desktop.png) | ![OpenDQ lineage view](docs/screenshots/v1.0.1/lineage-desktop.png) |

![OpenDQ incident detail with deterministic RCA](docs/screenshots/v1.0.1/incident-detail-desktop.png)

Mobile layout is verified at 390px with no page-level horizontal overflow.

## What it solves

Public data pipelines can return HTTP 200 while quietly changing shape, freshness, validity, or distribution. OpenDQ turns those observations into explicit, queryable evidence instead of a single opaque health score.

## 5-minute review

1. Open the [live dashboard](https://opendq-observatory.vercel.app/).
2. Review [/quality](https://opendq-observatory.vercel.app/quality) for rule-level evidence.
3. Review [/drift](https://opendq-observatory.vercel.app/drift) for bounded PSI/schema signals.
4. Open [/incidents](https://opendq-observatory.vercel.app/incidents) and inspect an incident.
5. Follow deterministic RCA, evidence, and blast radius on the incident detail page.
6. Open [/lineage](https://opendq-observatory.vercel.app/lineage) and [/reliability](https://opendq-observatory.vercel.app/reliability), then read the diagrams in [docs/architecture.md](docs/architecture.md).

## Capability status

| Capability | Status |
| --- | --- |
| Public-data ingestion | Implemented |
| Data contracts and idempotency | Implemented |
| Data quality | Implemented |
| Drift detection | Implemented |
| Incident lifecycle | Implemented |
| Lineage / blast radius | Implemented |
| Deterministic RCA | Implemented |
| AI Incident Copilot | Optional / provider-dependent; Groq live-verified for one bounded production smoke |
| Streaming | Not part of v1 |

## Architecture and production flow

```mermaid
flowchart TD
    Sources[Open-Meteo / USGS] --> Actions[GitHub Actions · six-hour batch]
    Actions --> Pipeline[Python ingestion, quality, drift, incidents, RCA]
    Pipeline --> DB[(Neon PostgreSQL)]
    DB --> Web[Next.js read-only APIs and dashboard]
    Pipeline --> AI[Optional Groq → Gemini → deterministic fallback]
    AI --> DB
    Web --> Vercel[Vercel Hobby]
```

The scheduler is GitHub Actions, not Vercel. See [architecture](docs/architecture.md) and the smaller [evidence/data-flow diagram](docs/data-flow.md).

```text
Observation → Rule Result → Drift Result → Incident → Evidence
           → Lineage Impact → Deterministic RCA → Optional explanation
```

## Engineering decisions

- deterministic-first: AI cannot change quality, drift, incident, lineage, or RCA state;
- explicit SQL and visible migrations are the schema authority;
- database-enforced observation idempotency and one active incident per dataset/rule;
- quality outcome, drift outcome, and execution reliability remain separate;
- lineage impact is snapshotted when an incident opens;
- deterministic RCA runs before optional AI and keeps evidence IDs;
- external providers receive bounded `PUBLIC_ONLY` data, with schema validation, grounding checks, quotas, caching, and deterministic fallback;
- public GET routes read persisted state and never trigger inference or mutation;
- the design stays batch-based and free-tier aware.

## Reliability and safety

The [SLO definition](docs/slo.md) derives execution SLIs from persisted history and reports `INSUFFICIENT_HISTORY` where evidence is short. The [free-tier architecture](docs/free-tier-architecture.md) documents the current cost boundary and its policy caveat. The local [incident demo](docs/demo.md) is guarded by `APP_ENV=demo`/`DEMO_DATABASE_URL` and refuses production-looking targets.

Production currently uses deterministic fallback for most AI analyses. Groq adapters, routing, structured validation, evidence grounding, and persistence are implemented and tested; one bounded Groq production smoke is persisted and live-verified. Gemini is not live-verified. AI remains non-authoritative.

## Local setup

Requirements: Python 3.12+, Node.js 22+, npm, `uv`, and Docker Desktop.

```powershell
Copy-Item .env.example .env
docker compose up -d postgres
uv venv pipeline/.venv
uv pip install --python pipeline/.venv/Scripts/python.exe -e "pipeline[dev]"
pipeline/.venv/Scripts/python.exe -m opendq migrate
```

Run the web app:

```powershell
cd apps/web
npm ci
npm run dev
```

The web app reports unavailable/degraded state without a database; it does not invent operational metrics.

## Safe demo and benchmark

```powershell
$env:APP_ENV = "demo"
$env:DEMO_DATABASE_URL = "postgresql://opendq:opendq@localhost:5432/opendq_demo"
pipeline/.venv/Scripts/python.exe -m opendq demo incident
Remove-Item Env:APP_ENV, Env:DEMO_DATABASE_URL
```

The demo narrates healthy data → quality/drift failure → incident → lineage impact → RCA → fallback → recovery. It never targets Neon. The local benchmark is `scripts/benchmark.ps1`; results and environment are recorded in [docs/performance-baseline.md](docs/performance-baseline.md).

## Testing and release evidence

Python gates:

```powershell
cd pipeline
.venv/Scripts/ruff.exe check opendq tests
.venv/Scripts/ruff.exe format --check opendq tests
.venv/Scripts/mypy.exe opendq
.venv/Scripts/python.exe -m pytest
```

Web gates:

```powershell
cd apps/web
npm test
npm run lint
npm run typecheck
npm run build
```


Post-deploy UI contract:

```powershell
npm run verify:production-ui -- https://opendq-observatory.vercel.app
```

This verifies that production HTML references stylesheets containing the OpenDQ shell selectors, catching deployment artifact/cache regressions that an HTTP 200 alone cannot detect.

CI uses disposable PostgreSQL and deterministic fixtures. It does not call public APIs or external AI providers. Release evidence, security checks, browser QA, screenshots, and known limitations live in [docs/releases/v1.0.0-evidence.md](docs/releases/v1.0.0-evidence.md).

## Interview path and trade-offs

Read [docs/interview-guide.md](docs/interview-guide.md) for the rationale behind idempotency, quality versus drift, state transitions, PSI, RCA boundaries, AI safety, and a hypothetical streaming boundary.

OpenDQ is intentionally batch, small-source, PostgreSQL-backed, and deterministic. PSI is a compact signal rather than universal drift truth; RCA is evidence ranking rather than causal discovery; Neon Free and Vercel Hobby impose resource constraints; AI providers are optional and quota-bound.

## Roadmap boundary

Streaming, Kafka/Redpanda, authentication, notifications, billing, multi-tenancy, autonomous remediation, and additional AI surfaces are deferred. They are not required to demonstrate the current reliability problem well.

## Documentation

- [Architecture](docs/architecture.md) · [Data flow](docs/data-flow.md) · [Data model](docs/data-model.md)
- [SLOs](docs/slo.md) · [Free-tier architecture](docs/free-tier-architecture.md) · [Performance baseline](docs/performance-baseline.md)
- [Quality](docs/data-quality.md) · [Drift](docs/drift.md) · [Incidents](docs/incidents.md) · [RCA](docs/root-cause-analysis.md) · [Lineage](docs/lineage.md)
- [AI Incident Copilot](docs/ai-incident-copilot.md) · [Local demo](docs/demo.md) · [Interview guide](docs/interview-guide.md) · [Deployment](docs/deployment.md)
- [Architecture decisions](docs/decisions/) · [Production snapshot](docs/production-snapshot-2026-09-06.md)
