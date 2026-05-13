from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from app.cv.models import FactBank


def load_fact_bank(path: Path) -> FactBank:
    """Load and validate a YAML fact bank without mutating the source file."""
    if not path.exists():
        raise FileNotFoundError(f"Fact bank file not found: {path}")

    if not path.is_file():
        raise ValueError(f"Fact bank path is not a file: {path}")

    raw_content = path.read_text(encoding="utf-8")
    if not raw_content.strip():
        raise ValueError(f"Fact bank file is empty: {path}")

    loaded_data = yaml.safe_load(raw_content)
    if loaded_data is None:
        raise ValueError(f"Fact bank file is empty: {path}")

    if not isinstance(loaded_data, dict):
        raise ValueError("Fact bank must be a YAML mapping with a top-level facts key.")

    if "facts" not in loaded_data:
        raise ValueError("Fact bank must contain a top-level facts key.")

    if not isinstance(loaded_data["facts"], list):
        raise ValueError("Fact bank facts value must be a list.")

    try:
        fact_bank = FactBank.model_validate(loaded_data)
    except ValidationError as exc:
        raise ValueError(f"Invalid fact bank: {exc}") from exc

    _reject_duplicate_fact_ids(fact_bank)

    return fact_bank


def _reject_duplicate_fact_ids(fact_bank: FactBank) -> None:
    seen_fact_ids: set[str] = set()
    duplicate_fact_ids: list[str] = []

    for fact in fact_bank.facts:
        if fact.id in seen_fact_ids:
            duplicate_fact_ids.append(fact.id)
            continue

        seen_fact_ids.add(fact.id)

    if duplicate_fact_ids:
        duplicates = ", ".join(sorted(set(duplicate_fact_ids)))
        raise ValueError(f"Duplicate fact IDs found: {duplicates}")
