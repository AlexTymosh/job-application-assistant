# SQL-first Architecture

SQLite is the source of truth for runtime user-managed data. The clean pre-release schema is initialised by SQLAlchemy metadata at startup.

Core tables:

- `person_profiles` and `profile_contacts`
- `master_cvs` and `master_cv_entries`
- `resumes`, `resume_sections`, and `resume_blocks`
- `applications`, `tailored_resumes`, and `application_events`
- `prompt_templates`, `app_settings`, uploads, cover letters, and artifacts

The previous development schema repair bridge has been removed. Existing pre-release development databases can be deleted and recreated when schema changes.

## Master CV source-material contract

`master_cv_entries` may contain legacy categories from pre-release data, but AI payload builders allow only `summary`, `skills`, `work_experience`, and `education`. Header/contact, Languages, Certificates, References, and legacy singular `reference` rows are hidden from Master CV UI pages and ignored for tailoring and cover-letter payloads even if they remain in SQLite. Because the app is pre-release, recreating the local SQLite database is acceptable if users want to remove old private Master CV rows completely.

Header Website URL is stored in Resume Header block metadata, so no schema change is required for the optional Website field.

## Active-profile isolation contract

Application creation verifies that the selected `base_resume_id` belongs to the active profile before inserting an Application. Application review, save, export, and download routes verify `application.profile_id` against the active profile before returning data. The Applications list never falls back to a global query when no active profile is selected.

Master CV page, edit, and delete routes require the active profile workspace and verify that each entry belongs to that profile's Master CV.
