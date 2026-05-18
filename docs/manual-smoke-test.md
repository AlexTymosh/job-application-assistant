# Manual Smoke Test

1. Start the app with `uv run uvicorn app.main:app --reload`.
2. Create a Profile.
3. Open Master CV and add at least one Extended Experience item with allowed and forbidden wording.
4. Open CV Builder and create a Resume Variant.
5. Edit Header, Skills, Summary, Work Experience, Education, Languages, Certificates, and References.
6. Confirm the right preview hides empty optional sections and shows blue uppercase headings.
7. Export the base Resume Variant as PDF and DOCX.
8. Open Application, select the Resume Variant, paste a job description, and adapt.
9. Confirm a Tailored Resume review page opens automatically.
10. Edit and save the Tailored Resume markdown.
11. Export the Tailored Resume as PDF and DOCX.
12. Confirm no user-facing screen uses old evidence/fact-checking language.
