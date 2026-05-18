# AI Tailoring Policy

Tailoring adapts a selected Resume Variant using active Master CV source material and pasted job text. The Master CV is local AI source material, not external fact-checking.

## Master CV allow-list

Only these Master CV categories are allowed into tailoring and cover-letter payloads:

- `summary` — summary source material;
- `skills` — hard and soft skill source material;
- `work_experience` — key/source bullets only;
- `education` — key bullets and achievements only.

Legacy or private categories are excluded even if old rows exist in SQLite: `header`, `reference`, `references`, `languages`, and `certificates`.

## Editable boundaries

- Summary text is AI-editable.
- Hard Skills and Soft Skills are AI-editable.
- Work Experience key bullets are AI-editable.
- Education achievements/key bullets are AI-editable.
- Header, Languages, Certificates, and References are not AI-editable by default.

## Internal guardrails

The app applies non-editable code-level guardrails:

- do not invent employers;
- do not invent dates;
- do not invent degrees;
- do not invent certificates;
- do not invent metrics unless present in the Resume Variant or allowed Master CV source material;
- do not modify Header/contact fields;
- do not send Header/contact, Languages, Certificates, or References to AI prompt payloads;
- do not treat related tools as direct experience unless explicitly present;
- return structured content.

Prompt-template user instructions can refine tone and focus, but they cannot override these guardrails.

## Prompt instruction resolution

Editable section prompts resolve in this order: section, resume, profile, then global. The resolved instructions are included in deterministic fake tailoring payloads, while internal guardrails remain non-editable code-level rules.

Cover letter generation uses the selected Resume Variant, Tailored Resume content, job description, AI-safe Master CV source material, and the resolved `cover_letter` instruction. Header/contact and private references are excluded from AI payloads by default.
