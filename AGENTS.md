# AGENTS.md

Stable instructions for agents working on this local FastAPI/Jinja2 application.

## Product direction

The product is AI JOB APPLICATION ASSISTANT: a local-first Resume Builder and AI Tailoring assistant. SQLite is the source of truth for user-managed data. YAML and Markdown are not runtime sources of truth. Markdown may exist only as an optional export format.

The core flow is:

```text
Active profile -> structured resume -> job description -> extracted requirements -> structured AI change proposals -> human review/edit -> approved snapshot -> private contact layer at render time -> PDF/DOCX export and cover letter -> copy/download/manual tracking
```

The application is not an auto-apply bot. Do not add automatic applications, LinkedIn automation, email sending, broad job scraping, cloud multi-user auth, payments, fake ATS scores, or hidden background submissions.

## Engineering rules

- Work in English for code, comments, docs, UI, tests, PR text, and completion reports.
- Keep routes thin: routes call services; services call repositories, SQLAlchemy models, LLM clients, exporters, or artifact boundaries.
- Store all normal product data in one app-level SQLite database under the selected app data folder.
- Store the active profile as app-level SQLite settings and validate that it points to an existing `PersonProfile`.
- Dashboard and Application are scoped to the active profile. Settings remains available without an active profile.
- Store OpenAI API keys through the OS keyring boundary, never in SQLite and never in templates.
- Tests must not call real OpenAI and must not touch the real OS keyring.
- Private contact details must be excluded from AI prompt builders by default.
- Private contact details are added only during final rendering/export.
- AI tailoring must return structured proposals only. Never apply LLM output directly to the base resume.
- Every proposal must go through review and be accepted, accepted as edited, or rejected before final export.
- Prompt-template user instructions must never override protected safety rules: no fabrication, untrusted job posting, private contact exclusion, and structured output.
- Copy/download means likely applied only. Do not claim definite submission unless the user manually marks the application as applied.
- Export uses approved snapshot content and adds private contact data only during final rendering/export.
- Fact links are configurable. When required, AI must not strengthen claims without active verified facts.
- If schema changes, keep deterministic initialisation or migrations explicit, idempotent, tested, and documented.

## Required reading before tasks

1. `AGENTS.md`
2. `SESSION_NOTES.md`
3. `README.md` when product behaviour, UI, or docs are affected
4. Directly related source files

If these documents conflict with stale source code, prefer the current architecture described here and in `SESSION_NOTES.md` and `README.md`.

## Validation

Before completion, run when possible:

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
uv run pre-commit run --all-files
```

## Commit format

Use emoji plus conventional commit style:

```text
✨ feat(app): consolidate profile-first application workflow

- optional detail
```

## First-release implementation notes

- Use `app/core/errors.py` domain errors for expected user-facing workflow failures instead of bare `ValueError` in new code.
- Keep prompt safety guardrails internal to prompt builders; do not expose protected rules as editable UI fields.
- Resume uploads are local artifacts only and must not be sent to AI automatically.
- Empty builder sections should guide the user, but empty final render/export sections should be hidden.

## First-release fix-up update

- Existing local SQLite databases are repaired idempotently at startup for the first MVP release. Missing SQL-first columns and first-release tables are added explicitly so older databases do not crash on facts, Adapt, uploads, prompt scopes, or application events.
- The active-profile workflow remains the boundary for Dashboard, Application, CV Builder, facts, and resume selection. Settings remains available without an active profile.
- Dashboard activity supports 10, 20, and 30 day ranges via the `days` query parameter and uses hover titles for exact counts.
- Navigation is Dashboard / Application / CV Builder, with Settings in the right-side tools area beside the active profile selector.
- Settings uses a left-menu/right-panel layout for profiles, CV Builder, prompt templates, app configuration, OpenAI/keyring, exports, AI policy, data folder, and safety/privacy.
- OpenAI API keys stay in the OS keyring boundary and are not stored in SQLite. OpenAI model IDs are configurable non-secret settings with environment defaults.
- The data-folder UI uses a path input and validation/create-if-missing flow. A native OS folder picker is not available in this server-rendered local web UI yet.
- Prompt-template scoping is global/profile/resume/section. Users select named objects from the UI; internal privacy and anti-fabrication guardrails stay hidden and non-editable.
- Resume uploads store PDF/DOC/DOCX files locally as reference artifacts only. Full parsing is not implemented yet, and invalid uploads are rejected before creating resume data.
- Resume Builder block forms are type-specific, and Summary/Skills internal blocks do not show irrelevant move or subsection controls.
