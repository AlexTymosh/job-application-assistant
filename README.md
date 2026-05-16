# Local Resume Builder and AI Tailoring Assistant

This is a local-first FastAPI/Jinja2 application for building structured resumes, tailoring them to job descriptions, reviewing AI-suggested changes, and exporting final application documents.

The product flow is simple:

```text
Create profiles and resumes -> paste a job -> extract requirements -> receive reviewed AI change proposals -> approve changes -> export a final resume and cover letter
```

## What it does

- Stores user-managed data in one app-level SQLite database under the selected app data folder.
- Lets users create multiple person profiles.
- Lets each profile own multiple structured resumes.
- Builds resumes from sections, blocks, and bullets.
- Stores facts and evidence for conservative tailoring.
- Lets users configure which resume content AI may edit.
- Extracts job requirements from pasted job descriptions.
- Creates structured AI change proposals instead of uncontrolled full-document rewrites.
- Shows before/after review and stores accepted or rejected decisions.
- Creates a tailored resume snapshot from accepted changes only.
- Adds private contact details only during final rendering/export.
- Exports PDF and DOCX by default, with optional Markdown and HTML user-facing exports.
- Generates cover letters through a separate prompt boundary.

## What it does not do

- It does not submit job applications automatically.
- It does not automate LinkedIn, email, WhatsApp, or Telegram.
- It does not scrape job sites broadly.
- It does not provide fake ATS scores.
- It does not store raw OpenAI API keys in SQLite.
- It does not use YAML or Markdown files as the user source of truth.

## Quickstart

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Open the local web app and start with:

1. `/data-folder` to confirm the app data folder.
2. `/settings` to configure export formats, AI policy defaults, and the OpenAI keyring entry if needed.
3. `/profiles` to create a person profile.
4. `/profiles/{profile_id}/resumes` to create resumes.
5. `/applications/new` to paste a job description and start tailoring.

## Architecture

The preferred layering is:

```text
routes -> services -> SQLAlchemy models / LLM clients / exporters / artifact boundary
```

The database contains settings, profiles, private contacts, resumes, sections, blocks, bullets, facts, fact links, applications, extracted requirements, tailoring runs, AI proposals, snapshots, cover letters, and artifact metadata.

## Privacy and AI safety

Private contact data such as email, phone, and address is stored locally but excluded from prompt builders by default. Prompt builders receive only AI-safe resume content, editable targets, allowed facts, job requirements, and editing policy.

Job postings are treated as untrusted data. AI prompts instruct the model to extract or compare facts only and never follow instructions embedded in job text.

## Testing

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
uv run pre-commit run --all-files
```
