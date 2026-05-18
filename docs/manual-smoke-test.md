# Manual Smoke Test

1. Start the app with `uv run uvicorn app.main:app --reload`.
2. Create a Profile.
3. Open Master CV and confirm only Summary, Skills, Work Experience, and Education are available.
4. Add Summary source material, Hard/Soft Skills, Work Experience key bullets, and Education achievement bullets.
5. Edit and delete one Master CV Work Experience item, confirming deletion with the visible checkbox.
6. Open CV Builder and create a Resume Variant.
7. Edit Header, including optional Website URL, plus Skills, Summary, Work Experience, Education, Languages, Certificates, and References.
8. Confirm the right preview hides empty optional sections and shows blue uppercase headings.
9. Export the base Resume Variant as PDF and DOCX.
10. Confirm DOCX uses Word Heading 1/2/3 styles and has no raw Markdown markers.
11. Confirm PDF/DOCX show email, LinkedIn, GitHub, Website, and reference LinkedIn link text/clickable links where supported by Word or ReportLab.
12. Open Application, select the Resume Variant, paste a job description, and adapt.
13. Confirm a Tailored Resume review page opens automatically and displays Base Resume, Tailored Resume, and a Cover Letter block.
14. Confirm the review page does not show a raw Tailored Resume Markdown editor.
15. Export the Tailored Resume as PDF and DOCX.
16. Download the Cover Letter TXT file.
17. Confirm Settings profile action buttons are aligned and deletion requires typing the exact profile name.
18. Confirm Dashboard chart background and activity bars are flat colours, with 10/20/30-day switching, dates, counts, and hover titles.
19. Confirm exported resume section headings include WORK EXPERIENCE and no user-facing screen uses old evidence/fact-checking language.

## Profile isolation checks

- Confirm Applications shows an active-profile empty state when no active profile is selected and does not list other profiles' records.
- Confirm direct cross-profile application URLs and forged resume IDs are rejected.
- Confirm direct cross-profile Resume Builder and export URLs are rejected.
- Confirm direct cross-profile Master CV page, item edit, and item delete URLs are rejected.
- Confirm direct requests to removed Master CV categories such as Header or References redirect away and do not show private fields.

## Legacy data checks

- If an old pre-release SQLite database contains legacy Master CV private categories, confirm those rows are not visible in Master CV pages and are not included in AI payloads.
- Recreating the local database is acceptable during pre-release if full cleanup is needed.
