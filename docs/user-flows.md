# User Flows

## Primary local workflow

```text
Open Settings -> create/select active profile -> build resume -> paste job -> Adapt -> review/edit proposals -> accept/reject -> edit cover letter -> copy/download -> likely applied tracking -> Dashboard
```

## Active profile

The app has one global active profile stored in SQLite settings. Dashboard, Application, resume selection, CV Builder links, facts, and application history use this active profile. Settings remains available when no active profile exists.

## Dashboard flow

1. Open `/`.
2. If no active profile exists, use the empty-state links to create or select a profile.
3. If an active profile exists, review profile-scoped resume count, application count, last-30-day application count, likely-applied count, manually marked applied count, recent applications, and the 30-day activity chart.

The chart counts applications by creation date.

## Settings hub flow

1. Open `/settings`.
2. Confirm export formats, locale, and OpenAI key status.
3. Configure default AI policies.
4. Create/manage profiles and select the active profile.
5. Open active-profile resumes, create a resume, or manage facts.
6. Open Prompt templates and edit user instructions.
7. Review the safety/privacy note.

## CV Builder flow

1. Open Settings -> active profile resumes.
2. Create a resume version such as Software Engineer, Automation Engineer, Data Analyst, or Backend Developer.
3. Choose Create standard CV sections for the default skeleton.
4. Edit sections as cards.
5. Edit blocks for summary, hard skills, soft skills, work experience, education, languages, certifications, references, or custom content.
6. Add bullets to work experience blocks.
7. Toggle visibility and AI-edit permissions.
8. Link facts to bullets where supported.

References are not AI-editable by default because they may contain private contact-like data.

## Application flow

1. Open `/applications`.
2. Confirm the active profile shown in the header.
3. Select a resume from the active profile.
4. Paste a job description.
5. Optionally add job title, company, and source URL.
6. Click Adapt.
7. The app creates an application, extracts requirements, runs tailoring, creates structured proposals, and generates a cover letter.
8. Review the fit summary, base resume text, tailored text, and warnings.
9. Edit tailored `after_text` before accepting if needed.
10. Accept, accept edited, or reject each proposal.
11. Edit and save the cover letter.
12. Create an approved snapshot from accepted changes.
13. Export/download enabled formats.
14. Copy resume or cover letter text.
15. Mark as applied manually if the user actually applied outside the app.

## Likely-applied tracking

Copy and download actions create events and move the application into a likely-applied state. This means the user probably used the material externally. It does not mean the app submitted the application. Manual Mark as applied records a user-confirmed application status.
