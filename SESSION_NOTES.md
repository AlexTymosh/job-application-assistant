# SESSION_NOTES.md

Purpose: short handoff state for the next Codex/AI session. This is not product documentation.

Read first:
1. `AGENTS.md`
2. `SESSION_NOTES.md`
3. files directly related to the current task

---

## Current Stage

Move the project from file-based profile configuration to a managed local application setup.

The current app already works as a local FastAPI/Jinja2 web application with:
- manual job intake;
- SQLite/Alembic persistence;
- fake/demo extraction mode;
- optional OpenAI extraction mode;
- CV loading from Markdown variants;
- fact-bank validation from YAML;
- fake safe tailoring;
- Evidence Matrix and CV Match Report;
- Markdown, HTML, PDF, and DOCX export foundations;
- safe artefact download routes.

The next work should improve product usability, not add more LLM features.

---

## Immediate Goal

Add a local app setup/settings foundation so users do not edit `config.yaml` manually.

Target behaviour:
- first launch creates or connects an app data folder;
- missing setup redirects the user to `/setup`;
- settings are editable in the web UI;
- durable user data lives outside the repository;
- API keys are not stored in YAML or committed files.

---

## Key Decisions

- Default app data folder should be visible and user-owned:
  `Documents/JobApplicationAssistant/`
- User should be able to connect an existing data folder.
- SQLite should become the primary source of app/profile settings.
- YAML should remain as example/import/export/fallback only, not the main UI-facing settings store.
- OpenAI API key should use OS keyring as the preferred storage backend.
- SQLite may store secret metadata only, not the raw API key.
- Real private profiles must stay outside the repository.
- The app remains local-first and web-only for v1.
- Do not add auto-apply, LinkedIn automation, email sending, cloud deployment, auth, or LangGraph.

---

## Known Documentation Conflict

`AGENTS.md` currently says settings must be stored in profile `config.yaml`.

This is now outdated for the next architecture.

Next documentation update must change that rule to:
- current compatibility layer: `config.yaml`;
- target source of truth: managed settings in SQLite;
- secrets: OS keyring preferred;
- YAML: example/import/export/fallback only.

Do not silently implement settings changes without updating `AGENTS.md` and `README.md`.

---

## Next Implementation Plan

### PR 1 — App data directory bootstrap

Goal:
Create an application-owned data folder foundation.

Add:
- `app/storage/__init__.py`
- `app/storage/app_dirs.py`
- `app/storage/bootstrap.py`
- `tests/test_app_dirs.py`
- `tests/test_storage_bootstrap.py`

Expected behaviour:
- default path resolves to `Documents/JobApplicationAssistant`;
- `APP_DATA_DIR` can override the default;
- bootstrap creates root folders:
  - `profiles/`
  - `logs/`
  - `backups/`
- no private data is created inside the repository.

Dependency:
- add `platformdirs>=4.3,<5.0`

Do not:
- migrate CV data yet;
- add settings UI yet;
- add keyring yet.

Commit:
`✨ feat(storage): add app data directory bootstrap`

---

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

### PR 3 — Managed settings storage

Goal:
Store editable app settings in SQLite.

Add:
- `app/settings/__init__.py`
- `app/settings/models.py`
- `app/settings/repositories.py`
- `app/settings/service.py`
- Alembic migration for `app_settings`
- `tests/test_settings_repository.py`
- `tests/test_settings_service.py`

Settings to support first:
- `llm_extraction_mode`
- `require_human_approval_before_export`
- `export_markdown`
- `export_html`
- `export_pdf`
- `export_docx`
- `default_profile_name`

Rules:
- DB settings override YAML/defaults.
- YAML remains compatibility fallback only.
- Do not store secrets in app_settings.

Commit:
`✨ feat(settings): add managed settings storage`

---

### PR 4 — Settings UI

Goal:
Allow settings to be edited from the web app.

Add:
- `app/api/routes_settings.py`
- `app/web/templates/settings.html`
- `tests/test_settings_routes.py`

UI fields:
- LLM extraction mode: fake/openai;
- require human approval before final export;
- enabled export formats;
- default profile;
- OpenAI model name fields if still needed.

Rules:
- validate before saving;
- show clear errors;
- keep routes thin;
- no OpenAI calls from routes.

Commit:
`✨ feat(settings): add editable settings page`

---

### PR 5 — Secret storage with OS keyring

Goal:
Store OpenAI API key outside YAML/SQLite plaintext.

Add:
- `app/secrets/__init__.py`
- `app/secrets/store.py`
- `app/secrets/service.py`
- `app/api/routes_secrets.py`
- `app/web/templates/secrets.html`
- `tests/test_secret_service.py`
- `tests/test_secret_routes.py`

Dependency:
- add `keyring>=25.0,<26.0`

Rules:
- OS keyring is preferred storage.
- SQLite stores only metadata such as:
  - provider
  - secret_name
  - storage_backend
  - is_configured
- tests must use fake keyring backend.
- never print or return the full API key.

Commit:
`✨ feat(secrets): store OpenAI API key in OS keyring`

---

### PR 6 — Data folder connection UI

Goal:
Allow user to create or connect an existing data folder.

Add:
- `app/api/routes_storage.py`
- `app/web/templates/storage.html`
- `tests/test_storage_routes.py`

Behaviour:
- show current app data path;
- allow entering a new path manually;
- validate the path;
- create folder if requested;
- do not delete existing data;
- do not move data automatically in this PR.

Commit:
`✨ feat(storage): add app data folder connection UI`

---

## Later Plan

After storage/setup/settings are stable:

1. Managed profiles table and profile UI.
2. Managed CV model:
   - variants;
   - aliases;
   - sections;
   - blocks;
   - facts;
   - block-to-fact links.
3. Import current Markdown CV and `fact_bank.yaml` into managed storage.
4. CV/fact editor UI.
5. Pipeline reads managed CV data from DB, with file-based fallback for example profiles.

Do not start these until PR 1–6 are complete.

---

## Current Risks

- `README.md` and `AGENTS.md` still describe a mostly file-based configuration model.
- Current `SESSION_NOTES.md` used to contain too much completed history; keep this file short.
- Human approval flow for final PDF/DOCX may still need UX hardening.
- File writes and SQLite transactions are not fully atomic.
- Real OpenAI tailoring is not implemented and should not be added until managed settings/secrets are stable.

---

## Validation Commands

Before each merge:

```powershell
uv lock
uv sync --locked --group dev
uv run ruff format .
uv run ruff check .
uv run pytest
uv run pre-commit run --all-files
git status --short
```

Private files must not appear in git status:
- `.env`
- real CV files
- generated artefacts
- SQLite databases
- private profile folders

---

## Current Next Codex Task

Implement PR 1 only:

`App data directory bootstrap`

Use `Documents/JobApplicationAssistant` as the default app data root, support `APP_DATA_DIR` override, create required folders, add tests, and update `AGENTS.md`/`README.md` only where necessary to document the new direction.

Do not implement setup redirect, settings UI, keyring, managed profiles, or managed CV in this PR.
