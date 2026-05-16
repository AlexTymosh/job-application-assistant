# AI JOB APPLICATION ASSISTANT

AI JOB APPLICATION ASSISTANT is a local-first FastAPI/Jinja2 web application for preparing job application materials without becoming an auto-apply bot.

The product flow is:

```text
Create a profile -> build resumes -> paste a job -> adapt the selected resume -> review and edit AI changes -> copy/download final content -> track likely applications
```

## What it does

- Stores user-managed data in one app-level SQLite database under the selected app data folder.
- Lets the user create multiple person profiles and select one global active profile.
- Lets each profile own several structured resume versions, such as Software Engineer, Automation Engineer, Data Analyst, or Backend Developer.
- Builds resumes from structured sections, blocks, and bullets.
- Creates optional standard CV sections: Summary, Skills, Work Experience, Education, Languages, Certifications, and References.
- Stores facts and links those facts to editable resume bullets where supported.
- Lets the user configure which sections, blocks, and bullets AI may edit.
- Extracts requirements from pasted job descriptions.
- Creates structured AI change proposals rather than uncontrolled full-document rewrites.
- Shows profile-scoped before/after review and lets the user edit tailored text before acceptance.
- Generates and stores a separate editable cover letter.
- Creates approved snapshots from accepted changes only.
- Adds private contact details only at final rendering/export time.
- Exports PDF and DOCX by default, with optional Markdown and HTML exports.
- Records copy/download activity as likely applied and provides a manual Mark as applied action.
- Shows active-profile dashboard statistics and recent application history.
- Stores DB-backed prompt-template user instructions while preserving protected safety rules.

## What it does not do

- It does not submit job applications automatically.
- It does not claim that copy/download actions definitely submitted an application.
- It does not automate LinkedIn, email, WhatsApp, or Telegram.
- It does not scrape job sites broadly.
- It does not provide fake ATS scores.
- It does not store raw OpenAI API keys in SQLite.
- It does not use YAML or Markdown files as runtime user sources of truth.

## Quickstart

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Then open the local web app and use:

1. `/settings` to confirm configuration, OpenAI key status, export formats, AI policy defaults, and prompt templates.
2. `/profiles/new` to create a person profile.
3. The header profile selector or Settings page to choose the active profile.
4. Settings -> CV Builder to create profile-scoped resumes.
5. `/applications` to paste a job, select an active-profile resume, and click Adapt.
6. The application review page to inspect requirements, fit summary, side-by-side changes, and cover letter.
7. Copy/download actions to track likely applied activity, or use Mark as applied when you actually apply.
8. `/` to review the active-profile Dashboard.

## Active profile concept

The app has one global active profile stored in SQLite as app-level settings. Dashboard, Application, CV Builder links, facts, and resume selection are scoped to the active profile. Settings remains available without an active profile. If the active profile is missing or deleted, the app safely falls back to a no-active-profile state.

## Dashboard

The home page opens the Dashboard. It shows active-profile-only metrics:

- resume count;
- application count;
- applications created in the last 30 days;
- likely applied count;
- manually marked applied count;
- recent application history;
- a deterministic server-rendered 30-day activity chart counted by application creation date.

## Application workflow

The Application page has a streamlined two-step workflow:

1. New application / job input: show active profile, select an active-profile resume, paste a job description, add optional job metadata, and click Adapt.
2. Adapted result / review: show extracted requirements, deterministic fit summary in fake mode, base-vs-tailored proposals, editable after text, accept/reject controls, editable cover letter, copy buttons, export/download links, and Mark as applied.

AI output is never applied directly to the base resume. The user must accept or reject proposals, and approved snapshots are created from accepted changes only.

## Settings hub

Settings is the workspace hub for:

- app configuration, data-folder status, export formats, locale, and OpenAI keyring status;
- AI policy defaults;
- profile creation/management and active-profile selection;
- CV Builder links for the active profile;
- active-profile facts;
- DB-backed prompt templates;
- safety/privacy notes.

## CV Builder

The CV Builder is launched from Settings or profile resume pages. It is profile-scoped and resume-scoped. The builder uses structured cards for sections and blocks, supports standard skeleton creation, and exposes visibility plus AI-edit toggles. References are created as non-AI-editable by default because they can contain private contact-like data.

## Prompt templates

Prompt templates are stored in SQLite. Users may edit custom user instructions for summary, skills, work-experience bullet, job-title, custom description, and cover-letter prompts. Protected safety rules are stored separately and cannot be disabled by user edits. Prompt builders continue to enforce no-fabrication, untrusted-job-posting, private-contact-exclusion, and structured-output rules.

## Privacy and AI safety

Private contact data such as email, phone, and address is stored locally but excluded from prompt builders by default. Prompt builders receive only AI-safe resume content, editable targets, allowed facts, job requirements, and editing policy. Private contact data is added only during final rendering/export.

Job postings are untrusted data. AI prompts instruct the model to extract or compare facts only and never follow instructions embedded in job text.

## Copy/download tracking and likely-applied semantics

Copy and download buttons record application events and update status to a likely-applied state. This means the user likely used the material outside the app; it is not a claim that the app submitted anything. The explicit Mark as applied action records that the user manually marked the application as applied.

## Testing and checks

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
uv run pre-commit run --all-files
```

## First-release hardening notes

This release keeps SQLite as the runtime source of truth and focuses on the local profile-first workflow. Settings remains available without an active profile, while Dashboard, Application, facts, and resume selection are scoped to the validated active profile.

### Error handling

Expected domain problems now render a safe error page with Dashboard, Application, Settings, and Back navigation. Missing active profiles, wrong-profile applications/resumes, missing tailoring runs, snapshot preconditions, and unsafe artifact paths are handled as user-facing workflow errors rather than raw server failures.

### CV Builder model

The CV Builder is server-rendered and structured around sections, blocks, and bullets. Builder pages show useful empty-state prompts, while rendered resume output hides empty sections and renders section headings in uppercase. Work experience blocks keep company, role, dates, present/current state, optional location, and AI-editable bullets; AI edits bullets by default rather than company or dates.

### Prompt scoping

Prompt instructions resolve in this order: section-specific, resume-specific, profile-specific, then global default. Prompt UI exposes only user instructions. Internal guardrails still enforce untrusted job text handling, no fabrication, private contact exclusion, and structured output.

### Uploads

Resume creation accepts PDF, DOC, and DOCX uploads. Files are stored under the local app data uploads area using safe generated filenames. Automatic resume parsing/import is not part of this first-release scope, and uploaded content is not sent to AI automatically.

### Likely-applied semantics

Copying full tailored resume text, copying a cover letter, or downloading an artifact records likely-applied activity only. The app never claims it submitted an application. The explicit Mark as applied button records the user-confirmed state.
