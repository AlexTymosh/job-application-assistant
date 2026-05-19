Goal:
Create a concise British English cover letter based on the pasted job description and the safe resume content provided by the application.

Task:
1. Analyse the job description and identify what kind of candidate the employer is looking for.
2. Identify the candidate’s most relevant strengths, skills, and experience from the provided resume content only.
3. If the job description clearly contains a recruiter, hiring manager, department, or team name, use it in the greeting. Otherwise use: "Dear Hiring Team,"
4. Write a short cover letter that connects the candidate’s relevant experience to the role.
5. Keep the tone professional, direct, human, and natural.
6. Keep the letter suitable for manual review and editing by the user.

Context:
The user is applying for a job. The application provides safe resume content without Header, References, contact details, phone, email, LinkedIn, GitHub, or website. Do not ask for or include these details.

Rules:
1. Use British English only.
2. Use a professional but natural business tone.
3. Maximum length: 1000 characters including greeting and sign-off.
4. Prefer three short paragraphs.
5. Use only facts present in the provided resume content.
6. Do not invent experience, employers, technologies, achievements, names, dates, or qualifications.
7. Do not use placeholders such as [Your Name], [Company], [Phone], [Email], or similar.
8. Do not include phone, email, address, LinkedIn, GitHub, website, or references.
9. Do not use clichés such as "I am excited to apply", "perfect fit", "dynamic team", "proven track record", or "hit the ground running".
10. Do not use em dashes or en dashes. Avoid these characters: "—" and "–".
11. Avoid American spelling.
12. Do not write in an obviously AI-generated style.
13. If there is not enough evidence in the resume for a claim, do not include that claim.
14. End with "Kind regards," only. The application may add the candidate’s name locally.

Output format:
Return JSON only.
Do not use Markdown.
Do not wrap the response in ```json.
Do not include any text before or after the JSON.

Return exactly this structure:

{
  "cover_letter": "string"
}


