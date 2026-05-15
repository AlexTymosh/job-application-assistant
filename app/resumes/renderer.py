from __future__ import annotations

from app.db.models import ProfileContact, Resume


def render_resume_markdown(
    resume: Resume,
    accepted_changes: dict[tuple[str, int], str] | None = None,
    contact: ProfileContact | None = None,
) -> str:
    accepted_changes = accepted_changes or {}
    lines: list[str] = [f"# {resume.profile.full_name or resume.profile.display_name}"]
    if contact is not None:
        contact_parts = [part for part in [contact.email, contact.phone, contact.city, contact.country] if part]
        if contact_parts:
            lines.append(" | ".join(contact_parts))
    if resume.target_role:
        lines.extend(["", f"**Target role:** {resume.target_role}"])

    for section in resume.sections:
        if not section.is_visible:
            continue
        lines.extend(["", f"## {section.title}"])
        for block in section.blocks:
            if not block.is_visible:
                continue
            title = accepted_changes.get(("resume_block_title", block.id), block.title)
            content = accepted_changes.get(("resume_block", block.id), block.content)
            if title:
                lines.append(f"### {title}")
            meta = " · ".join(part for part in [block.role_title, block.organisation, block.location] if part)
            dates = " - ".join(
                part
                for part in [
                    block.start_date,
                    "Present" if block.is_current else block.end_date,
                ]
                if part
            )
            if meta or dates:
                lines.append(" | ".join(part for part in [meta, dates] if part))
            if content:
                lines.append(content)
            for bullet in block.bullets:
                if not bullet.is_visible:
                    continue
                text = accepted_changes.get(("resume_bullet", bullet.id), bullet.text)
                if text:
                    lines.append(f"- {text}")
    return "\n".join(lines).strip() + "\n"
