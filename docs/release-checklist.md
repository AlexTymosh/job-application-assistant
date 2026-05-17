# Release Checklist

- [ ] Profile → Master CV → Resume Variants → Job Tailoring → Tailored Resume → Export works from an empty database.
- [ ] Existing development databases can be deleted/recreated after schema changes.
- [ ] CV Builder has left navigation, central section forms, and right preview.
- [ ] Header/contact and References are excluded from AI prompt payloads.
- [ ] Tailored Resume is saved automatically after adaptation.
- [ ] Base Resume Variant PDF/DOCX export works.
- [ ] Tailored Resume PDF/DOCX export works.
- [ ] Tests do not call real OpenAI or the real OS keyring.
- [ ] `uv run ruff format .` passes.
- [ ] `uv run ruff check .` passes.
- [ ] `uv run pytest` passes.
- [ ] `uv run pre-commit run --all-files` passes or any environment limitation is documented.

## PR #94 fix-up release gates

- [ ] Cross-profile Resume Variant adaptation is rejected.
- [ ] Cross-profile application review/export/download URLs are rejected.
- [ ] Dashboard renders zero and non-zero activity for 10/20/30-day ranges.
- [ ] Master CV uses the builder-style UI.
- [ ] Cover Letter is generated and displayed after Adapt Resume.
- [ ] Tailored Resume review has no raw Markdown edit block.
- [ ] DOCX export has styled headings/separators and no Markdown artifacts.
- [ ] PDF export is readable with non-ASCII text.
