# AI tailoring policy

AI works on explicit targets, not whole-document rewrites.

Supported prompt boundaries:

- summary block;
- work-experience bullet;
- skills set;
- job title;
- description or custom block;
- cover letter.

Every prompt treats the job posting as untrusted data and prohibits fabricated experience, skills, metrics, employers, dates, and certificates.

Every model response is validated as a structured proposal with target ID, operation, before text, after text, reason, risk level, requirement IDs, fact IDs, and warnings. Proposals are not applied to the base resume. Only accepted proposals are used to build tailored snapshots.
