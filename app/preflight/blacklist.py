from __future__ import annotations

from pathlib import Path


def load_blacklist_entries(path: Path) -> list[str]:
    if not path.is_file():
        return []

    entries = []

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped_line = line.strip()

        if not stripped_line or stripped_line.startswith("#"):
            continue

        entries.append(stripped_line.lower())

    return entries


def find_blacklist_matches(*, text: str, entries: list[str]) -> list[str]:
    lowered_text = text.lower()

    return [entry for entry in entries if entry in lowered_text]
