# Release Checklist

## Product gates

- [ ] The app remains local-first and does not add auto-apply, hidden submissions, job scraping, payments, or cloud multi-user auth.
- [ ] SQLite remains the runtime source of truth for user-managed data.
- [ ] Master CV remains AI-source-only: Summary, Skills, Work Experience key/source bullets, and Education key bullets/achievements.
- [ ] Variant-only mode works when **Use Master CV source material** is disabled.
- [ ] Variant-only mode sends no Master CV entries and excludes Header and References from all AI payloads.
- [ ] Variant-only mode saves a separate Tailored Resume and never overwrites the base Resume Variant.
- [ ] Variant-only mode generates Fit Analysis text without fake numeric ATS scoring.
- [ ] Variant-only mode generates Cover Letter text without Header, References, or Master CV payload data.
- [ ] Master CV enhanced mode keeps the deterministic existing behaviour until the future real Master CV enhanced implementation.
- [ ] OpenAI mode requires a configured key and returns a friendly error when the key is missing.
- [ ] OpenAI API keys are stored through the OS keyring boundary only, never in SQLite and never in templates.
- [ ] Saving an OpenAI API key does not claim that a real provider call was tested.

## UI gates

- [ ] Settings → AI policy exposes **Use Master CV source material** and it controls the pipeline.
- [ ] Settings → Models exposes Fake / deterministic local mode and OpenAI mode.
- [ ] Settings → Models explains that model identifiers are stored in SQLite and the OpenAI key is stored in the OS keyring only.
- [ ] Settings → Models shows **Key available: yes/no** without revealing the key.
- [ ] Settings → Prompt instructions includes `fit_analysis` and does not allow section scope for Cover Letter or Fit Analysis.
- [ ] Tailored Resume review shows Fit Analysis above Base Resume Variant and Tailored Resume Preview.
- [ ] Tailored Resume review keeps Cover Letter copy and TXT download actions.

## Validation gates

- [ ] Tests do not call real OpenAI or the real OS keyring.
- [ ] `.gitignore` keeps `.env`, local app data, private profile data, and generated application artefacts ignored.
- [ ] `uv run ruff format .` passes.
- [ ] `uv run ruff check .` passes.
- [ ] `uv run pytest` passes.
- [ ] `uv run pre-commit run --all-files` passes or any environment limitation is documented.

## Profile scope release gates

- [ ] Cross-profile Resume Variant adaptation is rejected.
- [ ] Cross-profile Resume Builder and base resume export URLs are rejected.
- [ ] Cross-profile application review/export/download URLs are rejected.
- [ ] Cross-profile Master CV page/item edit/item delete URLs are rejected.
- [ ] Dashboard renders zero and non-zero activity for 10/20/30-day ranges.

- [ ] Application → New adaptation shows real Prompt Variant options and excludes inactive variants.
- [ ] Selected Prompt Variant controls resume tailoring, cover letter, and fit analysis in Variant-only mode.
