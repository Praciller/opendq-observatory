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
