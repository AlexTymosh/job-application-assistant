# User Flows

## Primary local workflow

```text
Open Settings -> create/select active profile -> build resume -> paste job -> Adapt -> review/edit proposals -> accept/reject -> edit cover letter -> snapshot -> copy/download -> likely applied tracking -> Dashboard
```

## Active profile

The app has one global active profile stored in SQLite settings. Dashboard, Application, resume selection, CV Builder links, facts, and application history use this active profile. Settings remains available when no active profile exists.

## Settings hub flow

1. Open `/settings`.
2. Create/manage profiles and select the active profile.
3. Open active-profile resumes, create a resume, edit resume metadata, or manage active-profile facts.
4. Open Prompt templates and edit user instructions.
5. Configure locale, OpenAI keyring status, export formats, AI policies, safety/privacy, and data-folder settings.

## CV Builder flow

1. Open Settings -> active profile resumes.
2. Create a resume version and optionally upload an existing PDF, DOC, or DOCX resume for local storage.
3. Choose Create standard CV sections for the default skeleton.
4. Edit sections as cards and use compact ↑ / ↓ controls to reorder sections, blocks, and bullets.
5. Use section-specific fields for summary, skills, work experience, education, languages, certificates, references, or custom content.
6. Add multiple work experience periods with role, organisation, start/end dates, present/current state, optional location, and bullets.
7. Toggle visibility and AI-edit permissions.
8. Add section-level prompt overrides where needed.
9. Link facts to bullets where supported.

Builder pages show compact prompts for empty sections. Final rendered resume output hides empty sections and uses uppercase section titles.

## Application flow

1. Open `/applications`.
2. Confirm the active profile shown in the header.
3. Select a resume from the active profile.
4. Paste a job description and optionally add a source URL.
5. Click Adapt.
6. The app creates an application, extracts requirements, runs tailoring, creates structured proposals, and generates a cover letter.
7. Review the fit summary, base resume text, tailored editable copy, and warnings.
8. Edit tailored `after_text` before accepting if needed.
9. Accept, accept edited, or reject each proposal.
10. Edit and save the cover letter.
11. Create an approved snapshot from accepted changes.
12. Export/download enabled formats.
13. Copy full tailored resume text or cover letter text.
14. Mark as applied manually if the user actually applied outside the app.

If no active profile or no active-profile resume exists, the page shows a clean empty state instead of allowing an unrestricted action.

## Likely-applied tracking

Copy and download actions create events and move the application into a likely-applied state. This means the user probably used the material externally. It does not mean the app submitted the application. Manual Mark as applied records a user-confirmed application status.

## Upload limitations

Uploaded resume files are stored safely under the local app data upload area with generated safe filenames. Automatic DOC/DOCX/PDF parsing and AI import are not part of this first release.
