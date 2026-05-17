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

## Post-PR #91 first-release polish checklist

- [ ] Repaired legacy databases create new applications/events with current timestamps, and Dashboard includes them in 10/20/30 day charts and recent ordering.
- [ ] Dashboard chart shows date X-axis labels, count Y-axis labels, hover date/count titles, and no likely/manual applied metric cards.
- [ ] Header profile selector remains accessible but does not visibly render “Active profile”.
- [ ] Settings Export formats can be saved with all formats off.
- [ ] Settings AI policy defaults can be saved with all flags off.
- [ ] OpenAI Settings links use a new tab with `noopener noreferrer`.
- [ ] Data folder is managed from Settings -> Data folder, and `/data-folder` redirects there.
- [ ] Individual and bulk application deletion are profile-scoped and do not delete resumes/profiles.
- [ ] Profile deletion requires typed confirmation, removes dependent records/files where safe, clears active profile when necessary, and preserves other profiles.
- [ ] CV Builder/base resume PDF and DOCX exports work without an application and without AI calls.
- [ ] Resume builder compact styling preserves edit/add/bullet/move/prompt/export controls.
