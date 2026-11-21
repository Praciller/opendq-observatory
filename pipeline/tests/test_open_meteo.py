import json
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from opendq.errors import ErrorCode, IngestionError
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


@pytest.mark.asyncio
async def test_open_meteo_retries_one_timeout_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pause = AsyncMock()
    monkeypatch.setattr("opendq.sources.open_meteo.sleep", pause)
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url)
        if len(requests) == 1:
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(200, json=FIXTURE)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = OpenMeteoAdapter(
            client=client, base_url="https://api.open-meteo.test/v1/forecast"
        )
        assert await adapter.fetch() == FIXTURE

    assert len(requests) == 2
    assert requests[0] == requests[1]
    pause.assert_awaited_once_with(1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("times_out", "expected_code", "attempts"),
    [(True, ErrorCode.SOURCE_TIMEOUT, 2), (False, ErrorCode.SOURCE_UNAVAILABLE, 1)],
)
async def test_open_meteo_failed_fetch_is_bounded(
    monkeypatch: pytest.MonkeyPatch, times_out: bool, expected_code: ErrorCode, attempts: int
) -> None:
    pause = AsyncMock()
    monkeypatch.setattr("opendq.sources.open_meteo.sleep", pause)
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if times_out:
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = OpenMeteoAdapter(
            client=client, base_url="https://api.open-meteo.test/v1/forecast"
        )
        with pytest.raises(IngestionError) as error:
            await adapter.fetch()

    assert error.value.code == expected_code
    assert calls == attempts
    assert pause.await_count == attempts - 1


def test_open_meteo_rejects_malformed_row() -> None:
    malformed = {**FIXTURE, "hourly": {**FIXTURE["hourly"], "temperature_2m": [None, 28.3]}}

    result = OpenMeteoAdapter.normalize_payload(malformed)

    assert len(result.records) == 1
    assert result.rejected == 1
