# Release Checklist

This checklist is for the SQL-first Resume Builder architecture reset.

## Scope

The application is a local-first FastAPI/Jinja2 resume builder and AI tailoring assistant.

The source of truth must be SQLite, not YAML or Markdown profile files.

## Privacy rules

User data must stay external to the repository. Runtime data, generated files, SQLite databases, and private contact details must be stored outside the repository.

Raw OpenAI API keys must not be stored in SQLite or committed to Git.

Tests must not call the real OpenAI API.

## Install

```powershell
uv sync --locked --group dev