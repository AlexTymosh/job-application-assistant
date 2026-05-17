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

## Current first-release polish update

- Dashboard activity uses a server-rendered chart with a date X axis, application-count Y axis, hover titles, and 10/20/30 day range links. The likely-applied and manually marked applied metric cards are no longer displayed.
- Settings split forms are section-scoped. Export formats and AI policy defaults can be saved with every checkbox unchecked; unrelated Settings forms preserve existing values.
- Data folder is managed from Settings -> Data folder with path validation/create flow and reset-to-default support. `/data-folder` redirects to `/settings?section=data-folder`.
- CV Builder and the full resume builder can export the current base resume as PDF or DOCX under the app-owned artifacts directory without creating an application and without calling AI.
- Profile detail supports deleting one application, applications older than N days, all profile applications, and the profile itself. Destructive profile deletion requires typing the profile display name and clears the active profile when needed.
- The SQLite repair bridge avoids permanent `1970-01-01` timestamp defaults for repaired timestamp columns; new ORM-created rows use current UTC-naive timestamps so repaired databases still drive Dashboard charts and recent ordering correctly.

### Manual smoke additions

1. Start from an older SQLite database missing `applications.created_at`, run startup, create a new application, and confirm its created date is current and appears in Dashboard 10/20/30 day charts.
2. In Settings -> Export formats, uncheck every checkbox and save; confirm all formats are off. Repeat for Settings -> AI policy defaults.
3. In Settings -> Data folder, save a valid local path, confirm it is created/selected, then use the default-folder action.
4. Create an application, delete it from the profile detail cleanup section, and confirm Dashboard counts update while the resume/profile remain.
5. Delete a test profile by typing its display name and confirm dependent resumes, facts, applications, and scoped prompt templates are removed and the active profile is cleared if applicable.
6. Export a base resume from CV Builder as PDF and DOCX and confirm both downloads work without an application.
