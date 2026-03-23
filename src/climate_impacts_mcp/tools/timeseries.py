"""Projection tools — call CIE API for timeseries data."""

from __future__ import annotations

import asyncio

from mcp.server.fastmcp import Context

from ..client import CIEAPIError, CIEClient
from ..formatting import format_comparison_table, format_timeseries, format_warming_level_table
from ..models import Metadata, Variable
from .validation import (
    resolve_variable,
    validate_country,
    validate_scenario,
    validate_season,
    validate_spatial_weighting,
)


def _get_client(ctx: Context) -> CIEClient:
    return ctx.request_context.lifespan_context["client"]


def _get_metadata(ctx: Context) -> Metadata:
    return ctx.request_context.lifespan_context["metadata"]


def _scenario_display_name(meta: Metadata, scenario_id: str) -> str:
    for s in meta.scenarios:
        if s.id == scenario_id:
            return s.name
    return scenario_id


async def get_climate_projections(
    country_iso: str,
    variable: str,
    scenario: str,
    season: str = "annual",
    spatial_weighting: str = "area",
    ctx: Context = None,
) -> str:
    """Get climate change projections for a country, variable, and scenario.

    Returns a timeseries from 2015 to 2100 with median, uncertainty range, and warming levels.

    Args:
        country_iso: ISO 3166-1 alpha-3 country code (e.g. 'DEU', 'USA'). Use lookup_country to find codes.
        variable: Climate variable ID (e.g. 'tasAdjust', 'prAdjust'). Use list_climate_variables to get exact IDs — do NOT guess.
        scenario: Emission scenario ID (e.g. 'h_cpol'). Use list_scenarios to see options.
        season: Season — one of 'annual', 'MAM', 'JJA', 'SON', 'DJF'. Default: 'annual'.
        spatial_weighting: Spatial aggregation — one of 'area', 'pop', 'gdp', 'harvarea', 'wheat', 'maize', 'soybean', 'rice', 'sum'. Default: 'area'.
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
    sw_err = validate_spatial_weighting(meta, var_info, spatial_weighting)
    if sw_err:
        return sw_err

    client = _get_client(ctx)
    try:
        ts = await client.get_timeseries(
            iso=country_iso,
            var=var_info.id,
            scenario=scenario,
            season=season,
            aggregation_spatial=spatial_weighting,
        )
    except CIEAPIError as exc:
        return f"**API error**: {exc.message}"

    scenario_label = _scenario_display_name(meta, scenario)
    return format_timeseries(ts, variable=var_info, scenario_name=scenario_label)


async def compare_scenarios(
    country_iso: str,
    variable: str,
    scenarios: list[str],
    season: str = "annual",
    spatial_weighting: str = "area",
    time_horizons: list[int] | None = None,
    ctx: Context = None,
) -> str:
    """Compare climate projections across multiple scenarios side by side.

    Fetches data for each scenario in parallel and displays a comparison table at key time horizons.

    Args:
        country_iso: ISO 3166-1 alpha-3 country code. Use lookup_country to find codes.
        variable: Climate variable ID (e.g. 'tasAdjust', 'prAdjust'). Use list_climate_variables to get exact IDs — do NOT guess.
        scenarios: List of scenario IDs to compare (e.g. ['o_1p5c', 'h_cpol', 'h_ndc']). Use list_scenarios to see options.
        season: Season — one of 'annual', 'MAM', 'JJA', 'SON', 'DJF'. Default: 'annual'.
        spatial_weighting: Spatial aggregation method. Default: 'area'.
        time_horizons: Years to show in comparison. Default: [2030, 2050, 2100].
    """
    if time_horizons is None:
        time_horizons = [2030, 2050, 2100]

    meta = _get_metadata(ctx)

    # Validate inputs
    country_iso, err = validate_country(meta, country_iso)
    if err:
        return err
    resolved = resolve_variable(meta, variable)
    if isinstance(resolved, str):
        return resolved
    var_info: Variable = resolved
    season, err = validate_season(season)
    if err:
        return err
    sw_err = validate_spatial_weighting(meta, var_info, spatial_weighting)
    if sw_err:
        return sw_err

    validated_scenarios = []
    for sc in scenarios:
        sc_id, err = validate_scenario(meta, sc)
        if err:
            return err
        validated_scenarios.append(sc_id)

    client = _get_client(ctx)

    async def fetch(sc: str):
        return sc, await client.get_timeseries(
            iso=country_iso, var=var_info.id, scenario=sc,
            season=season, aggregation_spatial=spatial_weighting,
        )

    try:
        results_list = await asyncio.gather(*[fetch(sc) for sc in validated_scenarios])
    except CIEAPIError as exc:
        return f"**API error**: {exc.message}"

    results = {sc: ts for sc, ts in results_list}
    return format_comparison_table(results, time_horizons, variable=var_info)


async def get_warming_level_snapshot(
    country_iso: str,
    variable: str,
    scenario: str = "h_cpol",
    season: str = "annual",
    spatial_weighting: str = "area",
    ctx: Context = None,
) -> str:
    """View climate impacts indexed by global warming level (1.5/2.0/2.5/3.0C).

    Shows what impact values correspond to each warming level rather than by year.

    Args:
        country_iso: ISO 3166-1 alpha-3 country code. Use lookup_country to find codes.
        variable: Climate variable ID (e.g. 'tasAdjust', 'prAdjust'). Use list_climate_variables to get exact IDs — do NOT guess.
        scenario: Emission scenario ID. Default: 'h_cpol' (current policies). Use list_scenarios to see options.
        season: Season. Default: 'annual'.
        spatial_weighting: Spatial aggregation method. Default: 'area'.
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
    sw_err = validate_spatial_weighting(meta, var_info, spatial_weighting)
    if sw_err:
        return sw_err

    client = _get_client(ctx)
    try:
        ts = await client.get_timeseries(
            iso=country_iso, var=var_info.id, scenario=scenario,
            season=season, aggregation_spatial=spatial_weighting,
        )
    except CIEAPIError as exc:
        return f"**API error**: {exc.message}"

    return format_warming_level_table(ts, variable=var_info)
