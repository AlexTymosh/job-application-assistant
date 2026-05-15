# SESSION_NOTES.md

Purpose: short handoff state for the next Codex/AI session. This is not product documentation.

Read first:
1. `AGENTS.md`
2. `SESSION_NOTES.md`
3. files directly related to the current task

---

## Current Stage

Move the project from file-based profile configuration to a managed local application setup.

The current app remains a local FastAPI/Jinja2 web application with manual intake, SQLite/Alembic persistence, fake/demo extraction, optional OpenAI extraction, managed CV/fact pipeline loading with Markdown/YAML fallback, safe fake tailoring, reports, exporters, review pages, safe artefact downloads, app data bootstrap, setup diagnostics, managed settings storage, a Settings UI for supported non-secret app settings plus OS keyring-backed OpenAI API key management, a Data Folder UI for connecting the app data root safely, managed profile records for selecting existing file-based profile folders, the app-managed CV storage model, previewable Markdown/YAML import tools, and simple managed CV/fact editor pages.

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

Implemented safe app data folder connection and creation through `/data-folder`. The UI now rejects broad or high-risk folder selections such as filesystem roots, home/Documents roots, repository paths, repository parents, and unrelated non-empty folders that are not recognisable app data folders. Existing non-empty folders require strong app-data evidence: the README marker, a current readable `app.sqlite3`, or the complete `profiles/`, `logs/`, and `backups/` structure. Existing `README.txt` files are preserved when connecting an existing folder.

### PR 7 — Managed profiles

Implemented the managed profiles foundation:
- app-managed `profiles` records live in `app_data_root/app.sqlite3`;
- `/profiles` lists connected file-based profiles, validates their folder status and config identity, connects existing profile folders, and permits activation repair actions while setup is incomplete;
- active managed profiles are preferred for effective config loading and setup diagnostics;
- existing `.env`, managed settings default profile values, YAML config, Markdown CV variants, and YAML fact bank fallback remain compatible when no managed profile is active;
- profile application history remains in each profile-specific `applications.sqlite3`.
- Effective config loading revalidates active managed profile identity before using it.

### PR 8 — Managed CV model

Implemented the app-managed CV storage foundation:
- app settings schema version 3 adds app-level tables for CV variants, variant aliases, sections, blocks, facts, and block-fact links in `app_data_root/app.sqlite3`;
- managed CV SQLAlchemy models use `SettingsBase` and stay out of the profile application database metadata;
- repository operations create/list managed CV records and return Pydantic records rather than raw SQLAlchemy rows;
- duplicate variant names, aliases, fact keys, and block-fact links have explicit domain errors;
- profile deletion cascades managed CV records through app-level foreign keys;
- profile database setup readiness now verifies expected columns, not only table names, without creating or migrating tables during diagnostics;
- existing Markdown CV variants, YAML fact banks, selectors, and local pipeline behaviour remain unchanged.

Non-goals preserved:
- no import tools;
- no CV/fact editor;
- no pipeline migration to DB-backed CV/fact storage;
- no automatic profile application database migration;
- no URL scraping, auto-apply, LinkedIn automation, email sending, cloud deployment, auth, payments, or LangGraph.

Remaining risks:
- setup status is still diagnostic; it does not repair missing profile files or run profile migrations;
- if the host OS keyring backend is missing or unavailable, Settings reports a safe keyring error and `OPENAI_API_KEY` remains the developer fallback;
- database readiness checks verify expected tables and columns but do not yet provide a guided repair or migration button;
- profile and data folder UIs use text path inputs for this local developer release and do not provide OS-native folder pickers.

### PR 9 — Import tools

Completed safe import tools for existing active managed file-based profiles:

- `/profiles/import` renders a simple preview/apply UI;
- Markdown CV variants are loaded with existing Markdown and section parsers, then imported into managed variants, sections, and one deterministic `imported_content` block per section;
- YAML fact banks are loaded with the existing fact-bank validator, then imported into managed facts;
- previews perform no writes, report planned creates/skips/conflicts, avoid showing unnecessary absolute paths in the normal UI, reject empty or ambiguous CV sources, and block apply when conflicts exist;
- apply uses one SQLAlchemy transaction, is idempotent for matching records, does not overwrite conflicts, and writes only to `app_data_root/app.sqlite3`;
- source Markdown/YAML files, profile `applications.sqlite3`, current file-based pipeline loading, and block-fact links remain unchanged.

Non-goals preserved:

- no CV/fact editor UI;
- no pipeline migration to DB-backed CV/fact storage;
- no automatic profile application database migration;
- no automatic block-fact links;
- no URL scraping, auto-apply, LinkedIn automation, email sending, cloud deployment, auth, payments, or LangGraph.

Remaining risks:

- imports currently create one coarse block per parsed Markdown section; finer block splitting remains out of scope;
- conflicts require manual resolution outside the import tool because destructive overwrite is intentionally not implemented.

### PR 10 — CV/fact editor UI

Completed simple managed CV/fact editor screens on top of existing managed storage:

- `/profiles/cv` lists active-profile managed variants and facts summary, with clear empty-state links to Profiles, Import CV/Facts, and Facts;
- `/profiles/cv/variants/{variant_id}` lists sections and blocks in deterministic order;
- `/profiles/cv/blocks/{block_id}/edit` edits block Markdown, display order, enabled state, and selected same-profile fact links;
- `/profiles/facts` lists active-profile facts only;
- `/profiles/facts/new` and `/profiles/facts/{fact_id}/edit` create and edit managed facts with enum validation, immutable fact keys on edit, duplicate-key rejection, and active-state support;
- editor writes remain limited to app-level managed CV storage in `app_data_root/app.sqlite3`; source Markdown CV files, source YAML fact-bank files, profile `applications.sqlite3`, OpenAI, secrets, and the current file-based pipeline are not touched.

Non-goals preserved:

- no automatic splitting of imported coarse `imported_content` blocks;
- no hard delete flows; blocks use `is_enabled` and facts use `is_active`;
- no pipeline migration to DB-backed CV/fact storage;
- no automatic profile application database migration;
- no URL scraping, auto-apply, LinkedIn automation, email sending, cloud deployment, auth, payments, or LangGraph.

Remaining risks:

- imported CV sections are still coarse blocks, so the editor can modify only those imported block units until a later refinement;
- managed block-fact links are captured for future claim integrity, but the active pipeline does not consume them yet;
- safe repair guidance for missing app settings storage remains minimal.

### PR 11 — Pipeline migration

Completed managed CV/fact pipeline source migration:

- added a testable pipeline CV source loader that resolves the selected CV variant and facts from app-managed storage when a valid active managed profile source exists;
- composed managed Markdown from active variants, deterministic sections, and enabled blocks while preserving the required section marker contract used by `parse_cv_sections()`;
- converted active managed facts into the existing `FactBank` model using `fact_key` as the stable pipeline/report fact id;
- added an active managed profile identity guard so the pipeline cannot combine one profile's application database with another profile's managed CV/fact records;
- validated selected managed sources clearly: missing selected variants, missing required sections, required sections without enabled content, no active facts, and inactive or stale block-fact links fail without silent file fallback;
- preserved deterministic file-based Markdown/YAML fallback when no active managed profile exists or the active managed profile has no managed CV variants yet;
- updated `LocalApplicationPipelineService` to consume the new source loader and emit `pipeline_cv_source_loaded` events;
- aligned setup diagnostics with effective pipeline source readiness;
- preserved source records: pipeline execution does not mutate managed CV/fact storage, source Markdown/YAML files, or profile `applications.sqlite3`.

Non-goals preserved:

- no PR 12 release polish;
- no backup/export profile flow;
- no automatic profile application database migration;
- no destructive deletion of managed CV/fact records;
- no real OpenAI tailoring;
- no URL scraping, auto-apply, LinkedIn automation, email sending, cloud deployment, auth, payments, or LangGraph.

Remaining risks:

- managed block-fact links are validated for profile/active-fact integrity, but full block-level claim filtering is intentionally deferred;
- imported CV sections may still be coarse `imported_content` blocks until a later refinement;
- setup repair guidance remains text-based and does not yet provide one-click repair flows.

## Next Implementation Plan

### PR 12 — Release polish

Recommended scope:

- improve user-facing setup and repair guidance for managed CV/fact readiness failures;
- harden release smoke tests and final review/export user flows;
- polish documentation and release checklist without changing the pipeline source architecture;
- preserve managed-first pipeline source precedence and file-based fallback compatibility.

Release polish progress:
- Added explicit human approval final export action for applications waiting for approval.
- The action generates PDF/DOCX final artefacts from the persisted Markdown review artefact.
- QA warning applications are blocked from final export until reviewed.
- Repeated approval/export attempts do not duplicate final artefact records.

Smoke-test polish completed:
- added release-smoke coverage for the managed user path: connect active managed profile, preview/apply import, inspect managed CV/fact editor pages, edit an imported managed block, run the local pipeline, and verify managed-source artefact output;
- updated manual smoke and release checklist docs so release validation covers the managed-first pipeline path, not only the legacy file-based flow;
- preserved file-based fallback compatibility and did not change production pipeline behaviour.

## Key Decisions

- Default app data folder should be visible and user-owned: `Documents/JobApplicationAssistant/`.
- Users can connect an existing app data folder through `/data-folder`; `APP_DATA_DIR` remains the highest-priority developer override.
- Supported app settings, managed profile records, managed CV records, import tools, editor workflows, and managed-first pipeline loading already live in SQLite; future work should focus on release polish and guided repair.
- YAML should remain as example/import/export/fallback only, not the main UI-facing settings store.
- OpenAI API key uses OS keyring as the preferred storage backend, with `OPENAI_API_KEY` retained as a developer fallback.
- SQLite may store secret metadata only, not the raw API key.
- Real private profiles must stay outside the repository.
- The app remains local-first and web-only for v1.
- Do not add auto-apply, LinkedIn automation, email sending, cloud deployment, auth, or LangGraph.
