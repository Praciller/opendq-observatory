# SQL migration integrity

OpenDQ uses `pipeline/opendq/storage/migrations.py` as the only schema migration runner.
Migrations run in sorted filename order inside one PostgreSQL transaction with a
project-specific `pg_advisory_xact_lock` that serializes concurrent runners.

Each migration's SHA-256 is stored in `schema_migrations.checksum`. Later runs:

- Reject an applied filename missing from `db/migrations/`.
- Reject an applied SQL file whose bytes differ from its recorded checksum.
- Apply all pending SQL and checksum records atomically, rolling back the batch on failure.
- Preserve existing `001`–`006` filenames and the future Phase 7 migration namespace.

## Existing production databases

Pre-checksum v1 databases have `schema_migrations(version, applied_at)`.
Unattended `opendq migrate` now **fails closed** on a legacy ledger with no
`checksum` column. In particular, the six-hour scheduled ingestion cannot
silently backfill migration checksums. The only explicit one-time adoption
path, **after independently reviewing the production schema and ledger and
arranging a backup/recovery plan**, is:

```sh
cd pipeline
uv run python -m opendq migrate --adopt-legacy-checksums
```

The explicit flag adds a nullable `checksum` column and baselines existing
versions from the **currently reviewed SQL files**, only if **no new SQL
migrations are pending**. This trust-on-first-use operation **cannot prove**
historic SQL matches the repository and must never be used simply to suppress
drift warnings. If there is no ledger (fresh database), regular `migrate`
continues to create all tables without this flag.
Before release, review the production migration versions and schema against the
committed SQL files, and retain a database backup/recovery plan.

No migration named `007` is introduced here, to avoid colliding with Phase 7.
The ledger enhancement is performed by the trusted migration runner.

## Safe release checklist

1. Review existing production schema and migration versions in read-only mode.
2. Test the migration runner against a disposable PostgreSQL 16 database in CI.
3. Reconcile Phase 7 migration filenames and confirm a current production backup.
4. Plan a coordinated migration window; unattended ingestion will fail closed
   on an unbaselined legacy ledger if the runner is deployed prematurely.
5. After **separate explicit owner approval**, apply `--adopt-legacy-checksums`
   only for an independently verified legacy ledger, with no pending SQL files.
6. Confirm a `VERIFIED` read-only preflight result and ordinary idempotent
   `migrate` before resuming normal scheduled ingestion.
7. Keep this PR Draft until the database and rollout gates are completed.

Future schema migrations should only be **added**, never edited after application.
Do not suppress checksum mismatch errors or overwrite production checksums to make
a failing migration pass. Use a new additive SQL migration to change a schema.

## Required read-only preflight

Before enabling this migration runner against an existing database, execute the
inspector **without performing any migration**:

```sh
cd pipeline
# Ensure DATABASE_URL targets the intended database; never print the secret.
uv run python scripts/migration_preflight.py
```

The CLI starts a PostgreSQL transaction with `SET TRANSACTION READ ONLY`,
executes SELECT queries only, and returns redacted JSON metadata (migration
filenames, drift and ledger state, no DSN, credentials or row-level data).

Preflight states:

- `VERIFIED`: existing SHA-256 ledger matches current SQL files.
- `LEGACY_REVIEW_REQUIRED`: ledger predates checksums. Historical SQL cannot
  be proven from the current files. Independent schema review is mandatory.
- `PENDING_REVIEW`: new unapplied SQL files exist; they require a separate release.
- `BLOCKED`: unexpected applied versions (including an existing Phase 7 `007`
  absent in this checkout), checksum mismatch, missing ledger, or missing SQL files.

The CLI returns a nonzero exit code unless the ledger is already `VERIFIED`.
This does **not** authorize applying changes; operator approval and a recovery
plan are separate gates. The connected Neon project must be positively
identified as OpenDQ Production before executing the query. Do not substitute
another accessible Neon project or pass production secrets into logs.
