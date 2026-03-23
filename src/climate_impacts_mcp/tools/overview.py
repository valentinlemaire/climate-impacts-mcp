"""High-level overview tool — single-call climate impact summary for a country."""

from __future__ import annotations

import asyncio

from mcp.server.fastmcp import Context

from ..client import CIEAPIError, CIEClient
from ..formatting import format_country_overview
from ..models import Metadata, TimeseriesResponse, Variable
from .validation import (
    resolve_country_name,
    validate_season,
)

# One representative variable per impact category, ordered by likely availability.
KEY_VARIABLES: list[str] = [
    "tasAdjust",
    "prAdjust",
    "dryDaysAdjust",
    "heatwave_days_tasmax_q98",
    "rx1day_precip_Adjust",
    "burntFractionAll",
    "dischargeAdjust",
    "yield_mai_noirr",
    "labourprod_impact_high",
]

SCENARIOS = ["h_cpol", "o_1p5c"]


def _get_client(ctx: Context) -> CIEClient:
    return ctx.request_context.lifespan_context["client"]


def _get_metadata(ctx: Context) -> Metadata:
    return ctx.request_context.lifespan_context["metadata"]


async def get_country_overview(
    country: str,
    season: str = "annual",
    ctx: Context = None,
) -> str:
    """Get a comprehensive climate change impact overview for a country.

    Returns projections for key climate variables across multiple impact categories,
    comparing current policies (business as usual) vs 1.5C-compatible pathways.
    Accepts country names (e.g. 'Costa Rica') or ISO codes (e.g. 'CRI').

    Args:
        country: Country name (e.g. 'Costa Rica', 'Germany') or ISO code (e.g. 'CRI', 'DEU').
        season: Season — one of 'annual', 'MAM', 'JJA', 'SON', 'DJF'. Default: 'annual'.
    """
    meta = _get_metadata(ctx)

    # Resolve country
    country_obj, err = resolve_country_name(meta, country)
    if err:
        return err

    season, err = validate_season(season)
    if err:
        return err

    # Filter KEY_VARIABLES against actual metadata
    var_lookup: dict[str, Variable] = {v.id: v for v in meta.vars}
    valid_vars = [vid for vid in KEY_VARIABLES if vid in var_lookup]

    if not valid_vars:
        return "**Error**: No key climate variables found in metadata."

    # Build scenario display names
    scenario_names: dict[str, str] = {}
    for s in meta.scenarios:
        if s.id in SCENARIOS:
            scenario_names[s.id] = s.name
    for s_id in SCENARIOS:
        if s_id not in scenario_names:
            scenario_names[s_id] = s_id

    client = _get_client(ctx)

    # Fetch all variables x scenarios in parallel
    async def fetch_one(var_id: str, scenario: str) -> tuple[str, str, TimeseriesResponse | None]:
        try:
            ts = await client.get_timeseries(
                iso=country_obj.id,
                var=var_id,
                scenario=scenario,
                season=season,
                aggregation_spatial="area",
            )
            return var_id, scenario, ts
        except (CIEAPIError, Exception):
            return var_id, scenario, None

    tasks = [fetch_one(vid, sc) for vid in valid_vars for sc in SCENARIOS]
    results = await asyncio.gather(*tasks)

    # Organize results: {var_id: {scenario: ts}}
    by_var: dict[str, dict[str, TimeseriesResponse | None]] = {}
    for var_id, scenario, ts in results:
        by_var.setdefault(var_id, {})[scenario] = ts

    # Build variable_results, skipping variables where ALL scenarios failed
    variable_results: list[tuple[Variable, dict[str, TimeseriesResponse | None]]] = []
    for var_id in valid_vars:
        scenario_data = by_var.get(var_id, {})
        if any(ts is not None for ts in scenario_data.values()):
            variable_results.append((var_lookup[var_id], scenario_data))

    return format_country_overview(
        country_name=country_obj.name,
        country_iso=country_obj.id,
        scenario_names=scenario_names,
        variable_results=variable_results,
        season=season,
    )
