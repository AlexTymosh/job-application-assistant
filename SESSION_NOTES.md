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

## Completed Current Tasks

### PR 1 — App data directory bootstrap

Implemented:
- app data root resolution under `Documents/JobApplicationAssistant`;
- `APP_DATA_DIR` override support;
- idempotent creation of the app data root plus `profiles/`, `logs/`, and `backups/`;
- tests for path resolution, bootstrap idempotency, and no private profile file creation;
- documentation of the storage bootstrap boundary.

### PR 2 — Setup status and setup redirect

Implemented:
- setup status models and service checks for app data folders, file-based profile config, active profile folders, SQLite database tables, LLM runtime mode, default CV variant loading, and fact-bank validation;
- startup refactor so missing or invalid profile/LLM setup is represented as incomplete setup instead of a startup crash;
- `/setup` route and template that render setup pass/fail status without exposing secrets;
- middleware setup gate that redirects incomplete installations to `/setup` before route dependencies run;
- health and documentation routes remain available while setup is incomplete;
- tests for setup checks, side-effect boundaries, redirects, and complete/incomplete route behaviour.

Non-goals preserved:
- no settings UI;
- no `app_settings` table;
- no OS keyring integration;
- no managed profiles table;
- no managed CV, fact, alias, section, or block tables;
- no profile import tools;
- no URL scraping, auto-apply, LinkedIn automation, email sending, cloud deployment, auth, or LangGraph;
- existing YAML/Markdown file-based profile support remains compatible.

Remaining risks:
- setup status is currently diagnostic only; it does not repair missing profile files or run migrations;
- OpenAI API keys still come from the environment until keyring support is added;
- database readiness checks verify tables but do not yet provide a guided migration button or detailed migration version UI.

---

## Next Implementation Plan

### PR 3 — Managed settings storage

Goal:
Introduce the first app-managed settings storage layer while preserving existing file-based profile compatibility.

Recommended scope:
- add an app-level SQLite settings database under the app data root;
- add an `app_settings` table via Alembic or a dedicated app-data migration boundary;
- persist non-secret setup metadata such as selected profile path, selected LLM mode, and whether an OpenAI key is configured;
- keep raw API keys out of SQLite;
- continue supporting existing `.env`, `PROFILE_NAME`, `PROFILE_DATA_DIR`, YAML config, Markdown CV variants, and YAML fact-bank files;
- avoid managed CV/fact/profile rewrites until later PRs.

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
