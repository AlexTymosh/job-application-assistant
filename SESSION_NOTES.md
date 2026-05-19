# Session Notes

## Current product direction

The app has been rebuilt around:

```text
Profile → Master CV / AI source material → Resume Variants → Job Tailoring → Tailored Resume + Fit Analysis + Cover Letter → Export
```

The previous user-facing facts/evidence workflow has been removed from the product language. Master CV is the local AI-safe source material used by tailoring; it is not an external fact-checking system.

## Database strategy

The app is pre-release, so the local SQLite schema may be reset. Startup initialises a clean SQL-first schema with Master CV, Master CV entries, Resume Variants, structured resume sections/blocks, Applications, Tailored Resumes, Application Analyses, Cover Letters, prompt templates, settings, and artifacts. Old compatibility repair logic for development databases has been removed.

## Resume Builder

CV Builder is a section-focused workspace with left navigation, central editor, and right live preview. The preview follows a clean blue-heading layout with compact bullets and hidden empty optional sections. Base Resume Variants can be exported as PDF or DOCX without AI.

## Master CV

Master CV is limited to AI source material only: Summary, Skills, Work Experience key/source bullets, and Education key bullets/achievements. Header, Languages, Certificates, and References remain in Resume Builder and are excluded from AI payloads by an allow-list. Master CV items can be edited and deleted from the builder-style Master CV pages.

## Tailoring

Application tailoring branches by the **Use Master CV source material** setting. Variant-only mode uses only the selected Resume Variant and pasted job description, excludes Master CV entries from AI payloads, runs separate Summary, Skills, Work Experience bullets, Education achievements, Cover Letter, and Fit Analysis tasks, and can use deterministic fake mode or OpenAI mode with a configured key. Master CV enhanced mode keeps the deterministic Master CV-enhanced behaviour for now. The Tailored Resume review page shows Fit Analysis, Base Resume, Tailored Resume, Cover Letter, and export actions. It does not currently expose raw Tailored Resume editing in the UI.

## Guardrails

Master CV enhanced prompt and fake-client guardrails prohibit invented employers, dates, degrees, certificates, metrics, and private contact changes. Variant-only mode does not add fact-checking or hallucination validation; the user reviews the result. Header and References are excluded from all AI payloads and are reattached only for local preview/export. Tests must use deterministic fake AI and must not touch real OpenAI or the real OS keyring. DOCX exports use Word Heading 1/2/3 styles for semantic ATS-friendly structure and label the work section as WORK EXPERIENCE. PDF exports keep readable visual headings and preserve visible/clickable header links and reference LinkedIn links where ReportLab supports them. Settings profile actions use compact typed-confirmation controls, and Dashboard chart styling uses flat colours without gradients.

## OpenAI boundary

OpenAI mode uses the OS keyring-backed secret service for the API key and model identifiers from SQLite settings. The key is never stored in SQLite or rendered in templates. Saving a key does not test a real call. Tests use fake/spy clients and do not call real OpenAI or the real OS keyring.

- Prompt Variant support is end-to-end for Variant-only mode: the selected variant controls resume tailoring, cover letter, and fit analysis prompts.
