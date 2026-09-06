# Free-tier architecture evidence

Captured for the Phase 6 release candidate on 2026-09-06. The current deployed project is verified on Vercel Hobby and Neon Free, with a public GitHub repository and a six-hour GitHub Actions workflow. Open-Meteo and USGS provide the public source feeds; AI providers are optional and quota-bound.

## Why the footprint stays small

- No always-on worker exists: scheduled GitHub Actions runs the bounded batch and exits.
- No Kafka, Redpanda, Flink, Redis, hosted monitoring service, or second cloud provider is required.
- PostgreSQL stores normalized observations, compact evidence, run records, and bounded JSON; the current production snapshot is small.
- Drift uses bounded latest windows and versioned baselines rather than an unbounded event stream.
- AI calls are opt-in, limited per run/incident, fingerprint-cached, and persisted; public GET requests never call a provider.
- The web/API surface is read-only for ingestion, quality, drift, incident mutation, baselines, rules, and AI generation.

## Cost boundary

The architecture is designed for `$0/month under the currently verified free-plan policies until provider policies or usage requirements change.` This is a current design assumption, not a perpetual price guarantee. Vercel describes Hobby as free for personal projects, GitHub documents standard Actions runners as free in public repositories, and Open-Meteo documents a free no-sign-up API. Check the provider terms before treating this as a production cost commitment.

References: [Vercel Hobby](https://vercel.com/docs/plans/hobby), [GitHub Actions billing](https://docs.github.com/en/actions/concepts/billing-and-usage), [Open-Meteo features](https://open-meteo.com/en/features), [USGS earthquake feeds](https://earthquake.usgs.gov/earthquakes/feed/).
