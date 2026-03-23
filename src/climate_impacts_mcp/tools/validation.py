"""Shared input validation for MCP tools — validates against cached metadata."""

from __future__ import annotations

import difflib

from ..models import Country, Metadata, Variable

VALID_SEASONS = {"annual", "MAM", "JJA", "SON", "DJF"}
VALID_WARMING_LEVELS = {1.5, 2.0, 2.5, 3.0}


def _suggest(value: str, candidates: list[str], n: int = 3) -> list[str]:
    """Fuzzy-match *value* against *candidates* (case-insensitive)."""
    lower_map = {c.lower(): c for c in candidates}
    matches = difflib.get_close_matches(value.lower(), lower_map.keys(), n=n, cutoff=0.4)
    return [lower_map[m] for m in matches]


def resolve_variable(meta: Metadata, var_id: str) -> Variable | str:
    """Return the Variable if found, or an error string with suggestions."""
    # Exact match
    for v in meta.vars:
        if v.id == var_id:
            return v
    # Case-insensitive match
    for v in meta.vars:
        if v.id.lower() == var_id.lower():
            return v
    # No match — suggest
    suggestions = _suggest(var_id, [v.id for v in meta.vars])
    msg = f"**Validation error**: Variable `{var_id}` not found."
    if suggestions:
        formatted = ", ".join(f"`{s}`" for s in suggestions)
        msg += f"\nDid you mean: {formatted}?"
    msg += "\nUse the `list_climate_variables` tool to see all available variables."
    return msg


def validate_country(meta: Metadata, iso: str) -> tuple[str | None, str | None]:
    """Return (canonical_iso, None) on success or (None, error_string) on failure."""
    for c in meta.countries:
        if c.id == iso:
            return c.id, None
    # Case-insensitive
    for c in meta.countries:
        if c.id.lower() == iso.lower():
            return c.id, None
    suggestions = _suggest(iso, [c.id for c in meta.countries])
    msg = f"**Validation error**: Country code `{iso}` not found."
    if suggestions:
        formatted = ", ".join(f"`{s}`" for s in suggestions)
        msg += f"\nDid you mean: {formatted}?"
    msg += "\nUse the `lookup_country` tool to find ISO codes."
    return None, msg


def validate_scenario(meta: Metadata, scenario_id: str) -> tuple[str | None, str | None]:
    """Return (canonical_id, None) on success or (None, error_string) on failure."""
    for s in meta.scenarios:
        if s.id == scenario_id:
            return s.id, None
    # Case-insensitive
    for s in meta.scenarios:
        if s.id.lower() == scenario_id.lower():
            return s.id, None
    suggestions = _suggest(scenario_id, [s.id for s in meta.scenarios])
    msg = f"**Validation error**: Scenario `{scenario_id}` not found."
    if suggestions:
        formatted = ", ".join(f"`{s}`" for s in suggestions)
        msg += f"\nDid you mean: {formatted}?"
    msg += "\nUse the `list_scenarios` tool to see available scenarios."
    return None, msg


def validate_season(season: str) -> tuple[str | None, str | None]:
    """Return (canonical_season, None) on success or (None, error_string) on failure."""
    if season in VALID_SEASONS:
        return season, None
    # Case-insensitive
    for s in VALID_SEASONS:
        if s.lower() == season.lower():
            return s, None
    valid = ", ".join(f"`{s}`" for s in sorted(VALID_SEASONS))
    return None, f"**Validation error**: Season `{season}` is not valid.\nValid seasons: {valid}."


def validate_spatial_weighting(
    meta: Metadata, variable: Variable, weighting: str,
) -> str | None:
    """Return an error string if *weighting* is incompatible, else None."""
    # Check weighting exists in global list
    valid_ids = [sw.id for sw in meta.spatial_weightings]
    if weighting not in valid_ids:
        suggestions = _suggest(weighting, valid_ids)
        msg = f"**Validation error**: Spatial weighting `{weighting}` not found."
        if suggestions:
            formatted = ", ".join(f"`{s}`" for s in suggestions)
            msg += f"\nDid you mean: {formatted}?"
        return msg
    # Check per-variable allowlist (empty means all are allowed)
    if variable.spatial_weighting and weighting not in variable.spatial_weighting:
        allowed = ", ".join(f"`{w}`" for w in variable.spatial_weighting)
        return (
            f"**Validation error**: Spatial weighting `{weighting}` is not compatible "
            f"with variable `{variable.id}`.\nAllowed weightings for this variable: {allowed}."
        )
    return None


def resolve_country_name(meta: Metadata, query: str) -> tuple[Country | None, str | None]:
    """Resolve a country name or ISO code to a Country object.

    Tries: exact ISO -> exact name -> substring name -> fuzzy name match.
    Returns (Country, None) on success, or (None, error_message) on failure.
    """
    # 1. Exact ISO match
    for c in meta.countries:
        if c.id.upper() == query.upper():
            return c, None

    # 2. Exact name match (case-insensitive)
    q_lower = query.lower()
    for c in meta.countries:
        if c.name.lower() == q_lower:
            return c, None

    # 3. Substring match on name
    matches = [c for c in meta.countries if q_lower in c.name.lower()]
    if len(matches) == 1:
        return matches[0], None
    if len(matches) > 1:
        options = ", ".join(f"{c.name} (`{c.id}`)" for c in matches[:5])
        return None, f"**Validation error**: Multiple countries match '{query}': {options}. Please be more specific."

    # 4. Fuzzy match on names
    name_map = {c.name.lower(): c for c in meta.countries}
    close = difflib.get_close_matches(q_lower, name_map.keys(), n=3, cutoff=0.6)
    if len(close) == 1:
        return name_map[close[0]], None
    if close:
        suggestions = ", ".join(f"{name_map[m].name} (`{name_map[m].id}`)" for m in close)
        return None, f"**Validation error**: Country '{query}' not found. Did you mean: {suggestions}?"

    return None, f"**Validation error**: Country '{query}' not found. Use `lookup_country` to search for countries."


def validate_warming_level(wl: float) -> str | None:
    """Return an error string if *wl* is not a valid warming level, else None."""
    if wl in VALID_WARMING_LEVELS:
        return None
    valid = ", ".join(f"`{v}`" for v in sorted(VALID_WARMING_LEVELS))
    return f"**Validation error**: Warming level `{wl}` is not valid.\nValid levels: {valid}."
