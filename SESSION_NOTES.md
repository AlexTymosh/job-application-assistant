# SESSION_NOTES.md

Purpose: short handoff state for the next Codex/AI session. This is not product documentation.

Read first:
1. `AGENTS.md`
2. `SESSION_NOTES.md`
3. files directly related to the current task

---

## Current Stage

Move the project from file-based profile configuration to a managed local application setup.

The current app remains a local FastAPI/Jinja2 web application with manual intake, SQLite/Alembic persistence, fake/demo extraction, optional OpenAI extraction, Markdown CV variants, YAML fact-bank validation, safe fake tailoring, reports, exporters, review pages, and safe artefact downloads.

---

## Completed Current Task

### PR 1 — App data directory bootstrap

Implemented:
- app data root resolution under `Documents/JobApplicationAssistant`;
- `APP_DATA_DIR` override support;
- idempotent creation of the app data root plus `profiles/`, `logs/`, and `backups/`;
- tests for path resolution, bootstrap idempotency, and no private profile file creation;
- documentation of the storage bootstrap boundary.

Non-goals preserved:
- no setup redirect;
- no `/setup` route;
- no settings UI;
- no `app_settings` table;
- no OS keyring integration;
- no managed profiles or managed CV storage;
- no pipeline, exporter, OpenAI, auto-apply, LinkedIn, or email changes.

---

## Next Implementation Plan

### PR 2 — Setup status and setup redirect

Goal:
Redirect users to setup when required configuration is missing.

Add:
- `app/setup/__init__.py`
- `app/setup/checks.py`
- `app/setup/service.py`
- `app/api/routes_setup.py`
- `app/web/templates/setup.html`
- `tests/test_setup_checks.py`
- `tests/test_setup_routes.py`

Change:
- home route should redirect to `/setup` if setup is incomplete;
- dashboard remains available only after minimum setup is complete.

Minimum setup checks:
- app data directory exists;
- SQLite database exists or can be created/migrated;
- active profile exists;
- LLM mode is selected;
- if OpenAI mode is selected, API key is configured;
- at least one CV variant/fact source is available.

Commit:
`✨ feat(setup): redirect incomplete installations to setup page`

---

## Key Decisions

- Default app data folder should be visible and user-owned: `Documents/JobApplicationAssistant/`.
- User should be able to connect an existing data folder in a future PR.
- SQLite should become the primary source of app/profile settings later.
- YAML should remain as example/import/export/fallback only, not the main UI-facing settings store.
- OpenAI API key should use OS keyring as the preferred storage backend later.
- SQLite may store secret metadata only, not the raw API key.
- Real private profiles must stay outside the repository.
- The app remains local-first and web-only for v1.
- Do not add auto-apply, LinkedIn automation, email sending, cloud deployment, auth, or LangGraph.
