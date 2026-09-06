# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary users are recruiters and engineers evaluating a public data-reliability product. They need to understand the operational state quickly, then inspect persisted evidence and follow an incident or lineage path without changing system state.

## Product Purpose

OpenDQ Observatory turns public-data pipeline observations into explicit, queryable evidence for data quality, drift, incidents, lineage, deterministic root-cause analysis, optional AI explanations, and execution reliability. Success means a visitor can distinguish application availability, data outcomes, statistical drift, incident state, and measured execution history without fabricated metrics or hidden mutations.

## Positioning

Deterministic-first, read-only observability for public-data pipelines. Quality, drift, incident, lineage, and RCA state are owned by persisted evidence; optional AI may explain evidence but cannot change it.

## Operating Context

The web surface is a public Next.js App Router dashboard backed by persisted PostgreSQL/Neon evidence. It is reviewed locally and through a Vercel demo. The current product uses scheduled batch ingestion for Open-Meteo weather observations and USGS earthquake events. The dashboard is an investigation surface, not an administration or mutation surface.

## Capabilities and Constraints

- Routes currently include Overview, Quality, Drift, Incidents, Incident detail, Lineage, dataset Lineage, and Reliability.
- Web reads use existing read-only APIs and data access helpers; response contracts and route behavior are preserved.
- Empty, unavailable, insufficient-baseline, and insufficient-history states must remain explicit.
- No database migration, external analytics, paid service, Cloudflare dependency, public mutation handler, or public AI inference handler may be added for presentation work.
- Development phase language belongs in documentation, not production UI.

## Brand Commitments

Keep the OpenDQ Observatory name and deterministic-first, trustworthy operational voice. The redesign uses the requested restrained graphite/slate console with one teal/cyan accent and semantic state colors.

## Evidence on Hand

The repository contains the implemented web route and API surfaces, persisted-data mapping helpers under `apps/web/lib`, deterministic tests under `apps/web/tests`, and product/architecture evidence in `README.md` and `docs/`. No fabricated trend data, testimonials, or commercial claims are available or permitted.

## Product Principles

1. Persisted evidence is the source of truth.
2. Operational state and data state remain distinct.
3. Investigation paths should be visible within seconds.
4. Missing evidence is a valid, clearly explained result.
5. Public read-only behavior is a product boundary.

## Accessibility & Inclusion

The web console must provide semantic landmarks and headings, keyboard-visible focus, skip navigation, touch-sized controls, non-color status cues, and responsive layouts without horizontal overflow at 390px.
