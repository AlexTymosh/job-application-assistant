# Release checklist

- Run `uv run ruff format .`.
- Run `uv run ruff check .`.
- Run `uv run pytest`.
- Run `uv run pre-commit run --all-files`.
- Confirm no raw API keys are stored in SQLite or rendered in HTML.
- Confirm tests use fake AI clients.
- Confirm artifact paths are relative and safe to download.
- Confirm documentation describes SQLite as the source of truth.
- Confirm no auto-apply, LinkedIn automation, email sending, or broad scraping was added.
