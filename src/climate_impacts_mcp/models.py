"""Pydantic models for CIE API v2 responses."""

from __future__ import annotations

from pydantic import BaseModel, field_validator


# --- Metadata models ---


class Country(BaseModel):
    id: str
    name: str
    large: bool = False


class CountryGroup(BaseModel):
    id: str
    name: str
    children: list[str]


class Scenario(BaseModel):
    id: str
    name: str
    description: str
    basescenario: bool = False
    primary: bool = False


class SpatialWeighting(BaseModel):
    id: str
    name: str


class TemporalAveraging(BaseModel):
    id: str
    name: str


class Unit(BaseModel):
    id: str
    name: str
    short: str
    latex: str = ""


class VariableGroup(BaseModel):
    id: str
    name: str
    children: list[str]
    type: str = ""


class Variable(BaseModel):
    id: str
    name: str
    unit: str
    description: str
    group: str
    change_type: str | None = None
    disclaimer: str | None = None
    display_mode: str | None = None
    impact_type: str | None = None
    level: int = 0
    orig_unit: str | None = None
    reference_period: str | None = None
    scale_direction: int | None = None
    scale_type: str | None = None
    source: str | None = None
    spatial_weighting: list[str] = []
    temporal_averaging: list[str] = []


class Metadata(BaseModel):
    countries: list[Country]
    country_groups: list[CountryGroup]
    scenarios: list[Scenario]
    spatial_weightings: list[SpatialWeighting]
    temporal_averagings: list[TemporalAveraging]
    units: list[Unit]
    variable_groups: list[VariableGroup]
    vars: list[Variable]


# --- Timeseries models ---


class TimeseriesResponse(BaseModel):
    year: list[float]
    lower: list[float | None]
    median: list[float | None]
    upper: list[float | None]
    warming_levels: list[float | None]
    reference_value: float | None = None
    disclaimer: str | None = None


# --- Geo-data models ---


class GeoDataCoords(BaseModel, extra="allow"):
    lat: list[float]
    lon: list[float]

    @field_validator("lat", "lon", mode="before")
    @classmethod
    def extract_xarray_data(cls, v: object) -> object:
        if isinstance(v, dict) and "data" in v:
            return v["data"]
        return v


class GeoDataResponse(BaseModel, extra="allow"):
    dims: list[str]
    data: list[list[float | None]]
    coords: GeoDataCoords
    agreement: list[list[float | None]] | None = None
    extent: list[float]
    warming_levels: str | None = None


# --- Error model ---


class CIEErrorStatus(BaseModel):
    type: str
    message: str


class CIEErrorResponse(BaseModel):
    status: CIEErrorStatus
