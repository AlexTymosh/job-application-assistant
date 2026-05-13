from __future__ import annotations


class MarkdownExporter:
    """Prepare tailored CV Markdown for artefact persistence."""

    def export(self, markdown: str) -> str:
        if not markdown.strip():
            raise ValueError("Markdown export content must not be empty.")

        return f"{markdown.rstrip('\n')}\n"
