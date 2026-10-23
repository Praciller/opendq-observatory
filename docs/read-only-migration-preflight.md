# Read-only migration preflight

This command inspects only the existing `public.schema_migrations` ledger
against SQL files in `db/migrations`. It **never** applies migrations,
backfills checksums, seeds tables or ingests data.

```sh
cd pipeline
uv sync --locked
# Point DATABASE_URL to the explicitly verified target, without printing it.
uv run python scripts/migration_preflight.py
```

The command starts a PostgreSQL transaction with `SET TRANSACTION READ ONLY`
and uses only `SELECT`. Output contains migration *filenames* and state,
not any database credentials or application data. Errors have redacted output.

States:
- `VERIFIED` — checksummed ledger matches reviewed repository SQL.
- `LEGACY_REVIEW_REQUIRED` — existing ledger lacks checksums. Historical
  SQL cannot be proven equivalent to the current files, even if the listed
  versions agree. Independent schema review is mandatory.
- `PENDING_REVIEW` — additional migration SQL is pending on a checksummed
  ledger; do not apply it without release approval.
- `BLOCKED` — missing ledger, missing applied files, unexpected versions
  (including Phase 7 `007` unknown to the checkout), or bad checksum.

Exit code is **0 only for VERIFIED**; all other states are nonzero by design.
Do not turn a failed preflight into a successful CI release gate. Running this
command is not approval to modify production; backups, database access,
Phase 7 reconciliation and an approved migration window remain separate gates.

This standalone command has **no GitHub Actions workflow, no secret usage,
no automatic scheduler**, and does not change the existing `opendq migrate`
behavior. The separate PR #6 changes the runner and stays Draft.
