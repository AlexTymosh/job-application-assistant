# Release Checklist

- [ ] Profile → Master CV → Resume Variants → Job Tailoring → Tailored Resume → Export works from an empty database.
- [ ] Existing development databases can be deleted/recreated after schema changes.
- [ ] CV Builder has left navigation, central section forms, and right preview.
- [ ] Master CV contains only Summary, Skills, Work Experience key bullets, and Education key bullets.
- [ ] Header, Languages, Certificates, and References are available in Resume Builder only and are excluded from AI payloads.
- [ ] Master CV payloads use the category allow-list: `summary`, `skills`, `work_experience`, and `education`.
- [ ] Master CV item edit/delete works for AI-safe categories, legacy private Master CV rows are hidden from UI pages, and delete requires visible confirmation.
- [ ] Tailored Resume is saved automatically after adaptation.
- [ ] Base Resume Variant PDF/DOCX export works.
- [ ] Tailored Resume PDF/DOCX export works.
- [ ] DOCX export uses Heading 1/2/3 styles, labels the work section WORK EXPERIENCE, and has no raw Markdown artifacts.
- [ ] PDF export remains readable for Latin and non-ASCII text.
- [ ] Exported contact links include email mailto, LinkedIn, GitHub, Website, and reference LinkedIn where present, including PDF reference LinkedIn links where ReportLab supports them.
- [ ] Settings profile actions are aligned and typed deletion confirmation is required.
- [ ] Dashboard chart background and activity bars are flat colours with no gradient.
- [ ] Tests do not call real OpenAI or the real OS keyring.
- [ ] `uv run ruff format .` passes.
- [ ] `uv run ruff check .` passes.
- [ ] `uv run pytest` passes.
- [ ] `uv run pre-commit run --all-files` passes or any environment limitation is documented.

## Profile scope release gates

- [ ] Cross-profile Resume Variant adaptation is rejected.
- [ ] Cross-profile application review/export/download URLs are rejected.
- [ ] Cross-profile Master CV item edit/delete URLs are rejected.
- [ ] Dashboard renders zero and non-zero activity for 10/20/30-day ranges.
