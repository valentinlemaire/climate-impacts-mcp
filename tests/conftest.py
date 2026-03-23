"""Shared test fixtures."""

from __future__ import annotations

import pytest
import httpx
import respx

from climate_impacts_mcp.client import CIEClient
from climate_impacts_mcp.models import (
    Country,
    CountryGroup,
    Metadata,
    Scenario,
    SpatialWeighting,
    TemporalAveraging,
    Unit,
    Variable,
    VariableGroup,
)

SAMPLE_METADATA = Metadata(
    countries=[
        Country(id="DEU", name="Germany", large=True),
        Country(id="FRA", name="France", large=True),
        Country(id="IND", name="India", large=True),
    ],
    country_groups=[
        CountryGroup(id="oecd", name="OECD", children=["DEU", "FRA"]),
        CountryGroup(id="southern_asia", name="Southern Asia", children=["IND"]),
    ],
    scenarios=[
        Scenario(id="h_cpol", name="NGFS current policies", description="Current policies scenario"),
        Scenario(id="o_1p5c", name="1.5C compatible", description="1.5C compatible scenario"),
        Scenario(id="h_ndc", name="NDCs", description="NDCs scenario"),
    ],
    spatial_weightings=[
        SpatialWeighting(id="area", name="Area-weighted average"),
        SpatialWeighting(id="pop", name="Population-weighted average"),
        SpatialWeighting(id="gdp", name="GDP-weighted average"),
    ],
    temporal_averagings=[
        TemporalAveraging(id="annual", name="Annual"),
    ],
    units=[
        Unit(id="degc", name="degrees Celsius", short="C"),
    ],
    variable_groups=[
        VariableGroup(id="Climate", name="Climate", children=["tasAdjust", "prAdjust"]),
    ],
    vars=[
        Variable(
            id="tasAdjust",
            name="Temperature change",
            unit="degrees C",
            description="Near-surface air temperature change",
            group="Climate",
            reference_period="reference period 1995-2014",
            spatial_weighting=["area", "pop"],
        ),
        Variable(
            id="prAdjust",
            name="Precipitation change",
            unit="%",
            description="Precipitation change",
            group="Climate",
            spatial_weighting=[],
        ),
    ],
)

SAMPLE_TIMESERIES = {
    "year": [2015.0, 2020.0, 2025.0, 2030.0, 2050.0, 2100.0],
    "lower": [0.8, 0.9, 1.0, 1.1, 1.8, 2.5],
    "median": [1.0, 1.1, 1.2, 1.4, 2.2, 3.5],
    "upper": [1.2, 1.3, 1.5, 1.7, 2.6, 4.5],
    "warming_levels": [None, None, 1.5, 2.0, 2.5, 3.0],
    "reference_value": None,
    "disclaimer": None,
}

SAMPLE_GEO_DATA = {
    "dims": ["lat", "lon"],
    "data": [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
    "coords": {
        "lat": {"dims": ["lat"], "attrs": {}, "data": [50.0, 51.0]},
        "lon": {"dims": ["lon"], "attrs": {}, "data": [10.0, 11.0, 12.0]},
        "quantile": {"dims": [], "attrs": {}, "data": 0.5},
        "warming_level": {"dims": [], "attrs": {}, "data": 2.0},
        "second_warming_level": {"dims": [], "attrs": {}, "data": 1.0},
        "region": {"dims": [], "attrs": {}, "data": "DEU"},
    },
    "agreement": [[0.8, 0.9, 0.85], [0.7, 0.95, 0.9]],
    "extent": [1.0, 6.0],
    "warming_levels": "2.0 vs 1.0",
}


SAMPLE_WORLD_ATLAS = {
    "type": "Topology",
    "objects": {
        "countries": {
            "type": "GeometryCollection",
            "geometries": [
                {"type": "Polygon", "arcs": [[0]], "id": "276"},  # DEU
                {"type": "Polygon", "arcs": [[1]], "id": "250"},  # FRA
            ],
        }
    },
    "arcs": [
        [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],  # arc 0 (DEU)
        [[20, 0], [30, 0], [30, 10], [20, 10], [20, 0]],  # arc 1 (FRA)
    ],
}


@pytest.fixture
def sample_metadata() -> Metadata:
    return SAMPLE_METADATA


@pytest.fixture
def mock_api():
    with respx.mock(base_url="https://cie-api-v2.climateanalytics.org", assert_all_called=False) as mock:
        mock.get("/api/meta/").respond(json=SAMPLE_METADATA.model_dump())
        mock.get("/api/timeseries/").respond(json=SAMPLE_TIMESERIES)
        mock.get("/api/geo-data/").respond(json=SAMPLE_GEO_DATA)
        yield mock


@pytest.fixture
async def client(mock_api):
    async with httpx.AsyncClient() as http:
        yield CIEClient(http)
