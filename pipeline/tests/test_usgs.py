import json
from pathlib import Path

import httpx
import pytest
from opendq.sources.usgs import USGSAdapter

FIXTURE = json.loads((Path(__file__).parent / "fixtures/usgs_earthquakes.json").read_text())


@pytest.mark.asyncio
async def test_usgs_fetch_and_normalize_fixture() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("all_day.geojson")
        return httpx.Response(200, json=FIXTURE)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = USGSAdapter(
            client=client,
            base_url="https://earthquake.usgs.test/all_day.geojson",
        )
        payload = await adapter.fetch()
        result = adapter.normalize(payload)

    assert len(result.records) == 2
    assert result.rejected == 0
    assert result.records[0]["kind"] == "earthquake"
    assert result.records[0]["event_id"] == "fixture-usgs-1"
    assert result.records[0]["depth_km"] == 12.3


def test_usgs_rejects_feature_without_event_id() -> None:
    malformed = {**FIXTURE, "features": [{**FIXTURE["features"][0], "id": None}]}

    result = USGSAdapter.normalize_payload(malformed)

    assert result.records == []
    assert result.rejected == 1
