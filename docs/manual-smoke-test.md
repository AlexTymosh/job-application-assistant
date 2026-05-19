# Manual Smoke Test

1. Start the app with `uv run uvicorn app.main:app --reload`.
2. Create a Profile.
3. Create a Resume Variant with Header, Summary, Skills, Work Experience, Education, and References.
4. Open Master CV and confirm only Summary, Skills, Work Experience, and Education are available.
5. Add a Master CV entry with obvious text that should be easy to spot.
6. Open Settings → AI policy.
7. Disable **Use Master CV source material**.
8. Open Settings → Models.
9. Select **Fake / deterministic local mode**.
10. Adapt a resume from Application → New adaptation.
11. Confirm a Tailored Resume is created.
12. Confirm Fit Analysis appears above Base Resume Variant and Tailored Resume Preview.
13. Confirm Cover Letter appears and TXT download works.
14. Confirm Header and References appear in local preview/export, but are covered by tests that assert they are not sent to AI payloads.
15. Confirm the obvious Master CV text is not used in Variant-only mode.
16. Select OpenAI mode without a key.
17. Adapt again and confirm the app shows a friendly error telling the user to add an OpenAI API key.
18. Save an OpenAI key through Settings → Models.
19. Confirm **Key available: yes** appears and the key is not printed or revealed.
20. If manually testing real OpenAI, use a disposable test key and verify the app performs section-by-section adaptation.

## Regression smoke areas

- Master CV enhanced mode still runs the deterministic Master CV-enhanced flow when **Use Master CV source material** is enabled.
- Variant-only mode does not run fact-checking, hallucination validation, evidence matrices, or fake numeric ATS scoring.
- The base Resume Variant remains unchanged after adaptation.
- PDF and DOCX exports work for both base and tailored resumes.
- Tests use fake clients and do not call real OpenAI or the real OS keyring.

21. On Application → New adaptation, choose a custom Prompt Variant and confirm its prompt text is reflected in resume tailoring, cover letter, and fit analysis behaviour (covered by automated tests).
