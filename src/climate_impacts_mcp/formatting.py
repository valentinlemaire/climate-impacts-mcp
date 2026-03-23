"""Response formatting helpers that produce LLM-friendly markdown."""

from __future__ import annotations

import json

from .models import (
    Country,
    GeoDataResponse,
    TimeseriesResponse,
    Variable,
)

DATA_SOURCE = (
    "Source: [Climate Impact Explorer](https://climate-impact-explorer.climateanalytics.org)"
    " (Climate Analytics / IIASA)"
)


def format_timeseries(
    ts: TimeseriesResponse,
    variable: Variable | None = None,
    scenario_name: str | None = None,
) -> str:
    lines: list[str] = []
    if variable:
        lines.append(f"**{variable.name}** ({variable.unit})")
        if variable.description:
            lines.append(f"_{variable.description}_")
        if variable.reference_period:
            lines.append(f"Reference period: {variable.reference_period}")
    if scenario_name:
        lines.append(f"Scenario: **{scenario_name}**")
    if ts.reference_value is not None:
        lines.append(f"Reference value: {ts.reference_value}")
    lines.append("")
    lines.append("| Year | Median | Range (low-high) | Warming Level |")
    lines.append("|------|--------|-------------------|---------------|")
    for i, year in enumerate(ts.year):
        median = _fmt(ts.median[i])
        low = _fmt(ts.lower[i])
        high = _fmt(ts.upper[i])
        wl = _fmt_wl(ts.warming_levels[i]) if i < len(ts.warming_levels) else "-"
        lines.append(f"| {int(year)} | {median} | {low} - {high} | {wl} |")
    lines.append("")
    lines.append(f"_{DATA_SOURCE}_")
    return "\n".join(lines)


def format_comparison_table(
    results: dict[str, TimeseriesResponse],
    time_horizons: list[int],
    variable: Variable | None = None,
) -> str:
    lines: list[str] = []
    if variable:
        lines.append(f"**{variable.name}** ({variable.unit})")
        lines.append("")
    scenarios = list(results.keys())
    header = "| Year | " + " | ".join(scenarios) + " |"
    sep = "|------|" + "|".join(["--------"] * len(scenarios)) + "|"
    lines.append(header)
    lines.append(sep)
    for year in time_horizons:
        row = f"| {year} |"
        for sc in scenarios:
            ts = results[sc]
            val = _value_at_year(ts, year)
            row += f" {val} |"
        lines.append(row)
    lines.append("")
    lines.append(f"_{DATA_SOURCE}_")
    return "\n".join(lines)


def format_warming_level_table(
    ts: TimeseriesResponse,
    variable: Variable | None = None,
) -> str:
    lines: list[str] = []
    if variable:
        lines.append(f"**{variable.name}** ({variable.unit})")
        lines.append("")
    wl_data: dict[float, dict] = {}
    for i, wl in enumerate(ts.warming_levels):
        if wl is not None and i < len(ts.median):
            wl_data[wl] = {
                "median": ts.median[i],
                "lower": ts.lower[i],
                "upper": ts.upper[i],
                "year": int(ts.year[i]),
            }
    lines.append("| Warming Level | Year Reached | Median | Range (low-high) |")
    lines.append("|---------------|--------------|--------|-------------------|")
    for wl in sorted(wl_data.keys()):
        d = wl_data[wl]
        lines.append(
            f"| {wl}C | {d['year']} | {_fmt(d['median'])} | {_fmt(d['lower'])} - {_fmt(d['upper'])} |"
        )
    if not wl_data:
        lines.append("| - | - | No warming level data available | - |")
    lines.append("")
    lines.append(f"_{DATA_SOURCE}_")
    return "\n".join(lines)


def format_spatial_summary(geo: GeoDataResponse, variable: Variable | None = None) -> str:
    lines: list[str] = []
    if variable:
        lines.append(f"**{variable.name}** ({variable.unit})")
        lines.append("")
    flat = [v for row in geo.data for v in row if v is not None]
    if not flat:
        return "No spatial data available."
    flat.sort()
    n = len(flat)
    mean_val = sum(flat) / n
    median_val = flat[n // 2]
    lines.append(f"- **Grid cells**: {n}")
    lines.append(f"- **Min**: {flat[0]:.4g}")
    lines.append(f"- **Max**: {flat[-1]:.4g}")
    lines.append(f"- **Mean**: {mean_val:.4g}")
    lines.append(f"- **Median**: {median_val:.4g}")
    if geo.agreement is not None:
        agree_flat = [v for row in geo.agreement for v in row if v is not None]
        if agree_flat:
            avg_agree = sum(agree_flat) / len(agree_flat)
            lines.append(f"- **Model agreement**: {avg_agree:.0%}")
    extent = geo.extent
    if len(extent) >= 2:
        lines.append(f"- **Data range**: [{extent[0]:.4g}, {extent[1]:.4g}]")
    return "\n".join(lines)


def format_spatial_data(
    geo: GeoDataResponse,
    variable: Variable | None = None,
    boundary: dict | None = None,
    bbox: list[float] | None = None,
) -> str:
    lines: list[str] = []
    if variable:
        lines.append(f"**{variable.name}** ({variable.unit})")
    flat = [v for row in geo.data for v in row if v is not None]
    if not flat:
        return "No spatial data available."
    flat_sorted = sorted(flat)
    n = len(flat_sorted)
    mean_val = sum(flat_sorted) / n
    median_val = flat_sorted[n // 2]
    min_val = flat_sorted[0]
    max_val = flat_sorted[-1]

    agree_avg = None
    if geo.agreement is not None:
        agree_flat = [v for row in geo.agreement for v in row if v is not None]
        if agree_flat:
            agree_avg = sum(agree_flat) / len(agree_flat)

    stats_parts = [f"Grid cells: {n}", f"Min: {min_val:.4g}", f"Max: {max_val:.4g}", f"Mean: {mean_val:.4g}"]
    if agree_avg is not None:
        stats_parts.append(f"Agreement: {agree_avg:.0%}")
    lines.append("- " + " | ".join(stats_parts))
    lines.append("")

    # Build sparse grid: [lat, lon, value, agreement] per non-null cell
    grid = []
    lats = geo.coords.lat
    lons = geo.coords.lon
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            val = geo.data[i][j] if i < len(geo.data) and j < len(geo.data[i]) else None
            if val is None:
                continue
            agree = None
            if geo.agreement is not None and i < len(geo.agreement) and j < len(geo.agreement[i]):
                agree = geo.agreement[i][j]
            grid.append([round(lat, 2), round(lon, 2), round(val, 4), agree])

    payload: dict = {
        "stats": {"count": n, "min": round(min_val, 4), "max": round(max_val, 4), "mean": round(mean_val, 4), "median": round(median_val, 4)},
        "extent": [round(e, 4) for e in geo.extent] if len(geo.extent) >= 2 else geo.extent,
        "grid": grid,
        "bbox": bbox,
        "boundary": boundary,
    }
    if variable:
        payload["variable"] = {"id": variable.id, "name": variable.name, "unit": variable.unit}
    if geo.warming_levels:
        payload["warming_level"] = geo.warming_levels

    lines.append("```json")
    lines.append(json.dumps(payload, separators=(",", ":")))
    lines.append("```")
    lines.append("")
    lines.append(f"_{DATA_SOURCE}_")
    lines.append("")
    lines.append(
        "**Rendering**: Each grid cell is a 0.5° × 0.5° rectangle. "
        "Use the `boundary` TopoJSON as a clip path so grid cells are clipped "
        "to the country outline. Draw the boundary stroke on top for a clean border."
    )
    return "\n".join(lines)


def format_country_overview(
    country_name: str,
    country_iso: str,
    scenario_names: dict[str, str],
    variable_results: list[tuple[Variable, dict[str, TimeseriesResponse | None]]],
    season: str = "annual",
) -> str:
    lines: list[str] = []
    scenario_ids = list(scenario_names.keys())
    scenario_labels = [scenario_names[s] for s in scenario_ids]

    lines.append(f"# Climate Change Impacts: {country_name} ({country_iso})")
    lines.append("")
    lines.append(f"Comparing **{scenario_labels[0]}** vs **{scenario_labels[1]}** | Season: {season}")
    lines.append("")

    # Group by variable.group
    groups: dict[str, list[tuple[Variable, dict[str, TimeseriesResponse | None]]]] = {}
    for var, data in variable_results:
        groups.setdefault(var.group, []).append((var, data))

    for group, items in groups.items():
        lines.append("---")
        lines.append(f"## {group}")
        lines.append("")
        for var, scenario_data in items:
            lines.append(f"### {var.name} ({var.unit})")
            if var.description:
                lines.append(f"_{var.description}_")
            if var.reference_period:
                lines.append(f"Ref: {var.reference_period}")
            lines.append("")
            lines.append(_format_overview_variable_table(var, scenario_data, scenario_ids, scenario_names))
            lines.append("")

    if not variable_results:
        lines.append("No climate impact data available for this country.")
        lines.append("")

    lines.append("---")
    lines.append(f"_{DATA_SOURCE}_")
    lines.append("")
    lines.append("_Use `get_climate_projections` for year-by-year detail, `compare_scenarios` for custom scenario comparisons, or `get_spatial_data` for gridded map data._")
    return "\n".join(lines)


def _format_overview_variable_table(
    variable: Variable,
    scenario_data: dict[str, TimeseriesResponse | None],
    scenario_ids: list[str],
    scenario_names: dict[str, str],
) -> str:
    """Build a warming-level comparison table across scenarios."""
    # Collect warming level data per scenario
    wl_by_scenario: dict[str, dict[float, dict]] = {}
    all_wls: set[float] = set()
    for sc_id in scenario_ids:
        ts = scenario_data.get(sc_id)
        if ts is None:
            wl_by_scenario[sc_id] = {}
            continue
        wl_data: dict[float, dict] = {}
        for i, wl in enumerate(ts.warming_levels):
            if wl is not None and i < len(ts.median):
                wl_data[wl] = {
                    "median": ts.median[i],
                    "lower": ts.lower[i],
                    "upper": ts.upper[i],
                    "year": int(ts.year[i]),
                }
                all_wls.add(wl)
        wl_by_scenario[sc_id] = wl_data

    if not all_wls:
        return "_No warming level data available._"

    header = "| Warming Level | " + " | ".join(scenario_names[s] for s in scenario_ids) + " |"
    sep = "|---------------|" + "|".join(["--------"] * len(scenario_ids)) + "|"
    rows = [header, sep]
    for wl in sorted(all_wls):
        row = f"| {wl}\u00b0C |"
        for sc_id in scenario_ids:
            d = wl_by_scenario[sc_id].get(wl)
            if d is None:
                row += " - |"
            else:
                row += f" {_fmt(d['median'])} ({_fmt(d['lower'])}\u2013{_fmt(d['upper'])}) |"
        rows.append(row)
    return "\n".join(rows)


def format_country_list(countries: list[Country], query: str | None = None) -> str:
    if not countries:
        msg = f'No countries found matching "{query}".' if query else "No countries found."
        return msg
    lines = [f"Found {len(countries)} country/ies:", ""]
    lines.append("| Country | ISO |")
    lines.append("|---------|-----|")
    for c in countries[:50]:
        lines.append(f"| {c.name} | {c.id} |")
    if len(countries) > 50:
        lines.append(f"\n_...and {len(countries) - 50} more._")
    return "\n".join(lines)


def format_variable_list(variables: list[Variable]) -> str:
    if not variables:
        return "No variables found."
    groups: dict[str, list[Variable]] = {}
    for v in variables:
        groups.setdefault(v.group, []).append(v)
    lines: list[str] = []
    for group, vars_ in sorted(groups.items()):
        lines.append(f"### {group}")
        lines.append("")
        lines.append("| Variable | Name | Unit |")
        lines.append("|----------|------|------|")
        for v in vars_:
            lines.append(f"| `{v.id}` | {v.name} | {v.unit} |")
        lines.append("")
    return "\n".join(lines)


# --- helpers ---


def _fmt(val: float | None) -> str:
    if val is None:
        return "-"
    return f"{val:.4g}"


def _fmt_wl(val: float | None) -> str:
    if val is None:
        return "-"
    return f"{val}C"


def _value_at_year(ts: TimeseriesResponse, year: int) -> str:
    # year list is floats (e.g. 2030.0), match by int conversion
    for i, y in enumerate(ts.year):
        if int(y) == year:
            median = _fmt(ts.median[i])
            low = _fmt(ts.lower[i])
            high = _fmt(ts.upper[i])
            return f"{median} ({low}-{high})"
    return "-"
