# AI Job Application Assistant

**AI Job Application Assistant** is a local application for adapting CVs to job vacancies with AI support (OpenAI), with protection against hallucinations and a developed **Bridge**-based approach for supporting cross-adjacent skills.

The goal of the application is to help a candidate pass ATS filters using an existing CV by adapting the resume to a specific vacancy without inventing false claims.

The project is available as **Beta 1.0** with limited but working functionality:

- candidate profile creation;
- creation of Resume Variants for different vacancies;
- built-in professional prompts;
- ability to create custom Prompt Variants using a recommended structure;
- adaptation of a selected Resume Variant to a specific job vacancy;
- automatic Cover Letter generation;
- detailed Fit Analysis generation;
- application history tracking;
- export to PDF/DOCX;
- management of AI model connection versions.

**Note:** the application does not send personal data to AI. Personal information blocks and references are stored locally only.

The average cost of one full package request for the English-language version is approximately **7,700 output tokens** and **1,150 input tokens**. With the default settings, this is roughly **1 penny per package processing run** based on OpenAI prices as of May 2026.

The application is not currently an automatic job application bot.

It is a controlled workspace for preparing stronger job applications, while final review remains under the user's control.

## Architecture Concept

At the applied architecture layer, the system is designed around high-granularity controlled mutations: processing is performed at the level of semantic CV blocks rather than free-form document generation. This creates the foundation for transparent interface-level Diff control and full Resume Version Control with rollback capability.

For elegant ATS traversal without factual distortion, the pipeline relies on **Bridging** — a controlled semantic strategy that safely connects a candidate’s transferable, cross-adjacent experience with the explicit requirements of a vacancy.

The financial and technical efficiency of the pipeline is achieved through **dynamic model routing**: token-cost balancing by assigning different model classes to different processing layers, using fast LLMs for primary analysis and stronger reasoning models for deep adaptation.

## Product workflow

```text
Profile → Resume Variant → Prompt Variant → Job Application → Tailored Resume → Fit Analysis → Cover Letter → PDF/DOCX export
```

- **Profile** stores the person-level workspace and private contact layer.
- **Resume Variant** is a concrete CV version for a target role, such as Software Engineer, Automation Engineer, or Data Analyst.
- **Prompt Variant** is a prompt pack used for the AI tasks: resume tailoring, cover letter drafting, and fit analysis.
- **Job Application** stores pasted job text and the selected Resume Variant / Prompt Variant.
- **Tailored Resume** is a job-specific copy saved automatically after tailoring adapts allowed sections.
- **Fit Analysis** is generated automatically during adaptation as review guidance without fake numeric ATS scoring.
- **Cover Letter** is generated automatically during adaptation.
- **Export** produces PDF/DOCX versions for manual review and use.

SQLite is the runtime source of truth for user-managed data. YAML and Markdown are not runtime sources of truth; Markdown is only a rendering/export representation used internally for preview/export paths.

## Core capabilities

### Profiles

Profiles allow the app to support different people or candidate identities in one local workspace. Dashboard, Resume Variants, Master CV source material, applications, and tailored outputs are scoped to the active profile.

### Resume Variants

A Resume Variant is a structured CV version for a target role. For example, one profile can have separate variants for:

- Software Engineer;
- Python Developer;
- Automation Engineer;
- Data Analyst;
- Technical Operations / SaaS systems.

The base Resume Variant is not overwritten by AI tailoring. The application creates a separate Tailored Resume copy for each job application.

### Prompt Variants

Prompt Variants are reusable prompt packs. Each pack contains task-specific instructions for:

- **resume_tailoring** — adapts Statement, Skills, Work Experience bullets, and Education achievements;
- **cover_letter** — creates a cover letter draft from the safe resume content and job description;
- **fit_analysis** — compares the resume with the job description and produces review guidance.

The Prompt Variant editor shows the expected structured response contract for each task, which helps keep AI responses parseable and easier to debug.

### AI task separation

Variant-only tailoring uses separate structured tasks instead of asking the model to write one large free-form document. The current task separation is:

```text
Resume Tailoring → Cover Letter → Fit Analysis
```

This design gives clearer logs, safer parsing, and a better foundation for future review workflows such as block-level Diff, accept/reject controls, and resume version history.

### Model configuration

The Settings screen allows selecting model identifiers for different task layers. This makes it possible to balance cost and quality, for example by using faster models for lighter tasks and stronger reasoning models for deeper adaptation steps.

The OpenAI API key is stored through the OS keyring boundary and is not stored in SQLite or rendered back into templates.

## Resume Builder

The CV Builder uses a workspace layout:

- left vertical section navigation;
- central section-specific editor;
- right live resume preview;
- compact cards and focused fields;
- PDF/DOCX export for the base Resume Variant.

Resume Builder sections are Header, Skills, Statement, Work Experience, Education, Languages, Certificates, and References. Empty optional sections are hidden in preview and export. Header supports optional LinkedIn, GitHub, and Website URLs. Exports render email as a `mailto:` link and render LinkedIn, GitHub, Website, and reference LinkedIn URLs as visible/clickable links where the output format supports them, including ReportLab PDF link markup where practical. DOCX exports use semantic Word styles: Heading 1 for the candidate name/title, Heading 2 for major sections such as WORK EXPERIENCE, and Heading 3 for skill groups and work/education entries.

## Master CV / AI source material

The Master CV stores only AI-safe source material that can participate in future enhanced tailoring workflows:

- Statement source material;
- Hard Skills and Soft Skills;
- Work Experience key/source bullets;
- Education key bullets and achievements.

Header, Languages, Certificates, References, private contact details, and other non-AI sections belong to Resume Builder only. They are not part of the current Master CV UI and are excluded from tailoring and cover-letter payloads through the Master CV category allow-list. Master CV items can be edited and deleted from the builder-style page; deletion requires visible confirmation.

## AI tailoring policy

Tailoring has two intended modes controlled by **Settings → AI policy → Use Master CV source material**.

- **Variant-only mode** disables Master CV source material and runs the first practical AI flow. It uses only the selected Resume Variant and the pasted job description. It can run with the deterministic fake client or the OpenAI client when **OpenAI mode** is selected and a key is configured. Master CV entries are not loaded for AI payloads in this mode.
- **Master CV enhanced mode** keeps the existing deterministic Master CV-enhanced behaviour for now. The future real OpenAI Master CV enhanced flow is intentionally not the primary Beta 1.0 path.

Variant-only mode sends structured tasks for Resume Tailoring, Cover Letter, and Fit Analysis. It does not run fact-checking, hallucination validation, evidence matrices, source-claim validation, or fake numeric ATS scoring; the user is responsible for reviewing the generated result.

Private boundaries remain enforced in both modes:

- Header/contact fields are not sent to AI prompts.
- References are not sent to AI prompts.
- Header and References are reattached from the original Resume Variant only after AI processing for local preview/export.
- The original Resume Variant is never overwritten; the app saves a separate Tailored Resume.
- Tests use deterministic fake AI and never call real OpenAI or the real OS keyring.

OpenAI API keys are stored only through the OS keyring boundary, never in SQLite or templates. Saving the key does not test a real provider call by itself. Real OpenAI calls require OpenAI mode and a configured key.

## Application tailoring

Use **Application → New adaptation** to select a Resume Variant, select a Prompt Variant prompt pack, paste a job description, and adapt the resume. The app creates the Application, branches by the **Use Master CV source material** setting, saves a Tailored Resume automatically, creates Fit Analysis and Cover Letter output, and opens the review page.

The Tailored Resume review page shows Fit Analysis above the Base Resume preview and Tailored Resume preview, then the Cover Letter block and export/download actions. It does not currently expose a raw Tailored Resume editor in the UI.

## Database reset note

This app is still pre-release/beta. The schema has been reset around Master CV, Resume Variants, Applications, Tailored Resumes, Cover Letters, prompts, and artifacts. Existing development SQLite databases can be deleted and recreated when schema changes. If an old local SQLite database contains legacy Master CV private categories, they are hidden from the Master CV UI and excluded from AI payloads; recreating the local database is acceptable during pre-release. Startup initialises the clean SQL-first schema deterministically and no longer carries old development schema repair bridges.

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

## Development notes

- Prompt Variants are user-manageable prompt packs in Settings (`resume_tailoring`, `cover_letter`, `fit_analysis`).
- Prompt Variant settings show read-only expected JSON response contracts for all three Variant-only tasks.
- Variant-only AI JSON responses are parsed with a resilience layer: direct JSON, fenced JSON, or object extraction from wrapped responses.
- Invalid model responses return controlled errors with trace IDs and local AI task logs.
