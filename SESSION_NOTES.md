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

Application tailoring selects a Resume Variant, loads active Master CV items, adapts allowed fields, saves a Tailored Resume automatically, and then lets the user edit/export. Header and References are excluded from prompt payloads and added back only for rendering/export.

## Guardrails

Internal prompt and fake-client guardrails prohibit invented employers, dates, degrees, certificates, metrics, and private contact changes. Tests must use deterministic fake AI and must not touch real OpenAI or the real OS keyring.
