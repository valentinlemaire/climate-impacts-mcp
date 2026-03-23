"""Discovery tools — read from cached metadata, zero API calls."""

from __future__ import annotations

from mcp.server.fastmcp import Context

from ..formatting import format_country_list, format_variable_list
from ..models import Metadata


def _get_metadata(ctx: Context) -> Metadata:
    return ctx.request_context.lifespan_context["metadata"]


async def lookup_country(
    query: str,
    group: str | None = None,
    ctx: Context = None,
) -> str:
    """Look up a country's ISO code by name, or list countries in a group.

    Args:
        query: Country name (or partial name) to search for. Use '*' to list all.
        group: Optional country group filter (e.g. 'sids', 'ldc', 'g20'). Use list_scenarios to find group IDs.
    """
    meta = _get_metadata(ctx)
    candidates = meta.countries

    if group:
        group_ids = set()
        for g in meta.country_groups:
            if group.lower() in g.id.lower() or group.lower() in g.name.lower():
                group_ids.update(g.children)
        if group_ids:
            candidates = [c for c in candidates if c.id in group_ids]
        else:
            candidates = []

    if query != "*":
        q = query.lower()
        candidates = [
            c
            for c in candidates
            if q in c.name.lower() or q in c.id.lower()
        ]

    return format_country_list(candidates, query if query != "*" else None)


async def list_climate_variables(
    group: str | None = None,
    ctx: Context = None,
) -> str:
    """List available climate variables, optionally filtered by category group.

    Args:
        group: Optional category filter (e.g. 'Climate', 'Heat', 'Agriculture').
    """
    meta = _get_metadata(ctx)
    variables = meta.vars
    if group:
        variables = [v for v in variables if group.lower() in v.group.lower()]
    return format_variable_list(variables)


async def list_scenarios(ctx: Context = None) -> str:
    """List all available emission scenarios with descriptions."""
    meta = _get_metadata(ctx)
    lines = ["| Scenario ID | Name | Description |", "|-------------|------|-------------|"]
    for s in meta.scenarios:
        desc = s.description[:120] + "..." if len(s.description) > 120 else s.description
        lines.append(f"| `{s.id}` | {s.name} | {desc} |")
    return "\n".join(lines)
