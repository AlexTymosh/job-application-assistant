# Session Notes

## Current stage

The application has been reset to a SQL-first local Resume Builder and AI Tailoring architecture.

## Changed

- Added a clean app-level SQLite schema for settings, person profiles, private contacts, resumes, sections, blocks, bullets, facts, applications, requirements, tailoring runs, AI proposals, snapshots, cover letters, and artifacts.
- Replaced file-profile runtime assumptions with person profiles managed in the web UI.
- Added deterministic fake job extraction, tailoring, and cover letter clients for tests and demo use.
- Added prompt builders for summary blocks, work-experience bullets, skills sets, title edits, custom descriptions, and cover letters.
- Added a review flow that persists accepted and rejected AI change proposals.
- Added snapshot/export flow that applies accepted changes only and adds private contact data at render/export time.
- Added settings for export formats and default AI policies.
- Rebuilt documentation around the SQL-first product model.

## Removed

- Legacy profile-folder examples and import-first flow.
- YAML profile configuration as product storage.
- YAML fact bank as product storage.
- Markdown resume variants as product storage.
- Profile-specific application database assumptions.

## Remaining risks

- The current UI is intentionally simple and server-rendered; reorder controls are basic and should be expanded.
- The initial schema is deterministic via SQLAlchemy metadata creation; future releases should add versioned upgrade migrations before real user data exists.
- Real OpenAI clients remain behind boundaries and need a production-hardening pass before enabling non-fake mode.
- PDF and DOCX exports use one conservative style.

## Recommended next steps

1. Add richer edit forms for every section, block, bullet, and fact field.
2. Add explicit drag/reorder or move-up/move-down controls.
3. Add DB-backed prompt template editing.
4. Add more proposal validation around claim strengthening and fact ownership.
5. Add visual diff highlighting on the review page.
