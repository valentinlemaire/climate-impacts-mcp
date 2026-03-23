"""Tests for the validation module."""

from __future__ import annotations

from climate_impacts_mcp.tools.validation import (
    resolve_country_name,
    resolve_variable,
    validate_country,
    validate_scenario,
    validate_season,
    validate_spatial_weighting,
    validate_warming_level,
)
from tests.conftest import SAMPLE_METADATA


# --- resolve_country_name ---


def test_resolve_country_name_by_iso():
    country, err = resolve_country_name(SAMPLE_METADATA, "DEU")
    assert country is not None
    assert country.id == "DEU"
    assert country.name == "Germany"
    assert err is None


def test_resolve_country_name_by_iso_case_insensitive():
    country, err = resolve_country_name(SAMPLE_METADATA, "deu")
    assert country is not None
    assert country.id == "DEU"
    assert err is None


def test_resolve_country_name_exact_name():
    country, err = resolve_country_name(SAMPLE_METADATA, "Germany")
    assert country is not None
    assert country.id == "DEU"
    assert err is None


def test_resolve_country_name_exact_name_case_insensitive():
    country, err = resolve_country_name(SAMPLE_METADATA, "germany")
    assert country is not None
    assert country.id == "DEU"
    assert err is None


def test_resolve_country_name_substring_unique():
    country, err = resolve_country_name(SAMPLE_METADATA, "germ")
    assert country is not None
    assert country.id == "DEU"
    assert err is None


def test_resolve_country_name_substring_ambiguous():
    # Both "France" and "Germany" don't overlap, but "an" matches "Germany" and "France"
    country, err = resolve_country_name(SAMPLE_METADATA, "an")
    assert country is None
    assert "Multiple countries" in err


def test_resolve_country_name_no_match():
    country, err = resolve_country_name(SAMPLE_METADATA, "zzzzz")
    assert country is None
    assert "not found" in err


# --- resolve_variable ---


def test_resolve_variable_exact():
    result = resolve_variable(SAMPLE_METADATA, "tasAdjust")
    assert result.id == "tasAdjust"


def test_resolve_variable_case_insensitive():
    result = resolve_variable(SAMPLE_METADATA, "tasadjust")
    assert result.id == "tasAdjust"


def test_resolve_variable_not_found_with_suggestions():
    result = resolve_variable(SAMPLE_METADATA, "tas")
    assert isinstance(result, str)
    assert "not found" in result
    assert "tasAdjust" in result
    assert "list_climate_variables" in result


def test_resolve_variable_no_match():
    result = resolve_variable(SAMPLE_METADATA, "zzzzz")
    assert isinstance(result, str)
    assert "not found" in result


# --- validate_country ---


def test_validate_country_exact():
    iso, err = validate_country(SAMPLE_METADATA, "DEU")
    assert iso == "DEU"
    assert err is None


def test_validate_country_case_insensitive():
    iso, err = validate_country(SAMPLE_METADATA, "deu")
    assert iso == "DEU"
    assert err is None


def test_validate_country_invalid_with_suggestions():
    iso, err = validate_country(SAMPLE_METADATA, "DE")
    assert iso is None
    assert "not found" in err
    assert "lookup_country" in err


# --- validate_scenario ---


def test_validate_scenario_exact():
    sid, err = validate_scenario(SAMPLE_METADATA, "h_cpol")
    assert sid == "h_cpol"
    assert err is None


def test_validate_scenario_invalid():
    sid, err = validate_scenario(SAMPLE_METADATA, "rcp85")
    assert sid is None
    assert "not found" in err
    assert "list_scenarios" in err


# --- validate_season ---


def test_validate_season_valid():
    season, err = validate_season("annual")
    assert season == "annual"
    assert err is None


def test_validate_season_case_insensitive():
    season, err = validate_season("mam")
    assert season == "MAM"
    assert err is None


def test_validate_season_invalid():
    season, err = validate_season("spring")
    assert season is None
    assert "not valid" in err


# --- validate_spatial_weighting ---


def test_validate_spatial_weighting_compatible():
    var = SAMPLE_METADATA.vars[0]  # tasAdjust, allows ["area", "pop"]
    err = validate_spatial_weighting(SAMPLE_METADATA, var, "area")
    assert err is None


def test_validate_spatial_weighting_incompatible():
    var = SAMPLE_METADATA.vars[0]  # tasAdjust, allows ["area", "pop"]
    err = validate_spatial_weighting(SAMPLE_METADATA, var, "gdp")
    assert err is not None
    assert "not compatible" in err
    assert "area" in err


def test_validate_spatial_weighting_empty_allowlist():
    var = SAMPLE_METADATA.vars[1]  # prAdjust, allows []
    err = validate_spatial_weighting(SAMPLE_METADATA, var, "gdp")
    assert err is None


def test_validate_spatial_weighting_unknown():
    var = SAMPLE_METADATA.vars[0]
    err = validate_spatial_weighting(SAMPLE_METADATA, var, "nonexistent")
    assert err is not None
    assert "not found" in err


# --- validate_warming_level ---


def test_validate_warming_level_valid():
    err = validate_warming_level(2.0)
    assert err is None


def test_validate_warming_level_invalid():
    err = validate_warming_level(4.0)
    assert err is not None
    assert "not valid" in err
