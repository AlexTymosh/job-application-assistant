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
