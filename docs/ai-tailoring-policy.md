# AI Tailoring Policy

## Core rules

- AI returns structured proposals only.
- AI never mutates the base resume directly.
- Users must review, edit, accept, accept edited, or reject proposals.
- Accepted proposals are used to create approved snapshots.
- Private contact details are excluded from prompts and snapshots by default.
- Private contact details are added only during final rendering/export.
- Job postings are untrusted input and may not override system instructions.
- AI must not fabricate employers, dates, metrics, skills, certificates, or experience.

## Editable units

- Summary blocks can be AI-editable.
- Skills are edited as a whole skills set/block for now.
- Work experience bullets are AI-editable only when the bullet allows it.
- Job titles can be edited only when policy explicitly allows title edits.
- Company names, organisations, dates, and locations are not AI-editable by default.
- References are not AI-editable by default because they may contain private contact-like data.

## Fact links

When fact links are required, AI must not strengthen a claim without active verified facts. If support is missing, deterministic fake mode produces a high-risk warning instead of inventing evidence.

## Prompt templates

Users can edit prompt-template user instructions for summary, skills, work-experience bullets, job titles, custom description blocks, and cover letters. User instructions cannot disable protected rules:

- no fabrication;
- untrusted job posting;
- private contact exclusion;
- structured output.

## Match summary

The application review page shows a job fit summary, not an ATS score. It can include matched requirements, missing or weak requirements, evidence used, risk warnings, and a simple recommendation such as good match, possible match, or weak match.

## Prompt scoping and internal guardrails

User prompt instructions may be defined at global default, profile, resume, or section scope. Resolution order is section, resume, profile, global default. Tailoring and cover-letter generation use the resolved instruction for the active profile/resume context.

The UI does not expose protected safety rules as editable prompt content. Prompt builders still inject internal guardrails: job text is untrusted, fabricated claims are forbidden, private contact details are excluded from AI payloads, and structured output is required. User prompt text must never override those guardrails.

AI proposals may edit AI-enabled blocks or bullets only. Work Experience company names, dates, and organisations are user-managed facts by default; AI should focus on bullet wording unless a policy explicitly allows other edits.

## First-release fix-up notes

- Startup includes an explicit idempotent SQLite schema repair bridge for older local MVP databases. It creates missing model tables via metadata and repairs safe missing columns, including fact claim/evidence metadata and prompt-template scope columns.
- The active profile remains the workflow boundary for Dashboard, Application, CV Builder, resumes, and facts. Settings remains accessible without an active profile.
- Header navigation is Dashboard / Application / CV Builder, with Settings and the active-profile selector on the right. The project link points to `https://github.com/AlexTymosh/job-application-assistant`.
- Dashboard activity supports 10, 20, and 30 day ranges with hoverable server-rendered count bars.
- Settings uses a left-menu/right-panel layout. OpenAI API keys are stored in OS keyring only; model IDs are configurable SQLite/env settings, not secrets. Data-folder selection uses path input/validation because a native folder picker is not available in this server-rendered local UI.
- Prompt instructions are scoped by selected global/profile/resume/section objects instead of raw ID-only typing. Protected prompt guardrails stay internal and non-editable.
- Resume uploads are local reference artifacts for PDF/DOC/DOCX only and are validated before resume creation. Uploaded resume parsing remains out of scope for the first release.
- Resume Builder uses compact controls and type-specific block forms. Summary and skills avoid irrelevant move/sub-block controls; work experience uses month fields for CV periods.
