"""Tests for MCP tools using mocked API."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from climate_impacts_mcp.client import CIEAPIError
from climate_impacts_mcp.models import GeoDataResponse, Metadata, TimeseriesResponse
from climate_impacts_mcp.tools.metadata import list_climate_variables, list_scenarios, lookup_country
from climate_impacts_mcp.tools.overview import get_country_overview
from climate_impacts_mcp.tools.timeseries import get_climate_projections, compare_scenarios, get_warming_level_snapshot
from climate_impacts_mcp.tools.geodata import get_spatial_data
from tests.conftest import SAMPLE_GEO_DATA, SAMPLE_METADATA, SAMPLE_TIMESERIES, SAMPLE_WORLD_ATLAS


def _make_ctx(metadata: Metadata, client=None) -> MagicMock:
    ctx = MagicMock()
    lifespan_ctx = {"metadata": metadata}
    if client:
        lifespan_ctx["client"] = client
    ctx.request_context.lifespan_context = lifespan_ctx
    return ctx


async def test_lookup_country_by_name():
    ctx = _make_ctx(SAMPLE_METADATA)
    result = await lookup_country(query="germany", ctx=ctx)
    assert "DEU" in result
    assert "Germany" in result


async def test_lookup_country_by_group():
    ctx = _make_ctx(SAMPLE_METADATA)
    result = await lookup_country(query="*", group="southern_asia", ctx=ctx)
    assert "IND" in result
    assert "DEU" not in result


async def test_list_climate_variables_all():
    ctx = _make_ctx(SAMPLE_METADATA)
    result = await list_climate_variables(ctx=ctx)
    assert "`tasAdjust`" in result
    assert "`prAdjust`" in result


async def test_list_climate_variables_filtered():
    ctx = _make_ctx(SAMPLE_METADATA)
    result = await list_climate_variables(group="Climate", ctx=ctx)
    assert "`tasAdjust`" in result


async def test_list_scenarios():
    ctx = _make_ctx(SAMPLE_METADATA)
    result = await list_scenarios(ctx=ctx)
    assert "h_cpol" in result
    assert "NGFS current policies" in result
    assert "o_1p5c" in result


async def test_get_climate_projections():
    mock_client = MagicMock()
    mock_client.get_timeseries = AsyncMock(
        return_value=TimeseriesResponse(**SAMPLE_TIMESERIES)
    )
    ctx = _make_ctx(SAMPLE_METADATA, client=mock_client)
    result = await get_climate_projections(
        country_iso="DEU", variable="tasAdjust", scenario="h_cpol", ctx=ctx,
    )
    assert "Temperature change" in result
    assert "2030" in result
    mock_client.get_timeseries.assert_called_once()


async def test_get_climate_projections_invalid_variable():
    mock_client = MagicMock()
    ctx = _make_ctx(SAMPLE_METADATA, client=mock_client)
    result = await get_climate_projections(
        country_iso="DEU", variable="tas", scenario="h_cpol", ctx=ctx,
    )
    assert "Validation error" in result
    assert "tasAdjust" in result
    mock_client.get_timeseries.assert_not_called()


async def test_get_climate_projections_invalid_country():
    mock_client = MagicMock()
    ctx = _make_ctx(SAMPLE_METADATA, client=mock_client)
    result = await get_climate_projections(
        country_iso="XYZ", variable="tasAdjust", scenario="h_cpol", ctx=ctx,
    )
    assert "Validation error" in result
    mock_client.get_timeseries.assert_not_called()


async def test_get_climate_projections_case_insensitive_variable():
    mock_client = MagicMock()
    mock_client.get_timeseries = AsyncMock(
        return_value=TimeseriesResponse(**SAMPLE_TIMESERIES)
    )
    ctx = _make_ctx(SAMPLE_METADATA, client=mock_client)
    result = await get_climate_projections(
        country_iso="DEU", variable="tasadjust", scenario="h_cpol", ctx=ctx,
    )
    assert "Temperature change" in result
    # Verify the API was called with the canonical ID
    call_kwargs = mock_client.get_timeseries.call_args
    assert call_kwargs.kwargs.get("var") == "tasAdjust" or call_kwargs[1].get("var") == "tasAdjust"


async def test_compare_scenarios_invalid_variable():
    mock_client = MagicMock()
    ctx = _make_ctx(SAMPLE_METADATA, client=mock_client)
    result = await compare_scenarios(
        country_iso="DEU", variable="tas", scenarios=["h_cpol"], ctx=ctx,
    )
    assert "Validation error" in result
    mock_client.get_timeseries.assert_not_called()


async def test_get_warming_level_snapshot_invalid_variable():
    mock_client = MagicMock()
    ctx = _make_ctx(SAMPLE_METADATA, client=mock_client)
    result = await get_warming_level_snapshot(
        country_iso="DEU", variable="tas", ctx=ctx,
    )
    assert "Validation error" in result
    mock_client.get_timeseries.assert_not_called()


async def test_get_spatial_data_invalid_warming_level():
    mock_client = MagicMock()
    ctx = _make_ctx(SAMPLE_METADATA, client=mock_client)
    result = await get_spatial_data(
        country_iso="DEU", variable="tasAdjust", warming_level=5.0, ctx=ctx,
    )
    assert "Validation error" in result
    mock_client.get_geo_data.assert_not_called()


async def test_get_spatial_data_invalid_variable():
    mock_client = MagicMock()
    ctx = _make_ctx(SAMPLE_METADATA, client=mock_client)
    result = await get_spatial_data(
        country_iso="DEU", variable="tas", warming_level=2.0, ctx=ctx,
    )
    assert "Validation error" in result
    mock_client.get_geo_data.assert_not_called()


async def test_get_spatial_data_happy_path():
    mock_client = MagicMock()
    mock_client.get_geo_data = AsyncMock(
        return_value=GeoDataResponse(**SAMPLE_GEO_DATA)
    )
    ctx = _make_ctx(SAMPLE_METADATA, client=mock_client)
    ctx.request_context.lifespan_context["world_atlas"] = SAMPLE_WORLD_ATLAS
    result = await get_spatial_data(
        country_iso="DEU", variable="tasAdjust", warming_level=2.0, ctx=ctx,
    )
    assert "```json" in result
    assert "Temperature change" in result
    assert '"boundary"' in result
    mock_client.get_geo_data.assert_called_once()


async def test_get_spatial_data_no_atlas():
    mock_client = MagicMock()
    mock_client.get_geo_data = AsyncMock(
        return_value=GeoDataResponse(**SAMPLE_GEO_DATA)
    )
    ctx = _make_ctx(SAMPLE_METADATA, client=mock_client)
    # No world_atlas in context — boundary should be null
    result = await get_spatial_data(
        country_iso="DEU", variable="tasAdjust", warming_level=2.0, ctx=ctx,
    )
    assert "```json" in result
    assert '"boundary":null' in result


# --- get_country_overview ---


async def test_get_country_overview_by_name():
    mock_client = MagicMock()
    mock_client.get_timeseries = AsyncMock(
        return_value=TimeseriesResponse(**SAMPLE_TIMESERIES)
    )
    ctx = _make_ctx(SAMPLE_METADATA, client=mock_client)
    result = await get_country_overview(country="Germany", ctx=ctx)
    assert "Germany (DEU)" in result
    assert "Temperature change" in result
    assert "Precipitation change" in result


async def test_get_country_overview_by_iso():
    mock_client = MagicMock()
    mock_client.get_timeseries = AsyncMock(
        return_value=TimeseriesResponse(**SAMPLE_TIMESERIES)
    )
    ctx = _make_ctx(SAMPLE_METADATA, client=mock_client)
    result = await get_country_overview(country="DEU", ctx=ctx)
    assert "Germany (DEU)" in result


async def test_get_country_overview_invalid_country():
    mock_client = MagicMock()
    ctx = _make_ctx(SAMPLE_METADATA, client=mock_client)
    result = await get_country_overview(country="Zzzzland", ctx=ctx)
    assert "not found" in result
    mock_client.get_timeseries.assert_not_called()


async def test_get_country_overview_partial_api_failures():
    """Some variables fail, others succeed — should still return data."""
    call_count = 0

    async def mock_timeseries(**kwargs):
        nonlocal call_count
        call_count += 1
        if kwargs.get("var") == "tasAdjust":
            return TimeseriesResponse(**SAMPLE_TIMESERIES)
        raise CIEAPIError("No data")

    mock_client = MagicMock()
    mock_client.get_timeseries = mock_timeseries
    ctx = _make_ctx(SAMPLE_METADATA, client=mock_client)
    result = await get_country_overview(country="DEU", ctx=ctx)
    assert "Temperature change" in result
    # prAdjust failed, so it shouldn't appear (or it might appear with no data)
    assert call_count > 0
