"""FastMCP server entry point with lifespan management."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

import httpx
from mcp.server.fastmcp import Context, FastMCP

from .client import CIEClient
from .formatting import format_country_list, format_scenario_list, format_variable_list
from .logging import log_tool_call, setup_logging
from .tools.geodata import get_spatial_data
from .tools.metadata import list_climate_variables, list_scenarios, lookup_country
from .tools.overview import get_country_overview
from .tools.timeseries import (
    compare_scenarios,
    get_climate_projections,
    get_warming_level_snapshot,
)

INSTRUCTIONS = (
    "This server provides tools to explore climate change impacts by country, "
    "emission scenario, and time horizon. Data comes from the Climate Impact Explorer "
    "(CIE) by Climate Analytics, based on climate impact models developed by IIASA. "
    "Always cite 'Climate Impact Explorer (Climate Analytics / IIASA)' when presenting data.\n\n"
    "RECOMMENDED: For a broad overview, start with `get_country_overview` — it accepts a "
    "country name (e.g. 'Costa Rica') and returns a multi-variable climate impact summary "
    "comparing current policies vs 1.5C-compatible pathways in one call.\n\n"
    "For more detailed or specific analysis, read the MCP resources first to get valid IDs "
    "without extra tool calls:\n"
    "- climate://variables — all variable IDs (e.g. 'tasAdjust', 'prAdjust')\n"
    "- climate://scenarios — all scenario IDs (e.g. 'h_cpol', 'o_1p5c')\n"
    "- climate://countries — all country ISO codes (e.g. 'DEU', 'CRI')\n\n"
    "Then use get_climate_projections, compare_scenarios, "
    "get_warming_level_snapshot, or get_spatial_data to retrieve data. "
    "The discovery tools (lookup_country, list_climate_variables, list_scenarios) "
    "remain available as fallbacks for fuzzy search.\n\n"
    "For maps: call `get_spatial_data` — the response already includes the country's "
    "TopoJSON border in the `boundary` field. ALWAYS use this `boundary` as a clip path "
    "so grid cells are cropped to the country outline. Never fetch country borders from "
    "an external URL — the border is already in the response. "
    "NEVER filter or omit grid cells — always render ALL cells including zeros.\n\n"
    "Do NOT guess variable IDs — they are specific (e.g. 'tasAdjust' not 'tas'). "
    "If you use a wrong ID, the tool will suggest valid options."
)


WORLD_ATLAS_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json"


@asynccontextmanager
async def lifespan(server: FastMCP):
    async with httpx.AsyncClient(timeout=30.0) as http:
        client = CIEClient(http)
        metadata = await client.get_metadata()
        # Fetch world-atlas TopoJSON for country boundaries (used by get_spatial_data)
        world_atlas = None
        try:
            atlas_resp = await http.get(WORLD_ATLAS_URL)
            atlas_resp.raise_for_status()
            world_atlas = atlas_resp.json()
        except Exception:
            pass  # Boundary data will be unavailable but server still works
        yield {"client": client, "metadata": metadata, "world_atlas": world_atlas}


async def _variables_resource(ctx: Context) -> str:
    meta = ctx.request_context.lifespan_context["metadata"]
    return format_variable_list(meta.vars)


async def _scenarios_resource(ctx: Context) -> str:
    meta = ctx.request_context.lifespan_context["metadata"]
    return format_scenario_list(meta.scenarios)


async def _countries_resource(ctx: Context) -> str:
    meta = ctx.request_context.lifespan_context["metadata"]
    return format_country_list(meta.countries)


def _create_server(host: str = "127.0.0.1", port: int = 8000) -> FastMCP:
    server = FastMCP(
        "Climate Impacts",
        instructions=INSTRUCTIONS,
        lifespan=lifespan,
        host=host,
        port=port,
    )
    server.resource("climate://variables", description="All valid climate variable IDs, names, units, and groups")(_variables_resource)
    server.resource("climate://scenarios", description="All valid emission scenario IDs and descriptions")(_scenarios_resource)
    server.resource("climate://countries", description="All supported country names and ISO 3166-1 alpha-3 codes")(_countries_resource)
    server.tool()(log_tool_call(get_country_overview))
    server.tool()(log_tool_call(lookup_country))
    server.tool()(log_tool_call(list_climate_variables))
    server.tool()(log_tool_call(list_scenarios))
    server.tool()(log_tool_call(get_climate_projections))
    server.tool()(log_tool_call(compare_scenarios))
    server.tool()(log_tool_call(get_warming_level_snapshot))
    server.tool()(log_tool_call(get_spatial_data))
    return server


def main():
    setup_logging()
    port = int(os.environ.get("PORT", "0"))
    if port:
        server = _create_server(host="0.0.0.0", port=port)
        server.run(transport="streamable-http")
    else:
        server = _create_server()
        server.run()


if __name__ == "__main__":
    main()
