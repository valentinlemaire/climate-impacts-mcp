# Climate Impacts MCP Server

An open-source [MCP](https://modelcontextprotocol.io) (Model Context Protocol) server that gives LLMs access to climate change impact data. It wraps the [Climate Impact Explorer API](https://cie-api-v2.climateanalytics.org) so that AI assistants like Claude can answer questions about temperature change, drought, heatwaves, agriculture, and more — by country, emission scenario, and time horizon.

## Data Attribution

All climate impact data is provided by the **[Climate Impact Explorer](https://climate-impact-explorer.climateanalytics.org)**, developed by **[Climate Analytics](https://climateanalytics.org)** and based on climate impact models developed by **[IIASA](https://iiasa.ac.at)** (International Institute for Applied Systems Analysis).

This MCP server is a translation layer — it does not store or modify the underlying data.

## Features

- **Single-call country overview** — ask "what are the climate impacts in Costa Rica?" and get a multi-variable summary in one tool call
- **Timeseries projections** — year-by-year data from 2015 to 2100 with uncertainty ranges
- **Scenario comparison** — side-by-side comparison of emission pathways (current policies, 1.5C, NDCs, etc.)
- **Warming level snapshots** — impacts indexed by global warming level (1.5/2.0/2.5/3.0C)
- **Spatial map data** — per-cell gridded data with country boundary (TopoJSON) for map rendering
- **Smart validation** — fuzzy-matching on country names, variable IDs, and scenarios with helpful suggestions

## Tools

| Tool | Description |
|------|-------------|
| `get_country_overview` | Comprehensive multi-variable impact summary for a country (accepts names like "Costa Rica") |
| `lookup_country` | Fuzzy-match country name to ISO code |
| `list_climate_variables` | List available climate variables by category |
| `list_scenarios` | List emission scenarios |
| `get_climate_projections` | Timeseries projections for a country/variable/scenario |
| `compare_scenarios` | Compare multiple scenarios side-by-side at key time horizons |
| `get_warming_level_snapshot` | View impacts by warming level (1.5/2.0/2.5/3.0C) |
| `get_spatial_data` | Gridded spatial data + country boundary for map rendering |

## Quick Start

### Local (Claude Desktop)

1. Install dependencies:
   ```bash
   poetry install
   ```

2. Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):
   ```json
   {
     "mcpServers": {
       "climate-impacts": {
         "command": "/path/to/your/virtualenv/bin/python",
         "args": ["-m", "climate_impacts_mcp"]
       }
     }
   }
   ```
   Replace the command path with the output of `poetry env info -e`.

3. Restart Claude Desktop. The climate tools will appear automatically.

### Remote (SSE transport)

```bash
PORT=8080 poetry run climate-impacts-mcp
```

The server runs in SSE mode when `PORT` is set, suitable for Cloud Run or any remote deployment.

## Architecture

```
src/climate_impacts_mcp/
├── server.py          # FastMCP entry point, lifespan (httpx client + caches)
├── client.py          # Async httpx wrapper for CIE API v2
├── models.py          # Pydantic models for API responses
├── formatting.py      # Markdown formatting for LLM-friendly output
├── boundaries.py      # Country boundary extraction from world-atlas TopoJSON
└── tools/
    ├── metadata.py    # Discovery tools (cached): lookup_country, list_climate_variables, list_scenarios
    ├── timeseries.py  # Projection tools: get_climate_projections, compare_scenarios, get_warming_level_snapshot
    ├── geodata.py     # Spatial tool: get_spatial_data (grid + boundary)
    ├── overview.py    # High-level: get_country_overview (multi-variable parallel fetch)
    └── validation.py  # Input validation with fuzzy-matching
```

On startup, the server pre-fetches and caches:
- CIE API metadata (countries, variables, scenarios)
- World-atlas TopoJSON (country boundaries for map rendering)

## Deploy to GCP Cloud Run

### Using Cloud Build

```bash
gcloud builds submit --config cloudbuild.yaml
```

### Manual deploy

```bash
gcloud run deploy climate-impacts-mcp \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080
```

### Docker

```bash
docker build -t climate-impacts-mcp .
docker run -p 8080:8080 climate-impacts-mcp
```

## Development

```bash
# Install all dependencies (including dev)
poetry install

# Run tests
poetry run pytest

# Lint
poetry run ruff check src/ tests/

# Interactive MCP inspector
poetry run mcp dev src/climate_impacts_mcp/server.py
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `PORT` | (unset) | If set, runs in SSE mode on this port. If unset, runs in stdio mode. |

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

- **[Climate Analytics](https://climateanalytics.org)** — Climate Impact Explorer API and data
- **[IIASA](https://iiasa.ac.at)** — Climate impact models underlying the data
- **[Natural Earth / world-atlas](https://github.com/topojson/world-atlas)** — Country boundary data for map rendering
