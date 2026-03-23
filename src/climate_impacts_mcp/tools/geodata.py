"""Spatial data tool — returns full gridded data with country boundary for map rendering."""

from __future__ import annotations

from mcp.server.fastmcp import Context

from ..boundaries import ISO_ALPHA3_TO_NUMERIC, extract_country_topojson
from ..client import CIEAPIError, CIEClient
from ..formatting import format_spatial_data
from ..models import Metadata, Variable
from .validation import (
    resolve_variable,
    validate_country,
    validate_scenario,
    validate_season,
    validate_warming_level,
)


def _get_client(ctx: Context) -> CIEClient:
    return ctx.request_context.lifespan_context["client"]


def _get_metadata(ctx: Context) -> Metadata:
    return ctx.request_context.lifespan_context["metadata"]


async def get_spatial_data(
    country_iso: str,
    variable: str,
    warming_level: float,
    scenario: str = "h_cpol",
    season: str = "annual",
    ctx: Context = None,
) -> str:
    """Get spatial (gridded) climate data for a country at a specific warming level.

    Returns full per-cell grid data (lat/lon/value/agreement), statistics, and country
    boundary (TopoJSON from world-atlas) for map rendering. Output includes a JSON block
    that can be used directly for D3/SVG visualizations.

    RENDERING INSTRUCTIONS: The response includes a `boundary` field with the country's
    TopoJSON border. You MUST use it as a clip path — do NOT fetch country borders from
    any external URL. Each grid cell is a 0.5deg x 0.5deg rectangle. Clip all grid cells
    to the `boundary` outline (D3: clipPath + topojson.feature) before rendering.

    Args:
        country_iso: ISO 3166-1 alpha-3 country code. Use lookup_country to find codes.
        variable: Climate variable ID (e.g. 'tasAdjust', 'prAdjust'). Use list_climate_variables to get exact IDs — do NOT guess.
        warming_level: Global warming level in degrees C (1.5, 2.0, 2.5, or 3.0).
        scenario: Emission scenario ID. Default: 'h_cpol'. Use list_scenarios to see options.
        season: Season. Default: 'annual'.
    """
    meta = _get_metadata(ctx)

    # Validate inputs
    country_iso, err = validate_country(meta, country_iso)
    if err:
        return err
    resolved = resolve_variable(meta, variable)
    if isinstance(resolved, str):
        return resolved
    var_info: Variable = resolved
    scenario, err = validate_scenario(meta, scenario)
    if err:
        return err
    season, err = validate_season(season)
    if err:
        return err
    wl_err = validate_warming_level(warming_level)
    if wl_err:
        return wl_err

    client = _get_client(ctx)
    try:
        geo = await client.get_geo_data(
            iso=country_iso,
            var=var_info.id,
            season=season,
            scenarios=scenario,
            warming_levels=str(warming_level),
        )
    except CIEAPIError as exc:
        return f"**API error**: {exc.message}"

    # Extract country boundary from cached world-atlas
    world_atlas = ctx.request_context.lifespan_context.get("world_atlas")
    boundary = None
    bbox = None
    if world_atlas:
        numeric_id = ISO_ALPHA3_TO_NUMERIC.get(country_iso)
        if numeric_id:
            boundary = extract_country_topojson(world_atlas, numeric_id)

    # Compute bbox from grid coordinates
    lats, lons = geo.coords.lat, geo.coords.lon
    if lats and lons:
        bbox = [round(min(lons), 2), round(min(lats), 2), round(max(lons), 2), round(max(lats), 2)]

    return format_spatial_data(geo, variable=var_info, boundary=boundary, bbox=bbox)
