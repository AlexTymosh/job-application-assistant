# Manual smoke test

1. Start the app with `uv run uvicorn app.main:app --reload`.
2. Open `/setup` and confirm SQL-first diagnostics render.
3. Open `/settings` and enable PDF and DOCX exports.
4. Create a profile and add private contact details.
5. Create a resume.
6. Add summary, skills, work experience, and education sections.
7. Add at least one editable work-experience bullet.
8. Add a fact supporting that bullet.
9. Create an application from pasted job text.
10. Extract requirements.
11. Run tailoring.
12. Review before/after proposals and accept one.
13. Create a snapshot.
14. Export enabled formats.
15. Download PDF and DOCX artifacts.
16. Generate a cover letter.
17. Confirm contact details appear only in final rendered exports, not prompt payloads.
