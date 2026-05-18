# AI Tailoring Policy

Tailoring adapts a selected Resume Variant using pasted job text. The app now has two intended tailoring modes controlled by **Settings → AI policy → Use Master CV source material**.

## Current implementation status

- **Variant-only mode** (`use_master_cv=false`) is implemented as the first real section-by-section AI flow. It uses only the selected Resume Variant and the pasted job description. It can run with the deterministic fake client or with the OpenAI client when `llm_mode=openai` and an API key is available.
- **Master CV enhanced mode** (`use_master_cv=true`) keeps the existing deterministic Master CV-enhanced behaviour for now. The full real OpenAI Master CV enhanced flow is planned for a later variant.
- Tests must never call real OpenAI or the real OS keyring.

## Variant-only mode

Variant-only mode sends separate tasks for Summary, Skills, Work Experience bullets, Education achievements, Cover Letter, and Fit Analysis. It does not include Master CV entries in any payload. The user is responsible for prompt quality and final review.

Variant-only mode intentionally does **not** run fact-checking, evidence matrices, hallucination validation, source-claim validation, fake ATS scoring, or “do not invent” policy checks. The app still enforces technical boundaries: payloads must have the expected shape, the base Resume Variant is not overwritten, and private sections are excluded.

## Master CV allow-list

Only these Master CV categories are allowed into Master CV enhanced tailoring payloads:

- `summary` — summary source material;
- `skills` — hard and soft skill source material;
- `work_experience` — key/source bullets only;
- `education` — key bullets and achievements only.

Legacy or private categories are hidden from Master CV UI pages and excluded even if old rows exist in SQLite: `header`, `reference`, `references`, `languages`, and `certificates`.

## Editable and private boundaries

- Summary text is AI-editable.
- Hard Skills and Soft Skills are AI-editable.
- Work Experience key bullets are AI-editable.
- Education achievements/key bullets are AI-editable.
- Header and References are never sent to AI payloads.
- Languages and Certificates are not AI-editable by default.
- Header and References are reattached from the original Resume Variant only after AI processing for local preview/export.
- The original Resume Variant is never overwritten; the app saves a separate Tailored Resume.

## Prompt instruction resolution

Editable section prompts resolve in this order: section, resume, profile, then global. Cover Letter and Fit Analysis support global, profile, and resume scope, but not section scope.

The prompt types are `summary`, `skills`, `work_experience_bullets`, `education_achievements`, `cover_letter`, and `fit_analysis`.

## OpenAI and secrets

OpenAI calls require `llm_mode=openai` and a configured API key. The OpenAI API key is read through the OS keyring boundary and is never stored in SQLite or rendered back into templates. Saving the key only stores it; it does not prove that a real OpenAI call will succeed.
