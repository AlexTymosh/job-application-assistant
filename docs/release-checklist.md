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
