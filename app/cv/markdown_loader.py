from __future__ import annotations

from pathlib import Path


def load_markdown_file(path: Path) -> str:
    """Load a non-empty UTF-8 Markdown file without mutating it."""
    if not path.exists():
        raise FileNotFoundError(f"Markdown file not found: {path}")

    if not path.is_file():
        raise ValueError(f"Markdown path is not a file: {path}")

    markdown = path.read_text(encoding="utf-8")

    if not markdown.strip():
        raise ValueError(f"Markdown file is empty or whitespace-only: {path}")

    return markdown
