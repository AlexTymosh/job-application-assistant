# SQL-first Architecture

SQLite is the source of truth for runtime user-managed data. The clean pre-release schema is initialised by SQLAlchemy metadata at startup.

Core tables:

- `person_profiles` and `profile_contacts`
- `master_cvs` and `master_cv_entries`
- `resumes`, `resume_sections`, and `resume_blocks`
- `applications`, `tailored_resumes`, and `application_events`
- `prompt_templates`, `app_settings`, uploads, cover letters, and artifacts

The previous development schema repair bridge has been removed. Existing pre-release development databases can be deleted and recreated when schema changes.
