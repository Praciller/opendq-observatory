import json
from pathlib import Path
from typing import Any

import pytest
from opendq.errors import ErrorCode, IngestionError
from opendq.ingestion.results import IngestionResult
from opendq.ingestion.runner import run_all, run_source
from opendq.sources.open_meteo import OpenMeteoAdapter
from opendq.sources.usgs import USGSAdapter

FIXTURES = Path(__file__).parent / "fixtures"


class FixtureAdapter:
    source_slug = "fixture-source"
    dataset_slug = "fixture-dataset"
    source_name = "Fixture source"
    dataset_name = "Fixture dataset"
    description = "Fixture adapter"
    base_url = "https://example.test"

    def __init__(self, payload: dict[str, Any], *, fail: IngestionError | None = None) -> None:
        self.payload = payload
        self.fail = fail

    async def fetch(self) -> dict[str, Any]:
        if self.fail:
            raise self.fail
        return self.payload

    def normalize(self, payload: dict[str, Any]):
        return OpenMeteoAdapter.normalize_payload(payload)


@pytest.mark.asyncio
async def test_identical_weather_ingestion_becomes_no_change(repository) -> None:
    adapter = FixtureAdapter(json.loads((FIXTURES / "open_meteo.json").read_text()))

    first = await run_source(repository, adapter)
    second = await run_source(repository, adapter)

    assert first.status == "SUCCESS"
    assert first.records_written == 2
    assert second.status == "NO_CHANGE"
    assert second.records_written == 0


@pytest.mark.asyncio
async def test_timeout_finishes_run_as_failed(repository) -> None:
    adapter = FixtureAdapter({}, fail=IngestionError(ErrorCode.SOURCE_TIMEOUT, "request timed out"))

    result = await run_source(repository, adapter)

    assert result.status == "FAILED"
    assert result.error_code == ErrorCode.SOURCE_TIMEOUT
    with repository.connection.cursor() as cursor:
        cursor.execute(
            "SELECT status, finished_at FROM ingestion_runs WHERE run_id = %s", (result.run_id,)
        )
        row = cursor.fetchone()
    assert row is not None
    assert row[0] == "FAILED"
    assert row[1] is not None


@pytest.mark.asyncio
async def test_rejected_record_produces_partial_run(repository) -> None:
    payload = json.loads((FIXTURES / "open_meteo.json").read_text())
    payload["hourly"]["temperature_2m"][0] = None
    adapter = FixtureAdapter(payload)

    result = await run_source(repository, adapter)

    assert result.status == "PARTIAL"
    assert result.records_written == 1
    assert result.records_rejected == 1


@pytest.mark.asyncio
async def test_database_write_failure_is_recorded_as_failed(repository, monkeypatch) -> None:
    adapter = FixtureAdapter(json.loads((FIXTURES / "open_meteo.json").read_text()))

    def fail(*args, **kwargs):
        raise RuntimeError("database write unavailable")

    monkeypatch.setattr(repository, "upsert_observations", fail)
    result = await run_source(repository, adapter)

    assert result.status == "FAILED"
    assert result.error_code == ErrorCode.DATABASE_ERROR


@pytest.mark.asyncio
async def test_run_all_attempts_both_sources_after_one_failure(repository) -> None:
    good = FixtureAdapter(json.loads((FIXTURES / "open_meteo.json").read_text()))
    good.source_slug = "good-source"
    good.dataset_slug = "good-dataset"
    bad = FixtureAdapter({}, fail=IngestionError(ErrorCode.SOURCE_UNAVAILABLE, "offline"))
    bad.source_slug = "bad-source"
    bad.dataset_slug = "bad-dataset"

    results = await run_all(repository, [bad, good])

    assert [result.status for result in results] == ["FAILED", "SUCCESS"]
    assert isinstance(results[0], IngestionResult)


@pytest.mark.asyncio
async def test_usgs_ingestion_uses_event_identity(repository) -> None:
    adapter = FixtureAdapter(json.loads((FIXTURES / "usgs_earthquakes.json").read_text()))
    adapter.source_slug = USGSAdapter.source_slug
    adapter.dataset_slug = USGSAdapter.dataset_slug
    adapter.source_name = USGSAdapter.source_name
    adapter.dataset_name = USGSAdapter.dataset_name
    adapter.description = USGSAdapter.description
    adapter.normalize = USGSAdapter.normalize_payload

    first = await run_source(repository, adapter)
    second = await run_source(repository, adapter)

    assert first.records_written == 2
    assert second.status == "NO_CHANGE"
