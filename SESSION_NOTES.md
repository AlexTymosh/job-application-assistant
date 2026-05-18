# Session Notes

## Current product direction

The app has been rebuilt around:

```text
Profile → Master CV / AI source material → Resume Variants → Job Tailoring → Tailored Resume + Cover Letter → Export
```

The previous user-facing facts/evidence workflow has been removed from the product language. Master CV is the local AI-safe source material used by tailoring; it is not an external fact-checking system.

## Database strategy

The app is pre-release, so the local SQLite schema may be reset. Startup initialises a clean SQL-first schema with Master CV, Master CV entries, Resume Variants, structured resume sections/blocks, Applications, Tailored Resumes, Cover Letters, prompt templates, settings, and artifacts. Old compatibility repair logic for development databases has been removed.

## Resume Builder

CV Builder is a section-focused workspace with left navigation, central editor, and right live preview. The preview follows a clean blue-heading layout with compact bullets and hidden empty optional sections. Base Resume Variants can be exported as PDF or DOCX without AI.

## Master CV

Master CV is limited to AI source material only: Summary, Skills, Work Experience key/source bullets, and Education key bullets/achievements. Header, Languages, Certificates, and References remain in Resume Builder and are excluded from AI payloads by an allow-list. Master CV items can be edited and deleted from the builder-style Master CV pages.

## Tailoring

Application tailoring selects a Resume Variant, loads active-profile Master CV items, filters them to AI-safe categories, adapts allowed fields with the deterministic local fake tailoring client, saves a Tailored Resume automatically, and creates a deterministic Cover Letter draft. The Tailored Resume review page shows Base Resume, Tailored Resume, Cover Letter, and export actions. It does not currently expose raw Tailored Resume editing in the UI.

## Guardrails

Internal prompt and fake-client guardrails prohibit invented employers, dates, degrees, certificates, metrics, and private contact changes. Tests must use deterministic fake AI and must not touch real OpenAI or the real OS keyring. DOCX exports use Word Heading 1/2/3 styles for semantic ATS-friendly structure and label the work section as WORK EXPERIENCE. PDF exports keep readable visual headings and preserve visible/clickable header links and reference LinkedIn links where ReportLab supports them. Settings profile actions use compact typed-confirmation controls, and Dashboard chart styling uses flat colours without gradients.
