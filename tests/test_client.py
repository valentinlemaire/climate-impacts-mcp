"""Tests for the CIE API client."""

from __future__ import annotations

import httpx
import pytest

from climate_impacts_mcp.client import CIEAPIError, CIEClient


async def test_get_metadata(client, mock_api):
    meta = await client.get_metadata()
    assert len(meta.countries) == 3
    assert meta.countries[0].id == "DEU"
    assert len(meta.scenarios) == 3


async def test_get_timeseries(client, mock_api):
    ts = await client.get_timeseries(iso="DEU", var="tas", scenario="h_cpol")
    assert len(ts.year) == 6
    assert ts.reference_value is None
    assert ts.median[0] == 1.0


async def test_get_timeseries_sends_region(mock_api):
    """The region parameter must be sent — the CIE API requires it."""
    async with httpx.AsyncClient() as http:
        client = CIEClient(http)
        await client.get_timeseries(iso="DEU", var="tas", scenario="h_cpol")
    req = mock_api.calls[-1].request
    assert "region=DEU" in str(req.url)


async def test_get_timeseries_custom_region(mock_api):
    async with httpx.AsyncClient() as http:
        client = CIEClient(http)
        await client.get_timeseries(iso="DEU", var="tas", scenario="h_cpol", region="DE.BW")
    req = mock_api.calls[-1].request
    assert "region=DE.BW" in str(req.url)


async def test_get_geo_data(client, mock_api):
    geo = await client.get_geo_data(iso="DEU", var="tas", scenarios="h_cpol", warming_levels="2.0")
    assert geo.dims == ["lat", "lon"]
    assert len(geo.data) == 2
    assert geo.extent[0] == 1.0


async def test_api_error(mock_api):
    error_resp = {
        "status": {
            "type": "error",
            "message": "<html><body>Variable not found</body></html>",
        }
    }
    mock_api.get("/api/timeseries/").respond(json=error_resp)
    async with httpx.AsyncClient() as http:
        client = CIEClient(http)
        with pytest.raises(CIEAPIError, match="Variable not found"):
            await client.get_timeseries(iso="DEU", var="bad", scenario="h_cpol")
