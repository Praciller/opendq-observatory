# Local performance baseline

Captured 2026-09-06 with `scripts/benchmark.ps1` against the disposable local Docker PostgreSQL database. This is a local engineering baseline, not a production or cross-hardware claim.

Environment:

- Windows 11 (`Windows-11-10.0.26200-SP0`)
- Python 3.14.4
- PostgreSQL 16 Alpine in Docker Compose
- Five runs per metric
- 100 weather observations per fixture
- Database reset between runs

| Operation | Median ms | Range ms |
| --- | ---: | ---: |
| Fixture ingestion | 65.98 | 61.96–68.23 |
| Quality evaluation | 33.64 | 32.48–36.56 |
| Drift evaluation and incident reconciliation | 49.32 | 48.85–59.08 |
| Incident reconciliation query | 2.41 | 2.27–2.44 |
| Deterministic RCA | 6.84 | 6.21–7.15 |

The drift timing includes the existing drift-to-incident reconciliation path. The benchmark uses fixed fixture data and never targets Neon or a public endpoint. Re-run it after meaningful changes rather than treating these numbers as an SLA.

## SQL query-plan regression review (2026-10-28)

The existing operation-level benchmark above remains unchanged. This second, **local-only**
probe covers five exact representative query shapes from the existing repositories. It
records PostgreSQL `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)`, returned rows, scan-node
row counts, selected indexes, planning time, and execution time. It does not modify any
application query text.

Environment: Windows 11 (build 26300), Python 3.13.15, PostgreSQL 16.15 (local Docker),
`max_parallel_workers_per_gather=2`. Synthetic fixtures per run: 16,000 ingestion
runs (two datasets), 16,000 observations, 8,000 resolved plus one active incident,
and 4,002 lineage nodes. Inserts are wrapped in a transaction and **rolled back**
unconditionally. Statistics are gathered with local `ANALYZE`; only local fixture
tables are involved. Query plans are captured once per query, not statistically sampled.

| Repository path / query | Before (ms) | After (ms) | SQL rows returned | Before access / scanned rows | After access / scanned rows |
| --- | ---: | ---: | ---: | --- | --- |
| RCA `latest_ingestion` | 1.888 | 0.025 | 1 | Seq Scan: 8,000 matched + 8,000 filtered | `ingestion_runs_dataset_started_idx`: 1 row |
| Quality `quality_context` observations | 2.662 | 2.611 | 8,000 | Seq Scan: 8,000 matched + 8,000 filtered | Same; full dataset retrieval makes Seq Scan reasonable |
| Drift `observations(latest=True)` | 0.049 | 0.038 | 100 | `raw_observations_dataset_time_idx`: 100 rows | Same |
| Incident `_active_for_update` | 0.035 | 0.030 | 1 | `incidents_active_dataset_rule_idx`: 1 row | Same |
| Lineage `downstream` | 1.064 | 1.032 | 831 | `lineage_edges_upstream_idx`: 831 edges (plus lineage-node scan) | Same |

**Finding and change:** The pre-existing `ingestion_runs_source_started_idx`
covers source-scoped runs, **not** RCA's dataset-scoped `ORDER BY started_at DESC LIMIT 1`.
Migration `007_ingestion_rca_lookup.sql` adds only
`ingestion_runs(dataset_id, started_at DESC)`. On the same fixture the RCA path
changed from sequential scan to index scan, with unchanged returned row count and
semantic ordering. The observed latency difference is not a guaranteed speedup,
especially at the small production-demo data volume. No additional indexes were
added for scans that were already appropriate.

### Reproduce without accessing Neon

From this repository on a machine with local PostgreSQL 16 and Python/uv:

```powershell
docker compose up -d postgres
# Create a dedicated local database ONCE, only if it does not already exist:
docker exec opendq-observatory-postgres-1 createdb -U opendq opendq_sqlperf_local
cd pipeline
uv sync --locked --extra dev
$env:DATABASE_URL = "postgresql://opendq:opendq@localhost:5432/opendq_sqlperf_local"
uv run python -m opendq migrate
$env:DATABASE_URL = ""
$env:APP_ENV = "test"
$env:SQL_PLAN_DATABASE_URL = "postgresql://opendq:opendq@localhost:5432/opendq_sqlperf_local"
uv run python scripts/sql_plan_benchmark.py > sql-plan-local.json
```

The probe refuses non-local hosts, a DB without the `opendq_sqlperf_` prefix,
a URL matching `DATABASE_URL`, or `APP_ENV` other than `test`. It uses
read-only SELECTs for the plan itself and rolls back fixture data even on failure.
No production Neon access or new paid service is required.

`pipeline/tests/test_sql_plan_regression.py` adds a deterministic query-correctness
check, migration-index definition check, index *capability* check with local planner
settings, local-DB safety checks, and plan-parser checks. The normal CI PostgreSQL
service runs these under pytest. **No wall-clock threshold is enforced in CI**.

Limitations: the fixture uses synthetic skew and one Windows host; a single
`EXPLAIN ANALYZE` measurement is sensitive to cache, planner statistics,
hardware, and concurrently running processes. Planner selection at different
table sizes is allowed to differ; a Seq Scan is not automatically a regression.
Before/after evidence applies only to this fixture; it is not a benchmark of
Neon, public traffic, or end-to-end ingestion latency. The post-migration index
must be separately reviewed before any production schema deployment.

**Release gate:** Scheduled ingestion currently uses `--no-schema-change`. Merging
this migration before the production migration is explicitly approved and applied
would make that guard reject pending SQL and could interrupt scheduled ingestion.
Keep this branch unmerged until a separately approved, coordinated migration rollout
is ready; follow [migration integrity](migration-integrity.md) and
[read-only preflight](read-only-migration-preflight.md).
