# AI Job Application Assistant

AI Job Application Assistant is a local-first FastAPI/Jinja2 app for building CVs and preparing job-specific application materials. It helps create Resume Variants, adapt them to pasted job descriptions, generate a deterministic cover letter draft, and export CV files. It is not an auto-apply bot.

## Product workflow

```text
Profile → Master CV → Resume Variants → Job Application → Tailored Resume → PDF/DOCX export
```

- **Profile** stores the person-level workspace and private contact layer.
- **Master CV** stores only AI-safe source material for tailoring. It is not external fact-checking and it does not call third-party evidence systems.
- **Resume Variant** is a concrete CV version for a target role, such as Software Engineer or Backend Developer.
- **Job Application** stores pasted job text and the selected Resume Variant.
- **Tailored Resume** is a job-specific copy saved automatically after the deterministic local tailoring client adapts allowed sections.
- **Cover Letter** is generated automatically during adaptation by the deterministic local fake cover-letter client.

SQLite is the runtime source of truth for user-managed data. YAML and Markdown are not runtime sources of truth; Markdown is only a rendering/export representation used internally for preview/export paths.

## Resume Builder

The CV Builder uses a workspace layout:

- left vertical section navigation;
- central section-specific editor;
- right live resume preview;
- compact cards and focused fields;
- PDF/DOCX export for the base Resume Variant.

Resume Builder sections are Header, Skills, Summary, Work Experience, Education, Languages, Certificates, and References. Empty optional sections are hidden in preview and export. Header supports optional LinkedIn, GitHub, and Website URLs. Exports render email as a `mailto:` link and render LinkedIn, GitHub, Website, and reference LinkedIn URLs as visible/clickable links where the output format supports them, including ReportLab PDF link markup where practical. DOCX exports use semantic Word styles: Heading 1 for the candidate name/title, Heading 2 for major sections such as WORK EXPERIENCE, and Heading 3 for skill groups and work/education entries.

## Master CV / AI source material

The Master CV stores only AI-safe source material that can participate in tailoring:

- Summary source material;
- Hard Skills and Soft Skills;
- Work Experience key/source bullets;
- Education key bullets and achievements.

Header, Languages, Certificates, References, private contact details, and other non-AI sections belong to Resume Builder only. They are not part of the current Master CV UI and are excluded from tailoring and cover-letter payloads through the Master CV category allow-list. Master CV items can be edited and deleted from the builder-style page; deletion requires visible confirmation.

## AI tailoring policy

The current implementation uses deterministic local fake clients for tailoring and cover-letter generation. Model settings and OpenAI key storage exist as configuration surfaces, but the default code path used by the current workflow and tests does not call real OpenAI.

Tailoring uses the selected Resume Variant as the base and the Master CV as additional AI-safe source material. Internal code guardrails prevent the tailoring payload from including private or fixed fields by default:

- Header/contact fields are not AI-editable and are not sent to AI prompts.
- Master CV payloads use an allow-list: `summary`, `skills`, `work_experience`, and `education`.
- References are not sent to AI prompts.
- Languages, Certificates, and References are not AI-editable by default.
- Summary, Skills, Work Experience key bullets, and Education achievements are AI-editable.
- Employers, dates, degrees, certificates, and metrics must not be invented.
- Tests use deterministic fake AI and never call real OpenAI or the real OS keyring.

OpenAI API keys are stored only through the OS keyring boundary, never in SQLite or templates.

## Application tailoring

Use **Application → New adaptation** to select a Resume Variant, paste a job description, and adapt the resume. The app creates the Application, loads Master CV entries for the active profile, filters them through the AI-safe category allow-list, runs deterministic tailoring, saves a Tailored Resume automatically, creates a deterministic Cover Letter draft, and opens the review page.

The Tailored Resume review page currently shows the Base Resume preview, Tailored Resume preview, Cover Letter block, and export/download actions. It does not currently expose a raw Tailored Resume editor in the UI.

## Database reset note

This app is pre-release. The schema has been reset around Master CV, Resume Variants, Applications, Tailored Resumes, Cover Letters, prompts, and artifacts. Existing development SQLite databases can be deleted and recreated when schema changes. If an old local SQLite database contains legacy Master CV private categories, they are hidden from the Master CV UI and excluded from AI payloads; recreating the local database is acceptable during pre-release. Startup initialises the clean SQL-first schema deterministically and no longer carries old development schema repair bridges.

## Run locally

```bash
uv run uvicorn app.main:app --reload
```

## Validation

Before completing code changes, run when possible:

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
uv run pre-commit run --all-files
```
