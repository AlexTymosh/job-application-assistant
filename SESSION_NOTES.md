# Session Notes

## Current product direction

The app has been rebuilt around:

```text
Profile → Master CV / Extended Experience → Resume Variants → Job Tailoring → Tailored Resume → Export
```

The previous user-facing facts/evidence workflow has been removed from the product language. Master CV is the local extended experience source used by AI tailoring; it is not an external fact-checking system.

## Database strategy

The app is pre-release, so the local SQLite schema may be reset. Startup now initialises a clean SQL-first schema with Master CV, Master CV entries, Resume Variants, structured resume sections/blocks, Applications, and Tailored Resumes. Old compatibility repair logic for development databases has been removed.

## Resume Builder

CV Builder is a section-focused workspace with left navigation, central editor, and right live preview. The preview follows a clean blue-heading layout with compact bullets and hidden empty optional sections. Base Resume Variants can be exported as PDF or DOCX without AI.


## Tailoring

Application tailoring selects a Resume Variant, loads active Master CV items, adapts allowed fields, saves a Tailored Resume automatically, and then lets the user edit/export. Master CV is now limited to AI source material only: Summary, Skills, Work Experience key bullets, and Education key bullets. Header, Languages, Certificates, and References remain in Resume Builder and are excluded from AI payloads by an allow-list.

## Guardrails

Internal prompt and fake-client guardrails prohibit invented employers, dates, degrees, certificates, metrics, and private contact changes. Tests must use deterministic fake AI and must not touch real OpenAI or the real OS keyring. DOCX exports use Word Heading 1/2/3 styles for semantic ATS-friendly structure. PDF exports keep readable visual headings. Exports include email `mailto:` and LinkedIn/GitHub/website/reference LinkedIn links where practical. Settings profile actions use compact typed-confirmation controls, and Dashboard bars use flat muted blue without gradients.

## PR #94 fix-up

- Hardened profile isolation for application creation, review, export, and download. Applications are never listed globally when no active profile is selected.
- Restored the Dashboard stats service contract expected by the existing dashboard template, including 10/20/30-day activity ranges.
- Updated Master CV to use the same builder shell, left navigation, central editor, and right AI source preview style as CV Builder.
- Removed the raw tailored Markdown editor and added automatic deterministic cover letter generation during adaptation.
- Wired scoped prompt instructions into tailoring payloads and fake-client capture.
- Reworked DOCX/PDF exports to render styled resume content without Markdown artifacts and with runtime Unicode font handling for PDFs.
