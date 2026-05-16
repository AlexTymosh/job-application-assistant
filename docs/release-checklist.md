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
