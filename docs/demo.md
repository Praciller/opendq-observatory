# Local incident demo

The Phase 6 demo is a deterministic, local-only narrative:

```text
healthy fixture
  → temporal gap and distribution shift introduced
  → quality failure and DATA_DRIFT incident
  → lineage blast radius
  → deterministic RCA
  → deterministic AI fallback
  → missing timestamp repaired and healthy distribution restored
  → incidents resolve
```

## Safe command

Create a disposable local PostgreSQL database once:

```powershell
docker compose up -d postgres
docker exec opendq-observatory-postgres-1 createdb -U opendq opendq_demo
```

Run the demo only with an explicit environment and dedicated database URL:

```powershell
$env:APP_ENV = "demo"
$env:DEMO_DATABASE_URL = "postgresql://opendq:opendq@localhost:5432/opendq_demo"
pipeline/.venv/Scripts/python.exe -m opendq demo incident
Remove-Item Env:APP_ENV, Env:DEMO_DATABASE_URL
```

The command resets only the named local demo database, emits structured evidence, never reads `DATABASE_URL` as its target, never calls public data providers, and refuses non-local PostgreSQL hosts. It is not a production chaos test.

The integration regression is `pipeline/tests/test_phase6_end_to_end.py`; the failure catalog and environment guard are covered by `test_failure_scenarios.py` and `test_demo.py`.
