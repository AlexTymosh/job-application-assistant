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
