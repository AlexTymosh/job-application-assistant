from __future__ import annotations

from app.db.models import ProfileContact, Resume, ResumeBlock


def render_resume_markdown(
    resume: Resume,
    accepted_changes: dict[tuple[str, int], str] | None = None,
    contact: ProfileContact | None = None,
) -> str:
    accepted_changes = accepted_changes or {}

    lines: list[str] = [f"# {resume.profile.full_name or resume.profile.display_name}"]

    if contact is not None:
        contact_parts = [
            part
            for part in [
                contact.email,
                contact.phone,
                contact.city,
                contact.country,
            ]
            if part
        ]
        if contact_parts:
            lines.append(" | ".join(contact_parts))

    if resume.target_role:
        lines.extend(["", f"**Target role:** {resume.target_role}"])

    for section in resume.sections:
        if not section.is_visible:
            continue
        visible_blocks = [
            block
            for block in section.blocks
            if block.is_visible
            and _block_has_meaningful_content(block, accepted_changes)
        ]
        if not visible_blocks:
            continue

        lines.extend(["", f"## {section.title.upper()}"])

        for block in visible_blocks:
            title = accepted_changes.get(("resume_block_title", block.id), block.title)

            if block.block_type == "skills":
                content = accepted_changes.get(
                    ("skills_set", block.id),
                    accepted_changes.get(("resume_block", block.id), block.content),
                )
            else:
                content = accepted_changes.get(
                    ("resume_block", block.id), block.content
                )

            if title:
                lines.append(f"### {title}")

            meta = " · ".join(
                part
                for part in [
                    block.role_title,
                    block.organisation,
                    block.location,
                ]
                if part
            )

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


def _block_has_meaningful_content(
    block: ResumeBlock, accepted_changes: dict[tuple[str, int], str]
) -> bool:
    changed_title = accepted_changes.get(("resume_block_title", block.id), block.title)
    changed_content = accepted_changes.get(
        ("skills_set", block.id),
        accepted_changes.get(("resume_block", block.id), block.content),
    )
    title_is_content = block.block_type in {"custom", "title", "project", "education"}
    return any(
        str(value).strip()
        for value in [
            changed_title if title_is_content else "",
            changed_content,
            block.subtitle,
            block.role_title,
            block.organisation,
            block.location,
            block.start_date,
            block.end_date,
        ]
    ) or any(
        bullet.is_visible
        and accepted_changes.get(("resume_bullet", bullet.id), bullet.text).strip()
        for bullet in block.bullets
    )
