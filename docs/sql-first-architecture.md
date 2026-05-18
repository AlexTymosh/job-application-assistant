# SQL-first Architecture

SQLite is the source of truth for runtime user-managed data. The clean pre-release schema is initialised by SQLAlchemy metadata at startup.

Core tables:

- `person_profiles` and `profile_contacts`
- `master_cvs` and `master_cv_entries`
- `resumes`, `resume_sections`, and `resume_blocks`
- `applications`, `tailored_resumes`, `application_events`, `application_analyses`, and `cover_letters`
- `prompt_templates`, `app_settings`, uploads, and artifacts

The previous development schema repair bridge has been removed. Existing pre-release development databases can be deleted and recreated when schema changes.

## Master CV source-material contract

`master_cv_entries` may contain legacy categories from pre-release data, but Master CV enhanced payload builders allow only `summary`, `skills`, `work_experience`, and `education`. Header/contact, Languages, Certificates, References, and legacy singular `reference` rows are hidden from Master CV UI pages and ignored for tailoring and cover-letter payloads even if they remain in SQLite.

Variant-only mode does not load Master CV entries for AI payloads when **Use Master CV source material** is disabled.

Header Website URL is stored in Resume Header block metadata, so no schema change is required for the optional Website field.

## Resume and application content

Resume Builder stores user-entered CV sections in `resume_sections` and `resume_blocks`. The Header block metadata stores contact fields used only for preview and final rendering/export. Applications store pasted job text and the selected base resume. Tailored Resumes store structured JSON content and rendered Markdown generated from that structured content.

Fit Analysis output is stored in `application_analyses` with `analysis_type="fit_analysis"`. Cover Letters are stored in `cover_letters` and can be exported as TXT from the Tailored Resume review page.

## Settings and secrets

`app_settings` stores non-secret settings such as export defaults, AI policy defaults, `llm_mode`, active profile id, and OpenAI model identifiers. OpenAI API keys are stored through the OS keyring boundary only and must never be stored in `app_settings` or rendered in templates.

## Active-profile isolation contract

Application creation verifies that the selected `resume_id` belongs to the active profile before inserting an Application. Application review, export, cover-letter download, and Tailored Resume download routes verify `application.profile_id` against the active profile before returning data. The Applications list never falls back to a global query when no active profile is selected.

Resume Builder and base resume export routes verify that the resume belongs to the active profile. Master CV page, edit, and delete routes require the active profile workspace and verify that each entry belongs to that profile's Master CV.
