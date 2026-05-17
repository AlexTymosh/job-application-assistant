# Release Checklist

## Automated checks

- [ ] `uv run ruff format .`
- [ ] `uv run ruff check .`
- [ ] `uv run pytest`
- [ ] `uv run pre-commit run --all-files`

## Manual checks

- [ ] Complete the manual smoke test.
- [ ] Confirm tests do not call real OpenAI.
- [ ] Confirm tests do not touch the real OS keyring.
- [ ] Confirm raw OpenAI API keys are not stored in SQLite.
- [ ] Confirm private contact details are excluded from AI prompts.
- [ ] Confirm private contact details are added only at final export/render time.
- [ ] Confirm artifact paths are relative.
- [ ] Confirm traversal downloads are rejected.
- [ ] Confirm Dashboard is active-profile scoped.
- [ ] Confirm Application resume selector only lists active-profile resumes.
- [ ] Confirm application history is profile-scoped.
- [ ] Confirm copy/download tracking creates events and uses likely-applied semantics.
- [ ] Confirm Mark as applied creates a manual applied event.
- [ ] Confirm prompt-template edits do not remove protected safety rules.

## Product constraints

- [ ] No automatic job application submission.
- [ ] No LinkedIn automation.
- [ ] No email sending.
- [ ] No broad job scraping.
- [ ] No fake ATS score.
- [ ] No YAML or Markdown runtime source of truth.
- [ ] No raw OpenAI API key persisted in SQLite.

## First-release hardening checklist

- [ ] Facts page works with and without an active profile.
- [ ] Application routes require an active profile and block wrong-profile access.
- [ ] Adapt succeeds for a valid active-profile resume and rejects another profile's resume.
- [ ] Snapshot creation shows friendly errors when tailoring or accepted proposals are missing.
- [ ] Existing snapshot reuse is clear for the same tailoring run.
- [ ] Error pages include status code, safe message, Dashboard, Application, Settings, and Back navigation.
- [ ] Work Experience supports role, company, dates, current state, and bullets.
- [ ] Final render hides empty sections and uppercases section headings.
- [ ] Prompt UI exposes scoped user instructions but not editable protected safety rules.
- [ ] Uploads allow PDF/DOC/DOCX only and store files under app-owned upload artifacts.
- [ ] Profile forms do not show Location.

## First-release fix-up notes

- Startup includes an explicit idempotent SQLite schema repair bridge for older local MVP databases. It creates missing model tables via metadata and repairs safe missing columns, including fact claim/evidence metadata and prompt-template scope columns.
- The active profile remains the workflow boundary for Dashboard, Application, CV Builder, resumes, and facts. Settings remains accessible without an active profile.
- Header navigation is Dashboard / Application / CV Builder, with Settings and the active-profile selector on the right. The project link points to `https://github.com/AlexTymosh/job-application-assistant`.
- Dashboard activity supports 10, 20, and 30 day ranges with hoverable server-rendered count bars.
- Settings uses a left-menu/right-panel layout. OpenAI API keys are stored in OS keyring only; model IDs are configurable SQLite/env settings, not secrets. Data-folder selection uses path input/validation because a native folder picker is not available in this server-rendered local UI.
- Prompt instructions are scoped by selected global/profile/resume/section objects instead of raw ID-only typing. Protected prompt guardrails stay internal and non-editable.
- Resume uploads are local reference artifacts for PDF/DOC/DOCX only and are validated before resume creation. Uploaded resume parsing remains out of scope for the first release.
- Resume Builder uses compact controls and type-specific block forms. Summary and skills avoid irrelevant move/sub-block controls; work experience uses month fields for CV periods.

## Current first-release polish update

- Dashboard activity uses a server-rendered chart with a date X axis, application-count Y axis, hover titles, and 10/20/30 day range links. The likely-applied and manually marked applied metric cards are no longer displayed.
- Settings split forms are section-scoped. Export formats and AI policy defaults can be saved with every checkbox unchecked; unrelated Settings forms preserve existing values.
- Data folder is managed from Settings -> Data folder with path validation/create flow and reset-to-default support. `/data-folder` redirects to `/settings?section=data-folder`.
- CV Builder and the full resume builder can export the current base resume as PDF or DOCX under the app-owned artifacts directory without creating an application and without calling AI.
- Profile detail supports deleting one application, applications older than N days, all profile applications, and the profile itself. Destructive profile deletion requires typing the profile display name and clears the active profile when needed.
- The SQLite repair bridge avoids permanent `1970-01-01` timestamp defaults for repaired timestamp columns; new ORM-created rows use current UTC-naive timestamps so repaired databases still drive Dashboard charts and recent ordering correctly.

### Manual smoke additions

1. Start from an older SQLite database missing `applications.created_at`, run startup, create a new application, and confirm its created date is current and appears in Dashboard 10/20/30 day charts.
2. In Settings -> Export formats, uncheck every checkbox and save; confirm all formats are off. Repeat for Settings -> AI policy defaults.
3. In Settings -> Data folder, save a valid local path, confirm it is created/selected, then use the default-folder action.
4. Create an application, delete it from the profile detail cleanup section, and confirm Dashboard counts update while the resume/profile remain.
5. Delete a test profile by typing its display name and confirm dependent resumes, facts, applications, and scoped prompt templates are removed and the active profile is cleared if applicable.
6. Export a base resume from CV Builder as PDF and DOCX and confirm both downloads work without an application.
