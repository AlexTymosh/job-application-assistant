# AGENTS.md

Stable instructions for agents working on this local FastAPI/Jinja2 application.

## Product direction

The product is AI JOB APPLICATION ASSISTANT: a local-first CV Builder and AI Tailoring assistant. SQLite is the source of truth for user-managed data. YAML and Markdown are not runtime sources of truth. Markdown may exist only as an optional export/rendering format.

The core flow is:

```text
Profile -> Master CV / Extended Experience -> Resume Variants -> Job Application -> AI tailoring -> saved Tailored Resume -> PDF/DOCX export
```

The application is not an auto-apply bot. Do not add automatic applications, LinkedIn automation, email sending, broad job scraping, cloud multi-user auth, payments, fake ATS scores, or hidden background submissions.

## Engineering rules

- Work in English for code, comments, docs, UI, tests, PR text, and completion reports.
- Keep routes thin: routes call services; services call repositories, SQLAlchemy models, LLM clients, exporters, or artifact boundaries.
- Store all normal product data in one app-level SQLite database under the selected app data folder.
- Store the active profile as app-level SQLite settings and validate that it points to an existing `PersonProfile`.
- Dashboard, Application, CV Builder, Master CV, and Resume Variants are scoped to the active profile. Settings remains available without an active profile.
- Store OpenAI API keys through the OS keyring boundary, never in SQLite and never in templates.
- Tests must not call real OpenAI and must not touch the real OS keyring.
- Private contact details must be excluded from AI prompt builders by default.
- Private contact details are added only during final rendering/export.
- Master CV is the user's local extended experience source. It is not external fact-checking.
- AI tailoring uses the selected Resume Variant as the base and Master CV as source material.
- AI must not invent employers, dates, degrees, certificates, education, metrics, or private contact data.
- AI may edit Summary, Skills, Work Experience key bullets, and Education achievements by default.
- Header, Languages, Certificates, and References are not AI-editable by default.
- Prompt-template user instructions must never override internal safety rules.
- Copy/download means likely applied only. Do not claim definite submission unless the user manually marks the application as applied.
- Export uses base Resume Variant or saved Tailored Resume content and adds private contact data only during final rendering/export.
- If schema changes, keep deterministic initialisation explicit, idempotent, tested, and documented. The app is pre-release, so old development databases may be deleted/recreated instead of migrated.

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


## Current first-release notes

- The old user-facing facts/evidence workflow has been replaced with Master CV / Extended Experience terminology.
- Startup initialises a clean SQL-first schema; legacy development schema repair code is intentionally removed.
- CV Builder uses a left-navigation, central-editor, right-preview layout.
- Master CV is restricted to AI source material only: Summary, Skills, Work Experience key bullets, and Education key bullets. Header, Languages, Certificates, and References belong to Resume Builder only and are excluded from AI payloads by an allow-list.
- Base Resume Variant and Tailored Resume PDF/DOCX exports are available without automatic job submission. DOCX exports use Heading 1/2/3 styles with WORK EXPERIENCE as the work section heading, and exports render email, LinkedIn, GitHub, website, and reference LinkedIn links where present, including PDF reference links where ReportLab supports them.
- Settings profile actions use compact rows with typed delete confirmation. Dashboard chart and activity bars use flat muted colours, not gradients.

## PR #94 fix-up notes

- Keep application routes active-profile scoped. Never load, adapt, export, or download applications across profiles.
- Master CV should visually follow the CV Builder layout. Do not reintroduce a generic admin-card layout for Extended Experience.
- Tailored Resume review shows generated cover letter output, not raw Markdown editing.
- Styled DOCX/PDF export should be generated from structured resume content where possible.
