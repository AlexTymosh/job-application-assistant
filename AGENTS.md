# AGENTS.md

Stable instructions for agents working on this local FastAPI/Jinja2 application.

## Product direction

The product is a local-first Resume Builder and AI Tailoring assistant. SQLite is the source of truth for user-managed data. YAML and Markdown are not runtime sources of truth. Markdown may exist only as an optional export format.

The core flow is:

```text
Person profile -> structured resume -> job description -> extracted requirements -> structured AI change proposals -> human review -> approved snapshot -> private contact layer at render time -> PDF/DOCX export and cover letter
```

The application is not an auto-apply bot. Do not add automatic applications, LinkedIn automation, email sending, broad job scraping, cloud multi-user auth, payments, fake ATS scores, or hidden background submissions.

## Engineering rules

- Work in English for code, comments, docs, UI, tests, PR text, and completion reports.
- Keep routes thin: routes call services; services call repositories, SQLAlchemy models, LLM clients, exporters, or artifact boundaries.
- Store all normal product data in one app-level SQLite database under the selected app data folder.
- Store OpenAI API keys through the OS keyring boundary, never in SQLite and never in templates.
- Tests must not call real OpenAI and must not touch the real OS keyring.
- Private contact details must be excluded from AI prompt builders by default.
- AI tailoring must return structured proposals only. Never apply LLM output directly to the base resume.
- Every proposal must go through review and be accepted or rejected before final export.
- Export uses approved snapshot content and adds private contact data only during final rendering/export.
- Fact links are configurable. When required, AI must not strengthen claims without active verified facts.
- If schema changes, keep deterministic initialisation or migrations explicit, idempotent, tested, and documented.

## Required reading before tasks

1. `AGENTS.md`
2. `SESSION_NOTES.md`
3. `README.md` when product behaviour, UI, or docs are affected
4. Directly related source files

If these documents conflict with stale source code, prefer the current architecture described here and in `SESSION_NOTES.md` and `README.md`.

## Validation

Before completion, run when possible:

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
uv run pre-commit run --all-files
```

## Commit format

Use emoji plus conventional commit style:

```text
🏗 refactor(app): reset to SQL-first resume builder

- optional detail
```
