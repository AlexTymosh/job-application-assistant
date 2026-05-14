# SESSION_NOTES.md

Purpose: short handoff state for the next Codex/AI session. This is not product documentation.

Read first:
1. `AGENTS.md`
2. `SESSION_NOTES.md`
3. files directly related to the current task

---

## Current Stage

Move the project from file-based profile configuration to a managed local application setup.

The current app remains a local FastAPI/Jinja2 web application with manual intake, SQLite/Alembic persistence, fake/demo extraction, optional OpenAI extraction, Markdown CV variants, YAML fact-bank validation, safe fake tailoring, reports, exporters, review pages, safe artefact downloads, app data bootstrap, setup diagnostics, managed settings storage, a Settings UI for supported non-secret app settings plus OS keyring-backed OpenAI API key management, and a Data Folder UI for connecting the app data root safely.

---

## Completed Current Tasks

### PR 1 — App data directory bootstrap

Implemented the default `Documents/JobApplicationAssistant` app data root, `APP_DATA_DIR` override support, and idempotent creation of only `profiles/`, `logs/`, and `backups/` without private profile files.

### PR 2 — Setup status and setup redirect

Implemented setup diagnostics for app data folders, file-based profile config, active profile readiness, profile SQLite tables, LLM mode, default CV variant, and fact-bank validation, plus `/setup` and the setup redirect gate.

### PR 3 — Managed settings storage

Implemented `app_data_root/app.sqlite3` for non-secret app settings, deterministic settings schema migration, managed settings overlay onto runtime config, and setup checks proving app settings storage is separate from profile databases.

### PR 4 — Settings UI

Implemented `/settings` for supported non-secret managed settings, default file-based profile selection, validation, setup-gate exemption, and runtime refresh after saves.

### PR 5 — OS keyring secrets

Implemented `app/secrets/` for OpenAI API key storage through an injectable OS keyring boundary, kept SQLite limited to key-configured metadata, preserved `OPENAI_API_KEY` as a developer fallback, and updated setup/settings/runtime tests for safe secret handling.

### PR 6 — Data Folder UI

Implemented:
- `app/storage/` location boundary for resolving `APP_DATA_DIR`, persisted user selection, and default Documents app data roots;
- persisted app data root pointer storage outside the app data folder to avoid the `app.sqlite3` circular dependency;
- `/data-folder` GET/POST page for viewing, validating, creating, and connecting the app data root;
- setup-gate exemption and base navigation for `/data-folder`;
- safe connect/create behaviour that rejects blank, repository-internal, file-like invalid, and `APP_DATA_DIR`-controlled changes;
- bootstrap of only `profiles/`, `logs/`, `backups/`, generic `README.txt`, and `app.sqlite3`;
- runtime state refresh after a successful data folder connection;
- tests covering default/pointer/env precedence, route availability, page diagnostics, POST validation, pointer persistence, state refresh, no profile file creation, and no raw OpenAI key leakage.

Non-goals preserved:
- no managed profiles table;
- no managed CV, fact, alias, section, or block tables;
- no profile import tools;
- no profile data migration;
- no pipeline migration to managed CV storage;
- no URL scraping, auto-apply, LinkedIn automation, email sending, cloud deployment, auth, payments, or LangGraph;
- existing `.env`, YAML, Markdown, and file-based profile support remains compatible.

Remaining risks:
- setup status is still diagnostic; it does not repair missing profile files or run profile migrations;
- if the host OS keyring backend is missing or unavailable, Settings reports a safe keyring error and `OPENAI_API_KEY` remains the developer fallback;
- database readiness checks verify tables/schema but do not yet provide a guided repair or migration button;
- the Settings UI saves profile paths as text and relies on setup checks to report whether the selected path is usable;
- the Data Folder UI uses a text path input for this local developer release and does not provide an OS-native folder picker.

## Next Implementation Plan

### PR 7 — Managed profiles

Goal:
Add the first managed profiles foundation without migrating CV/fact data or changing the pipeline to DB-backed CV storage.

Recommended scope:
- introduce managed profile records in app-managed storage;
- support active managed profile selection through app services and thin routes;
- allow connecting existing file-based profile folders by path;
- keep existing `.env`, YAML, Markdown, and file-based profile behaviour compatible;
- do not import Markdown/YAML into managed CV/fact tables in this PR;
- do not migrate profile `applications.sqlite3` data automatically;
- do not change the tailoring/export pipeline to managed CV/fact storage yet.

Non-goals for PR 7:
- no managed CV storage;
- no import tools;
- no CV/fact editor;
- no pipeline migration;
- no profile backup/export tooling;
- no URL scraping, auto-apply, LinkedIn automation, email sending, cloud deployment, auth, payments, or LangGraph.

## Key Decisions

- Default app data folder should be visible and user-owned: `Documents/JobApplicationAssistant/`.
- Users can connect an existing app data folder through `/data-folder`; `APP_DATA_DIR` remains the highest-priority developer override.
- SQLite should become the primary source of app/profile settings later.
- YAML should remain as example/import/export/fallback only, not the main UI-facing settings store.
- OpenAI API key uses OS keyring as the preferred storage backend, with `OPENAI_API_KEY` retained as a developer fallback.
- SQLite may store secret metadata only, not the raw API key.
- Real private profiles must stay outside the repository.
- The app remains local-first and web-only for v1.
- Do not add auto-apply, LinkedIn automation, email sending, cloud deployment, auth, or LangGraph.
