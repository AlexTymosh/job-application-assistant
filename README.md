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

The first local release now treats the active profile as a hard workflow boundary. Facts, applications, application detail pages, mutations, resume selection, and dashboard metrics all require or derive the active profile. Direct application URLs without an active profile show a friendly error page instead of opening unrestricted data.

The initial Application form intentionally asks only for the active profile context, an active-profile resume, an optional source URL, and the job description. Job title and company can be inferred or edited later on the review/detail page. Adapt creates the application, extracts requirements, creates structured tailoring proposals, generates a cover letter, and redirects to the review page.

Approved snapshots are created only after at least one proposal is accepted or accepted as edited. Repeated snapshot creation for the same tailoring run returns the existing snapshot instead of creating confusing duplicates. Export/download starts from the approved snapshot and adds private contact details only during final rendering.

The CV Builder uses section-aware fields for practical first-release editing: summary text, skills text, work experience role/company/dates/current state, education/certification/reference-style metadata, and custom content. Work experience supports multiple periods and separate bullets. Empty sections remain visible in the builder as compact prompts, but final rendered resumes hide empty sections and render section titles in uppercase.

Prompt instructions are scoped in SQLite with this resolution order: section, resume, profile, global default. The prompt UI exposes only user-editable instructions. Internal guardrails remain non-editable in prompt-building code: job postings are untrusted, fabrication is forbidden, private contact details are excluded, and structured output is required.

Resume creation accepts optional `.pdf`, `.doc`, and `.docx` uploads. Uploaded files are stored under the app-owned `artifacts/uploads` area with safe generated filenames. Automatic parsing of complex resume layouts is intentionally not implemented for the first release; the file is kept as local reference material for manual import.

Expected first-release limitations remain: no automatic submission, no LinkedIn automation, no email sending, no broad scraping, no fake ATS score, and no YAML or Markdown runtime source of truth. Copy/download events mean likely applied only; only the explicit Mark as applied action records a manually confirmed application.

## First-release local compatibility and UX notes

### SQLite schema repair

This local-first MVP uses SQLite as the runtime source of truth. At startup the app still creates missing tables, and it also runs an explicit idempotent schema drift repair for older local databases that were created before the current SQL-first model. The repair bridge adds safe missing columns such as fact claim/evidence metadata and prompt-template scope columns because SQLite `CREATE TABLE IF NOT EXISTS` cannot alter existing tables.

### Navigation and active profile workflow

The main navigation is Dashboard, Application, and CV Builder. Settings is placed on the right near the active-profile selector. Dashboard, Application, CV Builder, resumes, and facts are scoped to the selected active profile; Settings remains available without one.

### Dashboard activity chart

The Dashboard activity chart supports `/?days=10`, `/?days=20`, and `/?days=30`. Unsupported values fall back to 30 days. Bars are server-rendered and expose date/count hover text.

### Settings, OpenAI, and data folder

Settings uses a left menu with focused panels. The OpenAI API key is stored through the OS keyring boundary, never in SQLite. Model IDs are normal configurable settings (`openai_model_default`, `openai_model_qa`, `openai_model_extract`, and `openai_model_tailor`) and may be supplied from environment variables or SQLite settings. Useful links: [OpenAI API keys](https://platform.openai.com/settings/organization/api-keys) and [OpenAI Models documentation](https://platform.openai.com/docs/models).

The local data folder is managed through path input and validation. A server-rendered local web UI cannot reliably open an OS-native PyCharm-style folder picker through standard browser APIs, so native folder picking is not claimed for the MVP.

### Prompt instructions and CV Builder

Prompt instructions can be scoped globally or to a selected profile, resume, or section using named selectors. Internal privacy, anti-fabrication, untrusted-job-posting, and structured-output guardrails are applied in prompt builders and are not editable in the UI.

CV Builder is a top-level workspace. Resume upload stores `.pdf`, `.doc`, and `.docx` files locally as reference artifacts, but full parsing of uploaded documents is not implemented yet. Resume block edit forms are type-specific for summary, skills, work experience, education, languages, certifications, references, and custom content.
