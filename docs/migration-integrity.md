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
On the first invocation, the runner adds a nullable `checksum` column and fills
checksums for applied versions using the **currently reviewed SQL files**.
This is a one-time trust-on-first-use adoption. It **cannot prove** that historic
SQL executed in production matches those files or detect preexisting schema drift.
Before release, review the production migration versions and schema against the
committed SQL files, and retain a database backup/recovery plan.

No migration named `007` is introduced here, to avoid colliding with Phase 7.
The ledger enhancement is performed by the trusted migration runner.

## Safe release checklist

1. Review existing production schema and migration versions in read-only mode.
2. Test the migration runner against a disposable PostgreSQL 16 database in CI.
3. Approve and merge the change independently of in-progress Phase 7 work.
4. Apply to production only during an approved ingestion/deployment window.
5. Check the audit output and schema ledger; stop if migration drift is detected.

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
