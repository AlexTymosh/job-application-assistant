# Manual Smoke Test

1. Run `uv run uvicorn app.main:app --reload`.
2. Open `/settings`.
3. Create or select an active profile.
4. Confirm the Settings cards start with Profiles, CV Builder, and Prompt templates.
5. Open active-profile facts and confirm it does not fail with or without an active profile.
6. Create a resume from the standard skeleton, optionally uploading a PDF, DOC, or DOCX file.
7. Edit the resume name, target role, and language.
8. Add or edit summary, hard skills, soft skills, work experience, education, language, certificate, reference, and custom content.
9. Add multiple work experience periods and bullets; confirm the current/present checkbox persists.
10. Reorder sections, blocks, and bullets with ↑ / ↓ buttons.
11. Add a section prompt override and confirm protected safety rules are not editable in the prompt UI.
12. Add facts and link at least one fact to a work experience bullet.
13. Open `/applications`.
14. Confirm only active-profile resumes appear.
15. Paste a job description and optional source URL.
16. Click Adapt.
17. Review extracted requirements and the fit summary.
18. Edit tailored proposal output.
19. Accept at least one edited proposal and reject at least one proposal if available.
20. Review and edit the cover letter.
21. Save review decisions.
22. Create an approved snapshot.
23. Export PDF and DOCX.
24. Copy full tailored resume text.
25. Copy cover letter text.
26. Download PDF and DOCX artifacts.
27. Confirm the status is likely applied after copy/download.
28. Click Mark as applied.
29. Confirm Dashboard metrics and the 30-day chart update for the active profile.
30. Confirm another active profile cannot access the first profile's application detail or mutation routes.
31. Confirm no private contact data appears in AI prompt payload tests or logs.
