# Session Notes

## Current stage

The first usable local release stage is completed for the SQL-first AI JOB APPLICATION ASSISTANT flow.

## Changed

- Updated the app shell to use the AI JOB APPLICATION ASSISTANT product name and a three-item main menu: Dashboard, Application, and Settings.
- Added a global active-profile workflow stored in SQLite app settings.
- Added active-profile display and selection in the header.
- Made the Dashboard active-profile scoped with resume/application counts, likely-applied metrics, manual applied metrics, recent applications, and a 30-day server-rendered activity chart.
- Turned Settings into a workspace hub for configuration, AI policies, profiles, CV Builder, facts, prompt templates, and privacy guidance.
- Added DB-backed prompt-template defaults and editable user instructions with protected safety rules.
- Added standard resume skeleton creation with Summary, Skills, Work Experience, Education, Languages, Certifications, and References.
- Improved the CV Builder page around structured sections, blocks, bullets, visibility badges, AI-edit badges, and move controls.
- Added a streamlined Application workflow that creates an application, extracts requirements, runs tailoring, and generates a cover letter in one Adapt action.
- Added application review with fit summary, editable tailored proposal text, accepted-edited status support, and editable cover letter storage.
- Added application events for creation, extraction, snapshots, exports, copy tracking, download tracking, likely applied, and manually marked applied.
- Preserved the privacy boundary where private contact details are excluded from prompts and snapshots but included at final export time.
- Expanded tests for active profile, dashboard metrics, prompt templates, standard skeletons, adaptation, copy/download/manual events, and route rendering.
- Updated user and architecture documentation for the profile-first release.

## Removed

- The old product title as the visible application name.
- Main navigation entries outside Dashboard, Application, and Settings.
- Global resume/application selection from the main Application workflow; the MVP now uses the active profile by default.

## Remaining risks

- Existing installations that already have an older SQLite schema still need a versioned migration strategy before real user data is relied on.
- CV Builder editing is intentionally server-rendered and basic; drag-and-drop and richer field-specific forms can be improved later.
- The fit summary is deterministic in fake mode and intentionally simple; real model integration should add stricter validation before non-fake use.
- Prompt-template integration is DB-backed and safety-preserving, but deeper per-template model prompt composition should be expanded in a later pass.
- Copy tracking depends on browser clipboard support; backend fallback forms remain available, but failed clipboard actions may not record events.

## Recommended next steps

1. Add versioned database migrations before distributing to users with persistent data.
2. Expand CV Builder edit forms with richer fact-link selection UI.
3. Add visual diff highlighting for before/after proposal review.
4. Add export buttons that create snapshots and artifacts in one guided action.
5. Harden real OpenAI client integration behind deterministic contract tests.

## Current hardening update

- Added domain error classes and friendly error rendering for expected workflow failures, HTTP errors, and unexpected exceptions.
- Hardened active-profile access for facts and application detail/mutation routes.
- Fixed first-release runtime failures around active-profile facts, Adapt, and approved snapshot creation.
- Reworked the Settings hub order and made active-profile facts a safe card action.
- Compactly polished the header, menu, active-profile selector, cards, buttons, textareas, and empty states.
- Removed Location from profile forms while leaving the legacy database column in place.
- Added resume metadata editing and optional safe PDF/DOC/DOCX upload storage under app-owned artifacts.
- Added scoped prompt instructions for global, profile, resume, and section levels while keeping safety guardrails internal and non-editable.
- Improved CV Builder controls with compact arrow move buttons and section-aware fields, including Work Experience role/company/date/current fields.
- Updated rendering to hide empty final sections and uppercase rendered section headings.
- Expanded regression coverage for facts, Adapt, snapshots, active-profile access, uploads, prompt resolution, error pages, work experience, metadata edits, and render behaviour.
