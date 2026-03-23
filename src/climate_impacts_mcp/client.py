"""Async HTTP client for the CIE API v2."""

from __future__ import annotations

import re

import httpx

from .models import (
    CIEErrorResponse,
    GeoDataResponse,
    Metadata,
    TimeseriesResponse,
)

BASE_URL = "https://cie-api-v2.climateanalytics.org"


class CIEAPIError(Exception):
    """Raised when the CIE API returns an error response."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


class CIEClient:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self.http = http_client

    async def get_metadata(self) -> Metadata:
        resp = await self.http.get(f"{BASE_URL}/api/meta/")
        resp.raise_for_status()
        return Metadata.model_validate(resp.json())

    async def get_timeseries(
        self,
        iso: str,
        var: str,
        scenario: str,
        season: str = "annual",
        aggregation_spatial: str = "area",
    ) -> TimeseriesResponse:
        params = {
            "iso": iso,
            "var": var,
            "scenario": scenario,
            "season": season,
            "aggregation_spatial": aggregation_spatial,
        }
        resp = await self.http.get(f"{BASE_URL}/api/timeseries/", params=params)
        resp.raise_for_status()
        data = resp.json()
        self._check_error(data)
        return TimeseriesResponse.model_validate(data)

    async def get_geo_data(
        self,
        iso: str,
        var: str,
        season: str = "annual",
        scenarios: str | None = None,
        warming_levels: str | None = None,
    ) -> GeoDataResponse:
        params: dict[str, str] = {
            "iso": iso,
            "var": var,
            "season": season,
        }
        if scenarios:
            params["scenarios"] = scenarios
        if warming_levels:
            params["warming_levels"] = warming_levels
        resp = await self.http.get(f"{BASE_URL}/api/geo-data/", params=params)
        resp.raise_for_status()
        data = resp.json()
        self._check_error(data)
        return GeoDataResponse.model_validate(data)

    def _check_error(self, data: dict) -> None:
        if isinstance(data.get("status"), dict) and data["status"].get("type") == "error":
            err = CIEErrorResponse.model_validate(data)
            raise CIEAPIError(_strip_html(err.status.message))
