# SESSION_NOTES.md

Purpose: short handoff state for the next Codex/AI session. This is not product documentation.

Read first:
1. `AGENTS.md`
2. `SESSION_NOTES.md`
3. files directly related to the current task

---

## Current Stage

Move the project from file-based profile configuration to a managed local application setup.

The current app remains a local FastAPI/Jinja2 web application with manual intake, SQLite/Alembic persistence, fake/demo extraction, optional OpenAI extraction, Markdown CV variants, YAML fact-bank validation, safe fake tailoring, reports, exporters, review pages, safe artefact downloads, app data bootstrap, setup diagnostics, managed settings storage, a Settings UI for supported non-secret app settings plus OS keyring-backed OpenAI API key management, a Data Folder UI for connecting the app data root safely, and managed profile records for selecting existing file-based profile folders.

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

Implemented safe app data folder connection and creation through `/data-folder`. The UI now rejects broad or high-risk folder selections such as filesystem roots, home/Documents roots, repository paths, repository parents, and unrelated non-empty folders that are not recognisable app data folders. Existing `README.txt` files are preserved when connecting an existing folder.

### PR 7 — Managed profiles

Implemented the managed profiles foundation:
- app-managed `profiles` records live in `app_data_root/app.sqlite3`;
- `/profiles` lists connected file-based profiles, validates their folder status, connects existing profile folders, and activates one managed profile;
- active managed profiles are preferred for effective config loading and setup diagnostics;
- existing `.env`, managed settings default profile values, YAML config, Markdown CV variants, and YAML fact bank fallback remain compatible when no managed profile is active;
- profile application history remains in each profile-specific `applications.sqlite3`.

Non-goals preserved:
- no managed CV model yet;
- no import tools;
- no CV/fact editor;
- no pipeline migration to DB-backed CV/fact storage;
- no automatic profile application database migration;
- no URL scraping, auto-apply, LinkedIn automation, email sending, cloud deployment, auth, payments, or LangGraph.

Remaining risks:
- setup status is still diagnostic; it does not repair missing profile files or run profile migrations;
- if the host OS keyring backend is missing or unavailable, Settings reports a safe keyring error and `OPENAI_API_KEY` remains the developer fallback;
- database readiness checks verify tables/schema but do not yet provide a guided repair or migration button;
- profile and data folder UIs use text path inputs for this local developer release and do not provide OS-native folder pickers.

## Next Implementation Plan

### PR 8 — Managed CV model

Goal:
Add the first managed CV data model while preserving the current file-based pipeline until an explicit migration step.

Recommended scope:
- design managed CV variants, sections, blocks, facts, and aliases in app-managed storage;
- keep imports/export compatibility explicit and safe;
- do not auto-migrate private profile application history;
- keep generated artefacts and existing pipeline behaviour stable unless the PR explicitly changes them.

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
