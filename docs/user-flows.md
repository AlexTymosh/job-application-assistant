# User Flows

## Main workflow

1. Create or select a Profile.
2. Add AI-safe source material to the Master CV when using Master CV enhanced mode.
3. Create one or more Resume Variants for target roles.
4. Open Application and paste a job description.
5. Select the Resume Variant to adapt.
6. The app creates an Application, saves a separate Tailored Resume, generates Fit Analysis, and generates a Cover Letter draft.
7. Review Fit Analysis, Base Resume preview, Tailored Resume preview, and Cover Letter, then export PDF/DOCX or download the cover letter TXT.

## Tailoring modes

### Variant-only mode

Disable **Use Master CV source material** in Settings → AI policy. The app uses only the selected Resume Variant and the pasted job description. Master CV entries are not loaded for the AI payload and are not sent to the AI client. Header and References are excluded from every AI payload, then reattached locally from the base Resume Variant for preview/export.

Variant-only mode runs separate AI tasks for Summary, Skills, Work Experience bullets, Education achievements, Cover Letter, and Fit Analysis. It does not run fact-checking, hallucination validation, evidence matrices, source-claim validation, or fake numeric ATS scoring. The user must review the result.

### Master CV enhanced mode

Enable **Use Master CV source material**. The app keeps the current deterministic Master CV-enhanced tailoring behaviour, using the selected Resume Variant plus AI-safe Master CV source material. The real OpenAI Master CV enhanced flow is planned for a future implementation.

## CV Builder workflow

The builder shows left section navigation, a central section editor, and a right live preview. Each section has only relevant fields. Header supports optional email, phone, LinkedIn, GitHub, Website, location, and extra text. Header, Languages, Certificates, and References have no AI controls in the main editor. Work Experience and Education allow AI only for key bullet/achievement text.

Exports include private contact details only during final rendering/export. DOCX uses Word Heading 1 for candidate name/title, Heading 2 for major sections including WORK EXPERIENCE, and Heading 3 for skill groups and work/education entries. Email, LinkedIn, GitHub, Website, and reference LinkedIn links are rendered as links where supported, including ReportLab PDF links where practical.

## Master CV workflow

Master CV is not a full resume builder clone. It captures only source material that can be used by Master CV enhanced tailoring: Summary source material, Hard/Soft Skills, Work Experience key/source bullets, and Education key bullets and achievements.

Header, Languages, Certificates, References, and private contact details belong to Resume Builder only. Legacy private Master CV rows from old pre-release databases are hidden from Master CV UI pages and excluded from AI payloads. Master CV items can be edited or deleted from the builder-style page; deletion requires a visible confirmation checkbox.

## Application review workflow

Adapt Resume automatically creates the Application, Tailored Resume, Fit Analysis, and Cover Letter, then redirects to the Tailored Resume review page. The review page contains:

- Fit Analysis above the comparison;
- Base Resume preview;
- Tailored Resume preview;
- Cover Letter block with copy and TXT download actions;
- resume PDF/DOCX export buttons.

The current UI does not expose raw Tailored Resume editing. Future section-based editing should be implemented separately if needed.

## Fix-up workflow guarantees

- Application pages, adaptation, exports, and downloads require an active profile and must belong to that active profile.
- Master CV uses a builder-style layout with left navigation, central editor, and AI source preview.
- Settings profile actions are shown in compact rows and keep typed profile-name deletion confirmation.
- Dashboard chart background and activity bars use flat colours without gradients while keeping range switching and date/count axes.
