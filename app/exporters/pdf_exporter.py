from __future__ import annotations

from html import escape
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


class PdfExporter:
    """Render a conservative Markdown subset as PDF bytes."""

    def export(self, markdown: str, title: str = "Tailored CV") -> bytes:
        if not markdown.strip():
            raise ValueError("PDF export content must not be empty.")

        buffer = BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            title=title,
            leftMargin=50,
            rightMargin=50,
            topMargin=50,
            bottomMargin=50,
        )
        document.build(_build_story(markdown))
        return buffer.getvalue()


def _build_story(markdown: str) -> list[object]:
    styles = getSampleStyleSheet()
    story: list[object] = []
    paragraph_lines: list[str] = []
    list_items: list[str] = []

    def add_spacer(height: int = 8) -> None:
        if story:
            story.append(Spacer(1, height))

    def flush_paragraph() -> None:
        if paragraph_lines:
            text = " ".join(line.strip() for line in paragraph_lines)
            add_spacer()
            story.append(Paragraph(escape(text), styles["BodyText"]))
            paragraph_lines.clear()

    def flush_list() -> None:
        if list_items:
            add_spacer()
            items = [
                ListItem(Paragraph(escape(item), styles["BodyText"]))
                for item in list_items
            ]
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=18))
            list_items.clear()

    for raw_line in markdown.splitlines():
        line = raw_line.strip()

        if not line:
            flush_paragraph()
            flush_list()
            continue

        if line.startswith("## "):
            flush_paragraph()
            flush_list()
            add_spacer(10)
            story.append(Paragraph(escape(line[3:].strip()), styles["Heading2"]))
            continue

        if line.startswith("# "):
            flush_paragraph()
            flush_list()
            add_spacer(12)
            story.append(Paragraph(escape(line[2:].strip()), styles["Heading1"]))
            continue

        if line.startswith("- "):
            flush_paragraph()
            list_items.append(line[2:].strip())
            continue

        flush_list()
        paragraph_lines.append(line)

    flush_paragraph()
    flush_list()

    return story
