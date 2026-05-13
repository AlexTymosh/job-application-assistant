from __future__ import annotations

from difflib import unified_diff


def build_unified_diff(
    before: str,
    after: str,
    fromfile: str = "before.md",
    tofile: str = "after.md",
) -> str:
    """Build a unified diff for two Markdown strings."""
    before_lines = _normalise_line_endings(before).splitlines(keepends=True)
    after_lines = _normalise_line_endings(after).splitlines(keepends=True)

    return "".join(
        unified_diff(
            before_lines,
            after_lines,
            fromfile=fromfile,
            tofile=tofile,
        )
    )


def has_meaningful_diff(before: str, after: str) -> bool:
    """Return whether two strings differ after normalising line endings."""
    return _normalise_line_endings(before) != _normalise_line_endings(after)


def _normalise_line_endings(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")
