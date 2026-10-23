# SQL migration integrity

OpenDQ uses `pipeline/opendq/storage/migrations.py` as the only schema migration runner.
Migrations run in sorted filename order inside one PostgreSQL transaction with a
project-specific `pg_advisory_xact_lock` that serializes concurrent runners.

Each migration's SHA-256 is stored in `schema_migrations.checksum`. Later runs:

- Reject an applied filename missing from `db/migrations/`.
- Reject an applied SQL file whose bytes differ from its recorded checksum.
- Apply all pending SQL and checksum records atomically, rolling back the batch on failure.
- Preserve existing `001`–`006` filenames and the future Phase 7 migration namespace.

## Stage 1: deploy without schema changes or backups

For the initial live deployment **without a schema migration**, the scheduled
ingestion workflow runs `opendq migrate --no-schema-change`. This mode only
checks that the migration ledger exists, all repository SQL filenames have
already been applied and none are unknown. It validates checksums when a
checksummed ledger exists. On a legacy ledger, it **does not claim SQL
integrity**, does not write hashes and does not add columns. It also refuses
to run pending SQL migrations, preventing an accidental schema change from
scheduled ingestion. On a fresh database it fails closed instead of silently
creating schema.

This is the only stage that may proceed without the separately validated
production backup/recovery prerequisites below: its migration step makes
**zero persistent database or schema changes**. Scheduled ingestion still
performs its **normal application data writes**. The production schema was
read in Neon Console on 2026-10-24 and contained exactly the six migration
versions already present in the checkout. Recheck ledger state after merge
if an unexpected job failure occurs; do not manually backfill checksums to
clear a warning. No `007` migration or Phase 7 schema changes are included
in this stage.

The ordinary `opendq migrate` command deliberately remains fail-closed for
legacy ledgers. Manual `--adopt-legacy-checksums` is reserved for Stage 2
and is never invoked by the scheduled workflow.

## Stage 2: checksum adoption requires a recovery point

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

## Stage 2 checksum-adoption checklist

1. Review existing production schema and migration versions in read-only mode.
2. Test the migration runner against a disposable PostgreSQL 16 database in CI.
3. Reconcile Phase 7 migration filenames and confirm a current production backup.
4. Plan a coordinated checksum-adoption window; scheduled ingestion uses
   `--no-schema-change` and keeps running on a fully applied legacy ledger,
   but will refuse newly pending SQL migrations.
5. After **separate explicit owner approval**, apply `--adopt-legacy-checksums`
   only for an independently verified legacy ledger, with no pending SQL files.
6. Confirm a `VERIFIED` read-only preflight result and ordinary idempotent
   `migrate` before resuming normal scheduled ingestion.
7. Keep checksum adoption disabled until database and recovery gates are
   completed, even if the separate no-schema-change Stage 1 code ships.

Future schema migrations should only be **added**, never edited after application.
Do not suppress checksum mismatch errors or overwrite production checksums to make
a failing migration pass. Use a new additive SQL migration to change a schema.

## Stage 2 production adoption gate (evidence as of 2026-10-24)

This section is an **operator checklist**, not authorization for production
commands. Revalidate every item immediately before the release; the database
and scheduled jobs may have changed since these observations.

### Verified without modifying production

- Vercel's production `NEON_PROJECT_ID` for `opendq-observatory` matched
  the Neon Console project `neon-green-pebble` (ID
  `restless-lake-84436685`). The observed branch was `main`, database
  `neondb`, schema `public`. This does **not** independently verify the
  GitHub Actions `DATABASE_URL` secret targets that same database.
- The Neon Tables viewer showed all **20** distinct tables created by the
  repository's `001`–`006` SQL migrations. This is a **table-name-only**
  comparison, not a full column/index/constraint or historic SQL audit.
- `public.schema_migrations` contained exactly the six migration filenames
  `001_initial.sql` through `006_ai_incident_copilot.sql`. The ledger had
  `version` and `applied_at`, but **no `checksum`**; no `007` was recorded.
  Therefore this is a **legacy ledger**. The read-only preflight CLI has not
  been executed against production; do not assert its result is `VERIFIED`.
- The Neon recovery UI showed **six hours** of point-in-time history,
  **no snapshots** and **no snapshot schedule**. No backup restore test was
  performed. This does not meet the recovery-evidence gate below.
- PR CI proves clean disposable PostgreSQL behavior only. The reviewed
  migration runner is not currently deployed to production.

### Stage 2 release blockers that must all be resolved

1. **Historical provenance.** Independently compare actual production
   columns, types, nullability, primary/foreign keys, indexes, constraints and
   applied migration history with each of the six committed SQL files.
   Compare to trustworthy earlier deployment or backup records where
   available; matching table names or current SQL hashes are not proof that
   the same bytes ran historically. Stop on any unexplained difference.
2. **Source identity and Phase 7.** Verify the GitHub scheduled ingestion
   database target out of band without printing its secret. Recheck ledger
   versions just before the window. Ensure Phase 7 has not already applied
   `007` or modified the schema and that no pending SQL files exist in the
   **exact** candidate SHA.
3. **Recovery.** Establish a durable, independently verified restoration
   point and document its scope, retention, owner, and a restore drill that
   does not overwrite production. A six-hour PITR window alone is not
   adequate evidence of recoverability. Creating snapshots or changing
   backup settings requires separate authorization and plan/availability
   checks. Never assume a paid Neon feature is free.
4. **Coordination.** Obtain explicit owner approval for a maintenance window.
   Stop new scheduled ingestion launches and wait for all active runs to
   finish. Do not disable workflows or change repository settings as an
   unapproved workaround.
5. **Adoption.** From a secured, approved runner pinned to the reviewed PR
   SHA and intended database, first perform the read-only preflight. A
   legacy result is expected until adoption. Only after conditions 1–4 are
   verified, with separate owner approval, use
   `uv run python -m opendq migrate --adopt-legacy-checksums`. This is a
   **write to the production migration ledger**. Do not run it from an
   unreviewed workflow, or submit its credentials in logs/chat.
6. **Post-adoption verification.** Require the independent read-only
   preflight to return `VERIFIED`; confirm that all six applied rows have
   non-null matching checksums and there are no unexpected/pending versions.
   Verify normal `migrate` is idempotent, then separately authorize the
   merge/deploy, resume ingestion and monitor job success, source freshness,
   application health and error logs. Keep a named rollback decision-maker
   and escalation path.

### Explicit stop conditions

Stop the **Stage 2 checksum adoption and any schema-changing merge or deployment** if: the production
project or scheduled-job target cannot be verified; schema differs without
an accepted explanation; a Phase 7 or unknown migration appears; a new SQL
file is pending; the preflight reports `BLOCKED`; the backup cannot be
restored; scheduled ingestion is still running; or owner approval is absent.
Do **not** "fix" the result by deleting ledger rows, rewriting SQL history,
overwriting hashes, forcing GitHub CI, or changing production credentials.

If anything fails **after adoption**, freeze further migrations and
ingestion, capture non-secret diagnostics, and follow the approved recovery
plan. Avoid trying to reverse a checksum ledger change by deleting the
column or changing hashes without a separate database recovery assessment.

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
