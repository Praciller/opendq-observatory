# Security and artifact review

Phase 6 review scope: public route handlers, workflow permissions, dependency reports, secret/artifact scans, and production-safe boundaries.

## Public boundary

- Public API handlers are read-only `GET` surfaces.
- Incident acknowledgement remains a trusted Python CLI operation; no public mutation route exists.
- AI inference is run by the bounded workflow/CLI; `GET /api/incidents/<id>/ai` reads persisted output and never invokes a provider.
- Provider input is public-only and bounded; raw prompts, raw provider responses, credentials, and unrestricted source payloads are not persisted.
- Demo and benchmark commands require `APP_ENV=demo` or `APP_ENV=test` plus a separate local PostgreSQL URL; they refuse production-looking hosts.

## CI and dependencies

CI has `contents: read`, uses a non-canceling production-ingestion concurrency group, keeps public-PR tests independent from Neon, and passes provider credentials only to the scheduled workflow environment. No new runtime dependency was added in Phase 6.

Fresh command output for the final release will be recorded in [v1.0.0 evidence](releases/v1.0.0-evidence.md); this document intentionally contains no credentials or secret-bearing environment values.
