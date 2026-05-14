# SESSION_NOTES.md

Purpose: short handoff state for the next Codex/AI session. This is not product documentation.

Read first:
1. `AGENTS.md`
2. `SESSION_NOTES.md`
3. files directly related to the current task

---

## Current Stage

Move the project from file-based profile configuration to a managed local application setup.

The current app remains a local FastAPI/Jinja2 web application with manual intake, SQLite/Alembic persistence, fake/demo extraction, optional OpenAI extraction, Markdown CV variants, YAML fact-bank validation, safe fake tailoring, reports, exporters, review pages, safe artefact downloads, app data bootstrap, setup diagnostics, managed settings storage, and a Settings UI for supported non-secret app settings plus OS keyring-backed OpenAI API key management.

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

### PR 3 — Managed settings storage

Implemented:
- dedicated app-level SQLite settings database at `Documents/JobApplicationAssistant/app.sqlite3`, or `APP_DATA_DIR/app.sqlite3` when overridden;
- separate `app/settings/` storage boundary with its own SQLAlchemy metadata, session helpers, schema validation, repository, service, and deterministic schema migration code;
- `app_settings` key/value table for non-secret JSON settings plus an app settings schema version table;
- managed settings support for LLM extraction mode, human approval before export, Markdown/HTML/PDF/DOCX export toggles, default file-based profile name/path, and OpenAI API key configured metadata;
- secret-looking setting keys are rejected, and only boolean OpenAI key metadata may be stored in SQLite;
- effective runtime config loading overlays supported app-managed settings over the existing file-based YAML/default flow;
- setup status now checks app settings storage separately from the profile `applications.sqlite3` database;
- startup error handling catches only expected local setup/storage exceptions while allowing unexpected programming errors to fail loudly;
- regression tests proving `app_settings` is not part of profile DB metadata and profile application tables are not required in `app.sqlite3`.

### PR 4 — Settings UI

Implemented:
- `/settings` GET and POST routes for supported non-secret managed app settings;
- a simple Jinja2 settings page for LLM extraction mode, human approval before final export, export format toggles, and default file-based profile selection;
- form validation for unsupported LLM modes, invalid boolean values, partial default profile selections, unsupported fields, and secret-looking generic fields;
- explicit persistence of unchecked checkbox values as `False`;
- clearing default profile selection when both profile fields are blank;
- setup gate exemptions so `/settings` remains available while setup is incomplete;
- runtime state refresh after saving settings, including clearing stale runtime state when saved settings make setup incomplete;
- tests covering complete and incomplete setup access, settings persistence, OpenAI runtime diagnostics, raw secret rejection, and runtime refresh.

### PR 5 — OS keyring secrets

Implemented:
- added the `app/secrets/` boundary for OpenAI API key read, write, delete, and configured checks;
- added runtime dependency metadata for Python `keyring`;
- stores raw OpenAI API keys through an injectable OS keyring service using stable service/account names;
- keeps SQLite limited to the existing non-secret `secrets.openai_api_key_configured` boolean metadata;
- preserves `OPENAI_API_KEY` as a developer fallback when no keyring value is available;
- updates setup status and LLM runtime validation so fake mode needs no key, OpenAI mode requires `model_extract`, and OpenAI mode accepts either keyring or environment fallback keys;
- passes the resolved effective API key into the OpenAI SDK client path before any network request;
- extends `/settings` so users can configure, replace, or clear the OpenAI API key without prefill, echo, or display of raw key material;
- adds tests with fake keyring backends for secret service operations, Settings UI key management, setup status key resolution, SQLite non-leakage, rendered HTML non-leakage, and OpenAI factory API key injection.

Non-goals preserved:
- no data folder picker UI;
- no managed profiles table;
- no managed CV, fact, alias, section, or block tables;
- no profile import tools;
- no pipeline migration to managed CV storage;
- no URL scraping, auto-apply, LinkedIn automation, email sending, cloud deployment, auth, payments, or LangGraph;
- existing `.env`, YAML, Markdown, and file-based profile support remains compatible.

Remaining risks:
- setup status is still diagnostic; it does not repair missing profile files or run profile migrations;
- if the host OS keyring backend is missing or unavailable, Settings reports a safe keyring error and `OPENAI_API_KEY` remains the developer fallback;
- database readiness checks verify tables/schema but do not yet provide a guided repair or migration button;
- the Settings UI saves profile paths as text and relies on setup checks to report whether the selected path is usable.

## Next Implementation Plan

### PR 6 — Data folder UI

Goal:
Add a safe UI path for viewing and later changing/connecting the local app data folder.

Recommended scope:
- show the current app data folder and app-managed subfolders in setup/settings diagnostics;
- keep folder creation and validation inside `app/storage/`;
- do not migrate profile data automatically;
- do not add managed profiles, managed CV storage, import tools, or data migration in this PR;
- preserve `.env`/`APP_DATA_DIR` as a developer override while introducing user-facing diagnostics.

## Key Decisions

- Default app data folder should be visible and user-owned: `Documents/JobApplicationAssistant/`.
- User should be able to connect an existing data folder in a future PR.
- SQLite should become the primary source of app/profile settings later.
- YAML should remain as example/import/export/fallback only, not the main UI-facing settings store.
- OpenAI API key uses OS keyring as the preferred storage backend, with `OPENAI_API_KEY` retained as a developer fallback.
- SQLite may store secret metadata only, not the raw API key.
- Real private profiles must stay outside the repository.
- The app remains local-first and web-only for v1.
- Do not add auto-apply, LinkedIn automation, email sending, cloud deployment, auth, or LangGraph.
