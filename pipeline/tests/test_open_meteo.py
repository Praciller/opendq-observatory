import json
from pathlib import Path

import httpx
import pytest
from opendq.sources.open_meteo import OpenMeteoAdapter

FIXTURE = json.loads((Path(__file__).parent / "fixtures/open_meteo.json").read_text())


@pytest.mark.asyncio
async def test_open_meteo_fetch_and_normalize_fixture() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["timezone"] == "UTC"
        return httpx.Response(200, json=FIXTURE)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = OpenMeteoAdapter(
            client=client,
            base_url="https://api.open-meteo.test/v1/forecast",
            latitude=13.7563,
            longitude=100.5018,
        )
        payload = await adapter.fetch()
        result = adapter.normalize(payload)

    assert len(result.records) == 2
    assert result.rejected == 0
    assert result.records[0]["kind"] == "weather"
    assert result.records[0]["temperature_c"] == 28.1
    assert result.records[0]["observed_at"].tzinfo is not None


def test_open_meteo_rejects_malformed_row() -> None:
    malformed = {**FIXTURE, "hourly": {**FIXTURE["hourly"], "temperature_2m": [None, 28.3]}}

    result = OpenMeteoAdapter.normalize_payload(malformed)

    assert len(result.records) == 1
    assert result.rejected == 1
