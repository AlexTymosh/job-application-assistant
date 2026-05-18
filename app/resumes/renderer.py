from __future__ import annotations

from html import escape
from typing import Any

from app.db.models import Resume

SECTION_ORDER = [
    "header",
    "summary",
    "skills",
    "work_experience",
    "education",
    "languages",
    "certificates",
    "references",
]
SECTION_TITLES = {
    "summary": "Summary",
    "skills": "Skills",
    "work_experience": "Work Experience",
    "education": "Education",
    "languages": "Languages",
    "certificates": "Certificates",
    "references": "References",
}


def resume_to_content(resume: Resume) -> dict[str, Any]:
    sections: dict[str, Any] = {}
    for section in sorted(resume.sections, key=lambda item: item.display_order):
        if not section.is_visible:
            continue
        blocks = [block for block in section.blocks if block.is_visible]
        if section.section_type == "header":
            block = blocks[0] if blocks else None
            sections["header"] = dict(block.metadata_json or {}) if block else {}
        elif section.section_type == "summary":
            sections["summary"] = {"text": blocks[0].content if blocks else ""}
        elif section.section_type == "skills":
            hard = next(
                (block.content for block in blocks if block.title == "Hard Skills"), ""
            )
            soft = next(
                (block.content for block in blocks if block.title == "Soft Skills"), ""
            )
            sections["skills"] = {"hard": hard, "soft": soft}
        elif section.section_type == "work_experience":
            sections["work_experience"] = [block_to_dict(block) for block in blocks]
        elif section.section_type == "education":
            sections["education"] = [block_to_dict(block) for block in blocks]
        elif section.section_type in {"languages", "certificates", "references"}:
            sections[section.section_type] = [block_to_dict(block) for block in blocks]
    return {
        "resume_id": resume.id,
        "name": resume.name,
        "target_role": resume.target_role,
        "sections": sections,
    }


def block_to_dict(block) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    data = dict(block.metadata_json or {})
    data.update(
        {
            "id": block.id,
            "title": block.title,
            "subtitle": block.subtitle,
            "organisation": block.organisation,
            "role_title": block.role_title,
            "location": block.location,
            "start_date": block.start_date,
            "end_date": block.end_date,
            "is_current": block.is_current,
            "optional_extra_enabled": block.optional_extra_enabled,
            "optional_extra_text": block.optional_extra_text,
            "content": block.content,
        }
    )
    return data


def render_resume_markdown_from_content(content: dict[str, Any]) -> str:
    sections = content.get("sections", {})
    header = sections.get("header", {})
    lines: list[str] = []
    name = " ".join(
        part
        for part in [header.get("first_name", ""), header.get("surname", "")]
        if part
    ).strip() or content.get("name", "Resume")
    lines.append(f"# {name}")
    if content.get("target_role"):
        lines.append(content["target_role"])
    contact_parts = [
        header.get("phone", ""),
        header.get("email", ""),
        header.get("linkedin_url", ""),
        header.get("github_url", ""),
        header.get("website_url") or header.get("personal_website_url", ""),
        header.get("location", ""),
        header.get("extra_text", ""),
    ]
    contact_line = " • ".join(part for part in contact_parts if part)
    if contact_line:
        lines.append(contact_line)
    summary = sections.get("summary", {}).get("text", "").strip()
    if summary:
        lines.extend(["", summary])
    skills = sections.get("skills", {})
    if skills.get("hard") or skills.get("soft"):
        lines.extend(["", "## Skills"])
        if skills.get("hard"):
            lines.append(f"**Hard Skills:** {skills['hard']}")
        if skills.get("soft"):
            lines.append(f"**Soft Skills:** {skills['soft']}")
    _append_experience(lines, sections.get("work_experience", []), "Work Experience")
    _append_education(lines, sections.get("education", []))
    _append_rows(
        lines,
        sections.get("languages", []),
        "Languages",
        lambda row: _language_line(row),
    )
    _append_rows(
        lines, sections.get("certificates", []), "Certificates", _certificate_line
    )
    _append_rows(lines, sections.get("references", []), "References", _reference_line)
    return "\n".join(line for line in lines if line is not None).strip() + "\n"


def render_resume_markdown(resume: Resume) -> str:
    return render_resume_markdown_from_content(resume_to_content(resume))


def render_resume_html_from_content(content: dict[str, Any]) -> str:
    markdown = render_resume_markdown_from_content(content)
    html_lines = ['<article class="resume-preview-paper">']
    in_list = False
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            continue
        if line.startswith("# "):
            html_lines.append(f"<h1>{escape(line[2:])}</h1>")
        elif line.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h2>{escape(line[3:].upper())}</h2>")
        elif line.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{escape(line[2:])}</li>")
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<p>{escape(line)}</p>")
    if in_list:
        html_lines.append("</ul>")
    html_lines.append("</article>")
    return "\n".join(html_lines)


def render_resume_html(resume: Resume) -> str:
    return render_resume_html_from_content(resume_to_content(resume))


def _append_experience(
    lines: list[str], items: list[dict[str, Any]], title: str
) -> None:
    visible = [
        item
        for item in items
        if any([item.get("role_title"), item.get("organisation"), item.get("content")])
    ]
    if not visible:
        return
    lines.extend(["", f"## {title}"])
    for item in visible:
        heading = " at ".join(
            part for part in [item.get("role_title"), item.get("organisation")] if part
        )
        if heading:
            lines.append(heading)
        period = _period(item)
        if period:
            lines.append(period)
        if item.get("optional_extra_enabled") and item.get("optional_extra_text"):
            lines.append(item["optional_extra_text"])
        _append_bullets(lines, item.get("content", ""))


def _append_education(lines: list[str], items: list[dict[str, Any]]) -> None:
    visible = [
        item
        for item in items
        if any([item.get("organisation"), item.get("role_title"), item.get("content")])
    ]
    if not visible:
        return
    lines.extend(["", "## Education"])
    for item in visible:
        heading = " — ".join(
            part for part in [item.get("organisation"), item.get("role_title")] if part
        )
        if heading:
            lines.append(heading)
        period = _period(item)
        if period:
            lines.append(period)
        _append_bullets(lines, item.get("content", ""))


def _append_rows(
    lines: list[str], rows: list[dict[str, Any]], title: str, formatter
) -> None:  # type: ignore[no-untyped-def]
    rendered = [formatter(row).strip() for row in rows]
    rendered = [item for item in rendered if item and item != "()"]
    if not rendered:
        return
    lines.extend(["", f"## {title}"])
    for item in rendered:
        lines.append(f"- {item}")


def _language_line(row: dict[str, Any]) -> str:
    language = row.get("language", row.get("title", ""))
    level = row.get("level", row.get("subtitle", ""))
    return f"{language} ({level})".strip()


def _certificate_line(row: dict[str, Any]) -> str:
    parts = [row.get("certificate_name", row.get("title", ""))]
    if row.get("issue_year"):
        parts.append(str(row["issue_year"]))
    text = " | ".join(part for part in parts if part)
    if row.get("certificate_url"):
        text = f"{text} — {row['certificate_url']}"
    return text


def _reference_line(row: dict[str, Any]) -> str:
    name = row.get("name", row.get("title", ""))
    role_company = ", ".join(
        part for part in [row.get("role_title", ""), row.get("company", "")] if part
    )
    contact = " • ".join(
        part
        for part in [
            row.get("phone", ""),
            row.get("email", ""),
            row.get("linkedin_url", ""),
        ]
        if part
    )
    return " — ".join(part for part in [name, role_company, contact] if part)


def _period(item: dict[str, Any]) -> str:
    start = item.get("start_date", "")
    end = "Current" if item.get("is_current") else item.get("end_date", "")
    return " – ".join(part for part in [start, end] if part)


def _append_bullets(lines: list[str], text: str) -> None:
    for raw in text.splitlines():
        bullet = raw.strip().lstrip("-• ").strip()
        if bullet:
            lines.append(f"- {bullet}")
