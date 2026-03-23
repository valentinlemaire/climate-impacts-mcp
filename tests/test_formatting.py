"""Tests for response formatting helpers."""

from __future__ import annotations

import json

from climate_impacts_mcp.formatting import (
    format_comparison_table,
    format_country_list,
    format_country_overview,
    format_spatial_data,
    format_spatial_summary,
    format_timeseries,
    format_variable_list,
    format_warming_level_table,
)
from climate_impacts_mcp.models import (
    Country,
    GeoDataCoords,
    GeoDataResponse,
    TimeseriesResponse,
    Variable,
)


def _make_ts() -> TimeseriesResponse:
    return TimeseriesResponse(
        year=[2030.0, 2050.0, 2100.0],
        lower=[1.0, 1.5, 2.0],
        median=[1.2, 2.0, 3.0],
        upper=[1.4, 2.5, 4.0],
        warming_levels=[1.5, 2.0, 3.0],
    )


def _make_var() -> Variable:
    return Variable(
        id="tasAdjust",
        name="Temperature change",
        unit="degrees C",
        description="Near-surface air temperature",
        group="Climate",
    )


def test_format_timeseries():
    result = format_timeseries(_make_ts(), variable=_make_var(), scenario_name="Current policies")
    assert "Temperature change" in result
    assert "Current policies" in result
    assert "2030" in result
    assert "| Year |" in result


def test_format_comparison_table():
    ts = _make_ts()
    result = format_comparison_table(
        {"h_cpol": ts, "o_1p5c": ts},
        time_horizons=[2030, 2050],
        variable=_make_var(),
    )
    assert "h_cpol" in result
    assert "o_1p5c" in result
    assert "2030" in result


def test_format_warming_level_table():
    result = format_warming_level_table(_make_ts(), variable=_make_var())
    assert "1.5C" in result
    assert "2.0C" in result
    assert "3.0C" in result


def test_format_spatial_summary():
    geo = GeoDataResponse(
        dims=["lat", "lon"],
        data=[[1.0, 2.0], [3.0, 4.0]],
        coords=GeoDataCoords(lat=[50.0, 51.0], lon=[10.0, 11.0]),
        agreement=[[0.8, 0.9], [0.85, 0.95]],
        extent=[1.0, 4.0],
    )
    result = format_spatial_summary(geo, variable=_make_var())
    assert "Grid cells" in result
    assert "Min" in result
    assert "agreement" in result
    assert "Data range" in result


def test_format_country_list():
    countries = [
        Country(id="DEU", name="Germany"),
        Country(id="FRA", name="France"),
    ]
    result = format_country_list(countries)
    assert "Germany" in result
    assert "DEU" in result


def test_format_country_list_empty():
    result = format_country_list([], query="zzz")
    assert "No countries found" in result


def test_format_variable_list():
    variables = [_make_var()]
    result = format_variable_list(variables)
    assert "Climate" in result
    assert "`tasAdjust`" in result


def test_format_spatial_data_with_boundary():
    geo = GeoDataResponse(
        dims=["lat", "lon"],
        data=[[1.0, 2.0], [3.0, 4.0]],
        coords=GeoDataCoords(lat=[50.0, 51.0], lon=[10.0, 11.0]),
        agreement=[[0.8, 0.9], [0.85, 0.95]],
        extent=[1.0, 4.0],
    )
    boundary = {"type": "Topology", "objects": {}, "arcs": []}
    result = format_spatial_data(geo, variable=_make_var(), boundary=boundary, bbox=[5.0, 47.0, 15.0, 55.0])
    assert "Temperature change" in result
    assert "```json" in result
    parsed = json.loads(result.split("```json")[1].split("```")[0])
    assert len(parsed["grid"]) == 4
    assert parsed["boundary"]["type"] == "Topology"
    assert parsed["bbox"] == [5.0, 47.0, 15.0, 55.0]
    assert parsed["stats"]["count"] == 4
    assert parsed["variable"]["id"] == "tasAdjust"


def test_format_spatial_data_without_boundary():
    geo = GeoDataResponse(
        dims=["lat", "lon"],
        data=[[1.0, None], [3.0, 4.0]],
        coords=GeoDataCoords(lat=[50.0, 51.0], lon=[10.0, 11.0]),
        extent=[1.0, 4.0],
    )
    result = format_spatial_data(geo, variable=_make_var(), boundary=None, bbox=None)
    assert "```json" in result
    parsed = json.loads(result.split("```json")[1].split("```")[0])
    assert len(parsed["grid"]) == 3  # null cell skipped
    assert parsed["boundary"] is None


def test_format_spatial_data_empty():
    geo = GeoDataResponse(
        dims=["lat", "lon"],
        data=[[None, None]],
        coords=GeoDataCoords(lat=[50.0], lon=[10.0, 11.0]),
        extent=[],
    )
    result = format_spatial_data(geo)
    assert "No spatial data" in result


def test_format_country_overview():
    ts = _make_ts()
    var = _make_var()
    result = format_country_overview(
        country_name="Germany",
        country_iso="DEU",
        scenario_names={"h_cpol": "Current Policies", "o_1p5c": "1.5C Compatible"},
        variable_results=[(var, {"h_cpol": ts, "o_1p5c": ts})],
        season="annual",
    )
    assert "Germany (DEU)" in result
    assert "Current Policies" in result
    assert "1.5C Compatible" in result
    assert "Temperature change" in result
    assert "1.5°C" in result


def test_format_country_overview_partial_failure():
    ts = _make_ts()
    var = _make_var()
    result = format_country_overview(
        country_name="Germany",
        country_iso="DEU",
        scenario_names={"h_cpol": "Current Policies", "o_1p5c": "1.5C Compatible"},
        variable_results=[(var, {"h_cpol": ts, "o_1p5c": None})],
        season="annual",
    )
    assert "Germany (DEU)" in result
    assert "Temperature change" in result


def test_format_country_overview_empty():
    result = format_country_overview(
        country_name="Germany",
        country_iso="DEU",
        scenario_names={"h_cpol": "Current Policies", "o_1p5c": "1.5C Compatible"},
        variable_results=[],
    )
    assert "No climate impact data" in result
