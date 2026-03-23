# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

An open-source MCP (Model Context Protocol) server that exposes the [CIE API v2](https://cie-api-v2.climateanalytics.org) (Climate Impact Explorer, by Climate Analytics) as MCP tools. This enables LLMs to answer user questions about climate change impacts — such as location-specific exposure under different mitigation scenarios and time horizons.

## Key Context

- **Upstream API**: `cie-api-v2.climateanalytics.org` — all climate data comes from this API; the MCP server is a translation layer, not a data store.
- **Hosting**: GCP (Google Cloud Platform)
- **Protocol**: MCP (Model Context Protocol) — the server exposes tools that LLM clients (e.g. Claude Desktop, Claude Code) can call.
- **Framework**: FastMCP (from `mcp[cli]` package)
- **Transport**: stdio (default/local) or SSE (Cloud Run, set `PORT` env var)

## Commands

```bash
# Install dependencies
poetry install

# Run server (stdio, for local MCP clients)
poetry run climate-impacts-mcp

# Run server (SSE, for Cloud Run)
PORT=8080 poetry run climate-impacts-mcp

# Run tests
poetry run pytest

# Lint
poetry run ruff check src/ tests/

# MCP inspector
poetry run mcp dev src/climate_impacts_mcp/server.py

# Docker
docker build -t climate-impacts-mcp .
docker run -p 8080:8080 climate-impacts-mcp
```

## Architecture

```
src/climate_impacts_mcp/
├── server.py          # FastMCP entry point, lifespan (httpx client + metadata cache)
├── client.py          # Async httpx wrapper for CIE API v2
├── models.py          # Pydantic models for API responses
├── formatting.py      # Markdown formatting for LLM-friendly output
└── tools/
    ├── metadata.py    # Discovery tools (cached, no API calls): lookup_country, list_climate_variables, list_scenarios
    ├── timeseries.py  # Projection tools: get_climate_projections, compare_scenarios, get_warming_level_snapshot
    └── geodata.py     # Spatial tool: get_spatial_data
```

- **Lifespan** creates a shared `httpx.AsyncClient`, instantiates `CIEClient`, and pre-fetches metadata (cached for server lifetime).
- **Tools** access the client and metadata via `ctx.request_context.lifespan_context`.
- All tools return formatted markdown strings, not raw JSON.
