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
