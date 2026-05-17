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

## First-release fix-up notes

- Startup includes an explicit idempotent SQLite schema repair bridge for older local MVP databases. It creates missing model tables via metadata and repairs safe missing columns, including fact claim/evidence metadata and prompt-template scope columns.
- The active profile remains the workflow boundary for Dashboard, Application, CV Builder, resumes, and facts. Settings remains accessible without an active profile.
- Header navigation is Dashboard / Application / CV Builder, with Settings and the active-profile selector on the right. The project link points to `https://github.com/AlexTymosh/job-application-assistant`.
- Dashboard activity supports 10, 20, and 30 day ranges with hoverable server-rendered count bars.
- Settings uses a left-menu/right-panel layout. OpenAI API keys are stored in OS keyring only; model IDs are configurable SQLite/env settings, not secrets. Data-folder selection uses path input/validation because a native folder picker is not available in this server-rendered local UI.
- Prompt instructions are scoped by selected global/profile/resume/section objects instead of raw ID-only typing. Protected prompt guardrails stay internal and non-editable.
- Resume uploads are local reference artifacts for PDF/DOC/DOCX only and are validated before resume creation. Uploaded resume parsing remains out of scope for the first release.
- Resume Builder uses compact controls and type-specific block forms. Summary and skills avoid irrelevant move/sub-block controls; work experience uses month fields for CV periods.

## Current first-release polish notes

- The SQLite compatibility bridge must not add permanent `1970-01-01` timestamp defaults for repaired timestamp columns. ORM-created rows use application-side UTC-naive timestamps so repaired databases create current `created_at`/`updated_at` values.
- Settings split forms use `settings_section` as the update boundary. Export and AI policy checkbox sections intentionally allow every checkbox to be unchecked; missing checkbox fields mean `false` only for the submitted section.
- Dashboard activity renders a server-side bar chart with date labels on the X axis, count labels on the Y axis, 10/20/30 day range links, and no likely-applied/manual-applied metric cards.
- The header keeps the active-profile selector accessible with `aria-label="Active profile"` but does not display the words “Active profile”.
- Data folder management lives in Settings -> Data folder. `/data-folder` is a compatibility redirect to that Settings section.
- Profile detail provides explicit destructive controls for deleting individual applications, deleting old/all applications for that profile, and deleting the profile after typed-name confirmation.
- CV Builder and the full resume builder can export the current base resume as PDF or DOCX under the app-owned artifacts directory without requiring an application.
