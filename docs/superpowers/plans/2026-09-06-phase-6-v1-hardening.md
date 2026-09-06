# Phase 6 Portfolio Hardening and v1.0 Release Candidate

> **For the implementer:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to execute this plan task by task. Use `superpowers:test-driven-development` for behavior changes and `superpowers:verification-before-completion` before release claims.

**Goal:** Make the existing deterministic OpenDQ Observatory explainable, demonstrable, accessible, and release-ready without introducing a new distributed system, data source, authentication layer, or major product capability.

**Architecture:** Derive reliability evidence from existing persisted ingestion, quality, drift, incident, RCA, lineage, and AI tables. Add a small read-only reliability surface only where the current schema supports honest measurements. Keep failure injection and the incident demo local/test-only, reuse existing repositories and services, and keep the public web app read-only. Documentation and release evidence will point to real outputs rather than invented metrics.

**Branch baseline:** `feat/v1-hardening` from `v0.5.0` at `e26232afd38345e2de6eb8b317a8b492dfc851d7`.

**Non-goals:** Kafka/Redpanda/Flink, new cloud providers, authentication, notifications, RAG/vector databases, autonomous remediation, new public data sources, broad dependency upgrades, production chaos testing, and fabricated scale/performance claims.

## Task 1: Define reliability evidence and add the optional read-only summary

**Files:** `apps/web/lib/reliability.ts`, `apps/web/app/api/reliability/route.ts`, `apps/web/app/reliability/page.tsx`, `apps/web/tests/reliability.test.ts`, `apps/web/app/page.tsx`, `apps/web/app/globals.css`, `docs/slo.md`.

- [x] Write web tests first for empty history, measured execution counts, `INSUFFICIENT_HISTORY`, separate execution/data-quality/drift states, bounded response fields, and sanitized database errors.
- [x] Implement SQL queries using existing indexed tables only: ingestion runs, quality evaluation runs, drift evaluation runs, incidents, and latest successful ingestion.
- [x] Report measured window, run counts, successes/failures, latest run, freshness timestamps, quality state, drift state, and open incidents without a universal health score.
- [x] Add a small `/reliability` page and a home-page link only if the route remains concise and responsive.
- [x] Document SLI/SLO definitions and explicitly label insufficient history; do not assert historical percentages that the database cannot calculate.
- [x] Run focused web tests and inspect the API response shape before continuing.

## Task 2: Add deterministic failure scenarios and demo safety

**Files:** `pipeline/opendq/failure_scenarios.py`, `pipeline/opendq/demo.py`, `pipeline/opendq/__main__.py`, `pipeline/tests/test_failure_scenarios.py`, `pipeline/tests/test_demo.py`, `docs/demo.md`.

- [x] Write tests for the scenario catalog and structured evidence fields: scenario, expected state, observed state, result, and duration.
- [x] Cover source timeout, invalid payload, database unavailable, timestamp gap, invalid range, schema change, distribution shift, quality failure, drift incident, resolution, primary AI failure, and all-provider failure using mocks/fixtures.
- [x] Add `python -m opendq demo incident` with an explicit `APP_ENV=demo` or `APP_ENV=test` requirement and a separate `DEMO_DATABASE_URL`; refuse missing or production-looking demo configuration.
- [x] Ensure the demo never falls back to `DATABASE_URL`, never calls public providers, and does not mutate Neon.
- [x] Reuse current repository, quality, drift, incident, lineage, RCA, and deterministic AI fallback services; do not create a second domain model.
- [x] Document the exact safe command, expected narrative, guard behavior, and the fact that generated evidence is runtime output rather than committed fixture data.

## Task 3: Add the flagship deterministic recovery regression

**Files:** `pipeline/tests/test_phase6_end_to_end.py`, existing repository/service modules only where a defect is exposed.

- [x] Write one integration test against the disposable PostgreSQL fixture that seeds a healthy fixture, ingests observations, evaluates quality and drift, seeds lineage, opens an incident, records blast-radius impact, computes deterministic RCA, persists deterministic AI fallback, restores healthy observations, re-evaluates, and asserts incident resolution.
- [x] Assert execution status separately from quality/drift outcome and assert no external HTTP calls occur.
- [x] Keep the test deterministic with fixed timestamps, fixture data, and injected provider failures.
- [x] Do not change schema unless this test exposes a genuine missing invariant; if no migration is required, record that fact in release evidence.

## Task 4: Capture a reproducible local performance baseline

**Files:** `scripts/benchmark.ps1`, `pipeline/opendq/benchmark.py` or a focused benchmark module, `docs/performance-baseline.md`.

- [x] Add a bounded local benchmark for fixture ingestion, quality, drift, incident reconciliation, RCA, and a representative read/query path.
- [x] Use a disposable local PostgreSQL database and fixed fixture sizes; never point the benchmark at production.
- [x] Report sample size, machine/runtime description, run count, median, and observed range; avoid a single best-run claim.
- [x] Run the benchmark once after implementation and record only the measured local result with date and environment.

## Task 5: Produce architecture, data-flow, free-tier, and interview documentation

**Files:** `docs/architecture.md`, `docs/data-flow.md`, `docs/free-tier-architecture.md`, `docs/interview-guide.md`, `docs/production-snapshot-2026-09-06.md`, `README.md`.

- [x] Add accurate Mermaid architecture and evidence/data-flow diagrams showing GitHub Actions as the scheduler, Python as the pipeline owner, Neon/PostgreSQL as persistence, and Vercel/Next.js as read-only presentation/API.
- [x] Document the current low-cost architecture, bounded AI calls/cache, no always-on worker/Kafka/Redis, public GET no-inference rule, and the conditional `$0/month` statement without promising perpetual free plans.
- [x] Capture a dated non-sensitive production snapshot from actual queries: sources, observations, rules, runs, incidents by status/kind, lineage nodes/edges, RCA, AI, and cadence.
- [x] Write interview talking points for deterministic-first design, idempotency, quality vs drift, incident state, partial unique index, lineage snapshots, PSI limitations, RCA boundaries, AI safety, free-tier trade-offs, and a hypothetical future Kafka boundary.
- [x] Rewrite README around the recruiter fast path: hero/live demo, problem, capabilities/status, architecture/flow, five-minute review, engineering decisions, reliability/safety, setup/testing/deployment, trade-offs, and roadmap.
- [x] Keep provider live status precise: Groq live-verified only if the persisted production row remains verifiable; Gemini remains not live-verified unless separately proven.

## Task 6: Review and repair UI/accessibility without novelty redesign

**Files:** `apps/web/app/layout.tsx`, all existing route pages, `apps/web/app/globals.css`, focused web tests, `docs/ui-review.md`.

- [x] Inspect `/`, `/quality`, `/drift`, `/incidents`, `/incidents/[id]`, `/lineage`, and `/reliability` for hierarchy, terminology, empty/error states, status semantics, dense evidence, table overflow, and navigation consistency.
- [x] Fix only genuine issues: semantic headings/landmarks, link labels, keyboard focus, visible status beyond color, table responsiveness, contrast, mobile spacing, and reduced-motion behavior if animation exists.
- [x] Preserve the existing visual language and avoid introducing a large component/design dependency; extract primitives only when duplication is already present.
- [x] Run browser-level QA with `agent-browser` at approximately 1440, 768, and 390 widths for the key routes; capture screenshots from real production data or clearly labeled deterministic local demo data.
- [x] Store the intentional screenshot set outside tracked runtime artifacts or in a clearly documented portfolio-assets location, and verify it contains no secrets.

## Task 7: Perform release hardening and evidence review

**Files:** `.github/workflows/ci.yml`, `.github/workflows/ingest.yml`, `docs/security-review.md`, `docs/database-query-review.md`, `docs/releases/v1.0.0-evidence.md`, `docs/releases/v1.0.0-checklist.md`.

- [x] Review CI permissions, concurrency, cache behavior, fork secret safety, pinned/official action versions, and deterministic independence from Neon; make only evidence-backed changes.
- [x] Review Python/npm dependencies, unused packages, secret/artifact hygiene, public mutation/inference handlers, API semantics, bounded arrays, sanitized errors, indexes, cascades, and expensive production query paths.
- [x] Run `scripts/secret-scan.ps1`, npm audit, available Python dependency security checks, Cloudflare reference search, and route-handler searches.
- [x] Record current production endpoint checks, migration state, scheduled workflow evidence, deployment/plan evidence, real snapshot counts, limitations, and provider verification without secrets.
- [x] Create the concise v1 checklist and do not mark any item complete without command or endpoint evidence.

## Task 8: Full verification, feature CI, merge, deploy, and release

**Files:** release evidence/checklist updates only after fresh outputs.

- [x] Run full Python gates: Ruff check, Ruff format check, mypy, pytest, failure scenario tests, demo guard tests, and the end-to-end recovery flow.
- [x] Run web test, lint, typecheck, and production build; run browser QA and confirm final API contracts.
- [x] Run migration verification from an empty database and confirm no Phase 6 migration exists unless justified.
- [x] Commit the hardening work, push `feat/v1-hardening`, and record the successful feature CI run ID/SHA.
- [x] Merge safely to `main`, require merge CI green, and record merge SHA/run ID.
- [x] Deploy the exact merged checkout to the existing canonical Vercel project only; verify READY, canonical alias, health, sources, quality, drift, incidents, lineage, RCA, AI, and reliability endpoints.
- [x] Run one final controlled `workflow_dispatch` from the verified v1 merge SHA and record the run ID/SHA and bounded AI behavior.
- [x] Capture final production browser screenshots and verify desktop/mobile routes.
- [ ] If all mandatory gates pass, create annotated tag `v1.0.0` on the exact verified merge SHA and a concise GitHub Release. If a mandatory owner-only action blocks this, record `BLOCKED`/`COMPLETE_WITH_LIMITATIONS` with the exact blocker and stop.
- [ ] Do not begin v1.1 feature work after the release decision.

## Verification matrix

- Python: `ruff check opendq tests`, `ruff format --check opendq tests`, `mypy opendq`, `pytest`.
- Web: `npm test`, `npm run lint`, `npm run typecheck`, `npm run build`.
- Security: secret scan, `npm audit`, available trusted Python dependency check, no Cloudflare dependency/reference, no public mutation or inference handlers.
- Runtime: disposable DB migrations, deterministic demo/failure suite, production non-destructive endpoint checks, final scheduled workflow, browser screenshots at desktop/tablet/mobile widths.
- Release evidence: every PASS/COMPLETE claim maps to fresh output, a committed document, a public endpoint, a CI run, or an explicitly labeled owner-gated limitation.
