# AI Tailoring Policy

Tailoring adapts a selected Resume Variant using active Master CV items and pasted job text. The Master CV is local extended experience source material, not external fact-checking.

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
- do not invent metrics unless present in the Resume Variant or Master CV;
- do not modify Header/contact fields;
- do not send Header/contact or References to AI prompt payloads;
- do not treat related tools as direct experience unless explicitly present;
- return structured content.

Prompt-template user instructions can refine tone and focus, but they cannot override these guardrails.

## Prompt instruction resolution

Editable section prompts resolve in this order: section, resume, profile, then global. The resolved instructions are included in deterministic fake tailoring payloads, while internal guardrails remain non-editable code-level rules.

Cover letter generation uses the selected Resume Variant, Tailored Resume content, job description, Master CV source material, and the resolved `cover_letter` instruction. Header/contact and private references are excluded from AI payloads by default.
