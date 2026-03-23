# CIE API v2 Mapping

Base URL: `https://cie-api-v2.climateanalytics.org`

---

## Endpoints

### GET `/api/meta/`

Returns all metadata: countries, country groups, scenarios, and variables.

**Parameters**: None

**Response schema**:
```json
{
  "countries": [
    {
      "name": "Germany",
      "iso": "DEU",
      "region": "Western Europe",
      "group": "OECD"
    }
  ],
  "country_groups": [
    {
      "name": "OECD",
      "iso": "OECD",
      "countries": ["DEU", "FRA", ...]
    }
  ],
  "scenarios": [
    {
      "name": "h_cpol",
      "description": "Current policies"
    }
  ],
  "variables": [
    {
      "name": "tas",
      "longname": "Temperature change",
      "unit": "degrees C",
      "description": "...",
      "group": "Climate"
    }
  ]
}
```

---

### GET `/api/timeseries/`

Returns projected timeseries data for a country, variable, scenario, season, and spatial aggregation.

**Parameters**:

| Parameter              | Type   | Required | Description                      |
|------------------------|--------|----------|----------------------------------|
| `iso`                  | string | Yes      | Country/group ISO code (e.g. `DEU`) |
| `var`                  | string | Yes      | Variable short name (e.g. `tas`) |
| `scenario`             | string | Yes      | Scenario ID                      |
| `season`               | string | No       | Season (default: `annual`)       |
| `aggregation_spatial`  | string | No       | Spatial aggregation (default: `area`) |

**Response schema**:
```json
{
  "year": [2015, 2020, 2025, ..., 2100],
  "lower": [0.8, 0.9, ...],
  "median": [1.0, 1.1, ...],
  "upper": [1.2, 1.3, ...],
  "warming_levels": [null, null, 1.5, 2.0, ...],
  "reference_value": 12.5
}
```

- Data range: 2015-2100 in 5-year intervals (18 data points)
- `lower`/`median`/`upper` represent the uncertainty range across model ensemble
- `warming_levels` maps each year to the global mean temperature increase; contains `null` for low-emission scenarios at later years where warming levels are not reached
- `reference_value` is the baseline value for the reference period

---

### GET `/api/geo-data/`

Returns spatial (gridded) data for a country, variable, and warming level.

**Parameters**:

| Parameter         | Type   | Required | Description                           |
|-------------------|--------|----------|---------------------------------------|
| `iso`             | string | Yes      | Country/group ISO code                |
| `var`             | string | Yes      | Variable short name                   |
| `season`          | string | No       | Season (default: `annual`)            |
| `scenarios`       | string | No       | Comma-separated scenario IDs          |
| `warming_levels`  | string | No       | Comma-separated warming levels (e.g. `1.5,2.0`) |

**Response schema**:
```json
{
  "dims": ["lat", "lon"],
  "data": [[...], [...]],
  "coords": {
    "lat": {"dims": ["lat"], "attrs": {}, "data": [47.0, 47.5, ...]},
    "lon": {"dims": ["lon"], "attrs": {}, "data": [5.5, 6.0, ...]},
    "quantile": {"dims": [], "attrs": {}, "data": 0.5},
    "warming_level": {"dims": [], "attrs": {}, "data": 2.0},
    "second_warming_level": {"dims": [], "attrs": {}, "data": 1.0},
    "region": {"dims": [], "attrs": {}, "data": "DEU"}
  },
  "agreement": [[...], [...]],
  "extent": [min_value, max_value],
  "warming_levels": "2.0 vs 1.0"
}
```

- `data` is a 2D grid of variable values
- `coords` uses xarray-serialized format: each coordinate is an object with `dims`, `attrs`, and `data` fields
- `agreement` is a 2D grid of model agreement fractions (0-1)
- `extent` is a 2-element array with the min/max of the data values (not geographic bounds)
- `warming_levels` is a descriptive string of the warming level comparison

---

### GET `/api/geo-shapes/`

Returns TopoJSON country boundary with subregion name lookup.

**Parameters**:

| Parameter | Type   | Required | Description                          |
|-----------|--------|----------|--------------------------------------|
| `iso`     | string | Yes      | Country ISO code (e.g. `DEU`)        |

**Response schema**:
```json
{
  "country": {
    "type": "Topology",
    "objects": { ... },
    "arcs": [...]
  },
  "bbox": [lon_min, lat_min, lon_max, lat_max]
}
```

- `country` contains the TopoJSON topology with a `MultiPolygon` geometry for the country outline
- Geometry properties include `adm0_a3` (ISO code), `initial_bounds`, and `subregions`
- `subregions` is a name lookup only (e.g. `{"DE.BW": "Baden-Württemberg", ...}`) — no geometry for individual subdivisions
- `bbox` is the geographic bounding box

---

## Allowed Values

### Scenarios (9)

| ID                     | Description                              |
|------------------------|------------------------------------------|
| `h_cpol`               | Current policies                         |
| `h_cpol_high_impact`   | Current policies (high impact)           |
| `o_1p5c`               | 1.5C compatible                          |
| `d_strain`             | Strain                                   |
| `h_ndc`                | NDCs (Nationally Determined Contributions) |
| `o_2c`                 | 2C compatible                            |
| `o_lowdem`             | Low demand                               |
| `d_delfrag`            | Delayed and fragmented                   |
| `cat_current`          | CAT current policies                     |

### Seasons (5)

| ID       | Description          |
|----------|----------------------|
| `annual` | Full year average    |
| `MAM`    | March-April-May      |
| `JJA`    | June-July-August     |
| `SON`    | September-October-November |
| `DJF`    | December-January-February  |

### Spatial Aggregations (9)

| ID         | Description                    |
|------------|--------------------------------|
| `area`     | Area-weighted average          |
| `pop`      | Population-weighted average    |
| `gdp`      | GDP-weighted average           |
| `harvarea` | Harvest-area-weighted average  |
| `wheat`    | Wheat harvest area             |
| `maize`    | Maize harvest area             |
| `soybean`  | Soybean harvest area           |
| `rice`     | Rice harvest area              |
| `sum`      | Sum (total)                    |

### Variable Groups (~43 variables)

| Group                  | Example Variables                           |
|------------------------|---------------------------------------------|
| Climate                | `tas`, `pr`, `sst`                          |
| Drought                | `drought_*`                                 |
| Heat                   | `heatwave_*`, `hot_days_*`                  |
| Extreme Precipitation  | `precip_extreme_*`                          |
| Fire                   | `fire_*`, `burnt_area_*`                    |
| Freshwater             | `water_*`, `runoff_*`                       |
| Agriculture            | `crop_yield_*`                              |
| Labour Productivity    | `labour_*`                                  |

(Exact variable list is dynamic; use `/api/meta/` to get current variables.)

### Warming Levels

`1.5`, `2.0`, `2.5`, `3.0` (degrees C above pre-industrial)

---

## Error Handling

Error responses have this structure:
```json
{
  "status": {
    "type": "error",
    "message": "<html>...</html>"
  }
}
```

The `message` field often contains HTML — strip tags before displaying.

---

## Known Quirks

- The `var` parameter caused errors in some v2 timeseries calls for certain variables
- Some country + scenario combinations return no data (empty arrays)
- `warming_levels` array contains `null` values for low-emission scenarios at later years where those warming levels are never reached
- Data is in 5-year intervals: 2015, 2020, 2025, ..., 2095, 2100 (18 points)
