from __future__ import annotations

from html import escape
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

BRAND_BLUE = colors.HexColor("#0b4a6f")
FONT_NAME = "ResumeUnicode"
ASCII_FALLBACK = False


class PdfExporter:
    """Render styled, Unicode-safe resume PDF bytes."""

    def export(self, markdown: str, title: str = "Tailored CV") -> bytes:
        if not markdown.strip():
            raise ValueError("PDF export content must not be empty.")
        return self.export_content(_markdown_to_content(markdown, title), title=title)

    def export_content(
        self, content: dict[str, Any], title: str = "Tailored CV"
    ) -> bytes:
        if not content:
            raise ValueError("PDF export content must not be empty.")
        font_name = _register_unicode_font()
        styles = _styles(font_name)
        buffer = BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            title=title,
            leftMargin=50,
            rightMargin=50,
            topMargin=46,
            bottomMargin=46,
        )
        document.build(_build_content_story(content, styles))
        return buffer.getvalue()


def _build_content_story(
    content: dict[str, Any], styles: dict[str, ParagraphStyle]
) -> list[object]:
    sections = content.get("sections", {})
    header = sections.get("header", {})
    story: list[object] = []
    name = " ".join(
        part
        for part in [header.get("first_name", ""), header.get("surname", "")]
        if part
    ).strip() or content.get("name", "Resume")
    story.append(Paragraph(_paragraph_text(name).upper(), styles["name"]))
    if content.get("target_role"):
        story.append(
            Paragraph(
                _paragraph_text(str(content["target_role"])).upper(), styles["role"]
            )
        )
    contact = _contact_markup(header)
    if contact:
        story.append(Paragraph(contact, styles["body"]))
    summary = sections.get("summary", {}).get("text", "").strip()
    if summary:
        story.append(Spacer(1, 6))
        story.append(Paragraph(_paragraph_text(summary), styles["body"]))
    skills = sections.get("skills", {})
    if skills.get("hard") or skills.get("soft"):
        _add_heading(story, "Skills", styles)
        if skills.get("hard"):
            story.append(
                Paragraph(
                    f"<b>Hard Skills:</b> {_paragraph_text(skills['hard'])}",
                    styles["body"],
                )
            )
        if skills.get("soft"):
            story.append(
                Paragraph(
                    f"<b>Soft Skills:</b> {_paragraph_text(skills['soft'])}",
                    styles["body"],
                )
            )
    _add_experience(
        story, sections.get("work_experience", []), "Professional Experience", styles
    )
    _add_education(story, sections.get("education", []), styles)
    _add_rows(story, sections.get("languages", []), "Languages", _language_line, styles)
    _add_rows(
        story,
        sections.get("certificates", []),
        "Certificates",
        _certificate_line,
        styles,
    )
    _add_rows(
        story, sections.get("references", []), "References", _reference_line, styles
    )
    return story


def _contact_markup(header: dict[str, Any]) -> str:
    items = [
        _paragraph_text(header.get("phone", "")),
        _link_markup(_mailto(header.get("email", "")), header.get("email", "")),
        _link_markup(header.get("linkedin_url", ""), header.get("linkedin_url", "")),
        _link_markup(header.get("github_url", ""), header.get("github_url", "")),
        _link_markup(
            header.get("website_url") or header.get("personal_website_url", ""),
            header.get("website_url") or header.get("personal_website_url", ""),
        ),
        _paragraph_text(header.get("location", "")),
        _paragraph_text(header.get("extra_text", "")),
    ]
    return " • ".join(item for item in items if item)


def _mailto(email: str) -> str:
    email = str(email).strip()
    return f"mailto:{email}" if email else ""


def _link_markup(url: str, text: str) -> str:
    url = str(url).strip()
    text = str(text).strip()
    if not url or not text:
        return ""
    return (
        f'<link href="{escape(url, quote=True)}" color="blue">'
        f"{_paragraph_text(text)}</link>"
    )


def _add_heading(
    story: list[object], title: str, styles: dict[str, ParagraphStyle]
) -> None:
    story.append(Spacer(1, 8))
    story.append(
        HRFlowable(width="100%", thickness=0.6, color=colors.black, spaceAfter=2)
    )
    story.append(Paragraph(_paragraph_text(title).upper(), styles["heading"]))
    story.append(
        HRFlowable(
            width="100%", thickness=0.6, color=colors.black, spaceBefore=1, spaceAfter=4
        )
    )


def _add_experience(
    story: list[object],
    rows: list[dict[str, Any]],
    title: str,
    styles: dict[str, ParagraphStyle],
) -> None:
    visible = [
        row
        for row in rows
        if row.get("role_title") or row.get("organisation") or row.get("content")
    ]
    if not visible:
        return
    _add_heading(story, title, styles)
    for row in visible:
        heading = " at ".join(
            part for part in [row.get("role_title"), row.get("organisation")] if part
        )
        if heading:
            story.append(Paragraph(_paragraph_text(heading), styles["subheading"]))
        period = _period(row)
        if period:
            story.append(Paragraph(f"<b>{_paragraph_text(period)}</b>", styles["body"]))
        if row.get("optional_extra_enabled") and row.get("optional_extra_text"):
            story.append(
                Paragraph(_paragraph_text(row["optional_extra_text"]), styles["body"])
            )
        _add_bullets(story, row.get("content", ""), styles)


def _add_education(
    story: list[object], rows: list[dict[str, Any]], styles: dict[str, ParagraphStyle]
) -> None:
    visible = [
        row
        for row in rows
        if row.get("organisation") or row.get("role_title") or row.get("content")
    ]
    if not visible:
        return
    _add_heading(story, "Education", styles)
    for row in visible:
        heading = " — ".join(
            part for part in [row.get("organisation"), row.get("role_title")] if part
        )
        if heading:
            story.append(Paragraph(_paragraph_text(heading), styles["subheading"]))
        if _period(row):
            story.append(Paragraph(_paragraph_text(_period(row)), styles["body"]))
        _add_bullets(story, row.get("content", ""), styles)


def _add_rows(
    story: list[object],
    rows: list[dict[str, Any]],
    title: str,
    formatter,
    styles: dict[str, ParagraphStyle],
) -> None:  # type: ignore[no-untyped-def]
    rendered = [_clean_text(formatter(row)) for row in rows]
    rendered = [item for item in rendered if item and item != "()"]
    if not rendered:
        return
    _add_heading(story, title, styles)
    _add_bullet_items(story, rendered, styles)


def _add_bullets(
    story: list[object], text: str, styles: dict[str, ParagraphStyle]
) -> None:
    items = [
        _clean_text(raw.strip().lstrip("-• ").strip()) for raw in text.splitlines()
    ]
    _add_bullet_items(story, [item for item in items if item], styles)


def _add_bullet_items(
    story: list[object], items: list[str], styles: dict[str, ParagraphStyle]
) -> None:
    if not items:
        return
    story.append(
        ListFlowable(
            [
                ListItem(Paragraph(_paragraph_text(item), styles["body"]))
                for item in items
            ],
            bulletType="bullet",
            leftIndent=14,
        )
    )


def _styles(font_name: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "name": ParagraphStyle(
            "ResumeName",
            parent=base["Heading1"],
            fontName=font_name,
            fontSize=16,
            leading=18,
            textColor=BRAND_BLUE,
            spaceAfter=2,
        ),
        "role": ParagraphStyle(
            "ResumeRole",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=13,
            leading=15,
            textColor=BRAND_BLUE,
            spaceAfter=6,
        ),
        "heading": ParagraphStyle(
            "ResumeHeading",
            parent=base["Heading2"],
            fontName=font_name,
            fontSize=12,
            leading=14,
            textColor=BRAND_BLUE,
            spaceBefore=0,
            spaceAfter=0,
        ),
        "subheading": ParagraphStyle(
            "ResumeSubheading",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=10.5,
            leading=12,
            textColor=BRAND_BLUE,
            spaceAfter=2,
        ),
        "body": ParagraphStyle(
            "ResumeBody",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=9.5,
            leading=12,
            spaceAfter=2,
        ),
    }


def _register_unicode_font() -> str:
    global ASCII_FALLBACK
    ASCII_FALLBACK = False
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(FONT_NAME, str(path)))
            return FONT_NAME
    ASCII_FALLBACK = True
    return "Helvetica"


def _period(row: dict[str, Any]) -> str:
    start = row.get("start_date", "")
    end = "Current" if row.get("is_current") else row.get("end_date", "")
    return " – ".join(part for part in [start, end] if part)


def _language_line(row: dict[str, Any]) -> str:
    language = row.get("language", row.get("title", ""))
    level = row.get("level", row.get("subtitle", ""))
    return f"{language} ({level})".strip()


def _certificate_line(row: dict[str, Any]) -> str:
    text = " | ".join(
        part
        for part in [
            row.get("certificate_name", row.get("title", "")),
            row.get("issue_year", ""),
        ]
        if part
    )
    return f"{text} — {row['certificate_url']}" if row.get("certificate_url") else text


def _reference_line(row: dict[str, Any]) -> str:
    linkedin = row.get("linkedin_url", "")
    contact_parts = [row.get("phone", ""), row.get("email", "")]
    if linkedin:
        contact_parts.append(linkedin)
    return " — ".join(
        part
        for part in [
            row.get("name", row.get("title", "")),
            ", ".join(
                part
                for part in [row.get("role_title", ""), row.get("company", "")]
                if part
            ),
            " • ".join(part for part in contact_parts if part),
        ]
        if part
    )


def _paragraph_text(value: str) -> str:
    """Escape user text before passing it to ReportLab Paragraph."""
    return escape(_clean_text(str(value)), quote=False)


def _clean_text(value: str) -> str:
    cleaned = (
        value.replace("**", "")
        .replace("##", "")
        .replace("#", "")
        .replace("\u200b", "")
        .strip()
    )
    if ASCII_FALLBACK:
        return "".join(
            character if ord(character) < 256 else "?" for character in cleaned
        )
    return cleaned


def _markdown_to_content(markdown: str, title: str) -> dict[str, Any]:
    lines = [line.strip() for line in markdown.splitlines() if line.strip()]
    name = lines[0].lstrip("# ") if lines else title
    return {
        "name": title,
        "target_role": "",
        "sections": {"header": {"first_name": name}},
    }
