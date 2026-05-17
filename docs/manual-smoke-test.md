# Manual Smoke Test

1. Run `uv run uvicorn app.main:app --reload`.
2. Open `/settings`.
3. Create or select an active profile.
4. Create a resume from the standard skeleton.
5. Add or edit summary, hard skills, soft skills, work experience, education, language, certificate, and reference content.
6. Add facts and link at least one fact to a work experience bullet.
7. Open `/applications`.
8. Paste a job description.
9. Select an active-profile resume.
10. Click Adapt.
11. Review extracted requirements and the fit summary.
12. Edit tailored proposal output.
13. Accept at least one edited proposal and reject at least one proposal if available.
14. Review and edit the cover letter.
15. Save review decisions.
16. Create an approved snapshot.
17. Export PDF and DOCX.
18. Copy full tailored resume text.
19. Copy cover letter text.
20. Download PDF and DOCX artifacts.
21. Confirm the status is likely applied after copy/download.
22. Click Mark as applied.
23. Confirm Dashboard metrics and the 30-day chart update for the active profile.
24. Confirm another profile does not show the active profile's applications.
25. Confirm no private contact data appears in AI prompt payload tests or logs.

## Additional first-release smoke checks

26. Open Settings -> Facts with no active profile and confirm a clean empty state.
27. Confirm Settings -> Facts works after selecting an active profile.
28. Confirm `/applications` with no active profile and with no resumes shows clean empty states.
29. Confirm the Application form contains resume, source URL, and job description fields, without initial Job Title or Company fields.
30. Confirm the job description textarea resizes vertically only.
31. Try to create a snapshot before accepting proposals and confirm a friendly error.
32. Upload a PDF/DOC/DOCX when creating a resume and confirm it is stored locally; try a disallowed extension and confirm it is rejected.
33. Rename a resume and confirm the new name appears in the list, builder, and Application selector.
34. Add a Work Experience block with Present checked, add bullets, and confirm it renders in the final resume.
35. Confirm empty final resume sections are hidden and rendered section headings are uppercase.
36. Confirm prompt overrides resolve in section, resume, profile, global order.

## First-release fix-up notes

- Startup includes an explicit idempotent SQLite schema repair bridge for older local MVP databases. It creates missing model tables via metadata and repairs safe missing columns, including fact claim/evidence metadata and prompt-template scope columns.
- The active profile remains the workflow boundary for Dashboard, Application, CV Builder, resumes, and facts. Settings remains accessible without an active profile.
- Header navigation is Dashboard / Application / CV Builder, with Settings and the active-profile selector on the right. The project link points to `https://github.com/AlexTymosh/job-application-assistant`.
- Dashboard activity supports 10, 20, and 30 day ranges with hoverable server-rendered count bars.
- Settings uses a left-menu/right-panel layout. OpenAI API keys are stored in OS keyring only; model IDs are configurable SQLite/env settings, not secrets. Data-folder selection uses path input/validation because a native folder picker is not available in this server-rendered local UI.
- Prompt instructions are scoped by selected global/profile/resume/section objects instead of raw ID-only typing. Protected prompt guardrails stay internal and non-editable.
- Resume uploads are local reference artifacts for PDF/DOC/DOCX only and are validated before resume creation. Uploaded resume parsing remains out of scope for the first release.
- Resume Builder uses compact controls and type-specific block forms. Summary and skills avoid irrelevant move/sub-block controls; work experience uses month fields for CV periods.

## Additional first-release polish smoke tests

1. Start from an older local SQLite database where `applications` exists without `created_at`, launch the app, create a new application, and confirm the created date is current rather than `1970-01-01`.
2. Open `/?days=10`, `/?days=20`, and `/?days=30`; confirm the chart shows the new application, date labels on the X axis, count labels on the Y axis, and date/count hover text.
3. Open Dashboard and confirm the “Likely applied” and “Manually marked applied” metric cards are absent.
4. Open Settings -> Export formats, uncheck every format, save, and confirm all export flags remain off.
5. Open Settings -> AI policy defaults, uncheck every checkbox, save, and confirm all policy flags remain off.
6. Open Settings -> Data folder, enter a valid local folder path, save it, and confirm the status updates. Submit an empty path and confirm a friendly validation error. Open `/data-folder` and confirm it redirects to Settings -> Data folder.
7. Open Settings -> OpenAI and confirm “OpenAI API keys” and “OpenAI Models documentation” open in a new tab.
8. Create an application, open its detail page, confirm the delete form is visible, tick the confirmation checkbox, delete it, and confirm Dashboard counts decrease while the resume/profile remain.
9. Create an old application, use profile Application cleanup to delete applications older than N days, and confirm only matching profile applications are removed.
10. Create a disposable profile with a resume, fact, application, and scoped prompt. Delete the profile by typing its display name and confirm dependent data is removed, the active profile is cleared if applicable, and other profiles remain.
11. Open CV Builder and the full resume builder, click Download PDF and Download DOCX for a base resume, and confirm files download without creating an application or calling AI.
12. Confirm resume builder sections and blocks are visually compact while edit block, add block, add bullet, move controls, prompts, and export buttons remain available.
