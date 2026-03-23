# Contributing

Contributions are welcome! Here's how to get started.

## Development setup

```bash
git clone https://github.com/valentinlemaire/climate-impacts-mcp.git
cd climate-impacts-mcp
poetry install
```

## Workflow

1. Fork the repo and create a feature branch from `main`
2. Make your changes
3. Run tests and lint:
   ```bash
   poetry run pytest
   poetry run ruff check src/ tests/
   ```
4. Open a pull request

## Guidelines

- Keep changes focused — one feature or fix per PR
- Add tests for new tools or formatting changes
- Follow existing code patterns (validation, formatting, error handling)
- All tools must return markdown strings, not raw JSON
- Run `ruff check` before submitting — the CI will enforce it

## Architecture

See `CLAUDE.md` for a quick overview of the codebase structure and conventions.
