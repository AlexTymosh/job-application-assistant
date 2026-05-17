# AI Job Application Assistant

AI Job Application Assistant is a local-first FastAPI/Jinja2 app for building CVs and tailoring them to job descriptions without becoming an auto-apply bot.

## Product workflow

```text
Profile → Master CV → Resume Variants → Job Application → Tailored Resume → PDF/DOCX export
```

- **Profile** stores the person and private contact layer.
- **Master CV** is the extended experience library. It is not external fact-checking and it does not call third-party evidence systems.
- **Resume Variant** is a concrete CV version for a target role, such as Software Engineer or Backend Developer.
- **Job Application** stores pasted job text and the selected Resume Variant.
- **Tailored Resume** is a job-specific copy saved automatically after deterministic fake AI or configured AI adapts allowed sections.

SQLite is the runtime source of truth for user-managed data. YAML and Markdown are not runtime sources of truth; Markdown is only an export/rendering representation.

## Resume Builder

The CV Builder uses a screenshot-inspired workspace:

- left vertical section navigation;
- central section-specific editor;
- right live resume preview;
- compact cards and focused fields;
- PDF/DOCX export for the base Resume Variant.

Sections are Header, Skills, Summary, Professional Experience, Education, Languages, Certificates, and References. Empty optional sections are hidden in preview and export.

## Master CV / Extended Experience

The Master CV stores source material that AI can use while tailoring a selected Resume Variant. Items include category, title, content, keywords, allowed wording, forbidden wording, inference notes, and claim strength. This supports conservative wording such as using “Python dependency management experience” when Master CV says Poetry, while blocking direct claims such as “uv experience” unless explicitly present.

## AI tailoring policy

Tailoring uses the selected Resume Variant as the base and the Master CV as additional source material. Internal code guardrails prevent AI from editing private or fixed fields by default:

- Header/contact fields are not AI-editable and are not sent to AI prompts.
- References are not sent to AI prompts.
- Languages, Certificates, and References are not AI-editable by default.
- Summary, Skills, Work Experience key bullets, and Education achievements are AI-editable.
- Employers, dates, degrees, certificates, and metrics must not be invented.
- Tests use deterministic fake AI and never call real OpenAI or the real OS keyring.

OpenAI API keys are stored only through the OS keyring boundary, never in SQLite or templates.

## Application tailoring

Use **Application → New adaptation** to select a Resume Variant, paste a job description, and adapt the resume. The app creates the Application, loads active Master CV items, runs deterministic tailoring by default, saves a Tailored Resume automatically, and opens the review page. Users can edit the rendered Tailored Resume and export PDF/DOCX.

## Database reset note

This app is pre-release. The schema has been reset around Master CV, Resume Variants, and Tailored Resumes. Existing development SQLite databases can be deleted and recreated when schema changes. Startup initialises the clean SQL-first schema deterministically and no longer carries old development schema repair bridges.

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
