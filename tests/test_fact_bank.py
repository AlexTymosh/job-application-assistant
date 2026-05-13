from pathlib import Path

import pytest

from app.cv.fact_bank import load_fact_bank
from app.cv.models import AllowedClaimLevel, FactCategory

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_FACT_BANK = ROOT / "profiles" / "example" / "cv" / "fact_bank.example.yaml"

VALID_FACT_BANK = """
facts:
  - id: fact_python_001
    category: skill
    name: Python
    allowed_claim_level: practical
    evidence: Used in a portfolio project.
"""


def write_fact_bank(tmp_path: Path, content: str) -> Path:
    fact_bank_path = tmp_path / "fact_bank.yaml"
    fact_bank_path.write_text(content, encoding="utf-8")
    return fact_bank_path


def test_load_fact_bank_loads_example_fact_bank() -> None:
    fact_bank = load_fact_bank(EXAMPLE_FACT_BANK)

    assert len(fact_bank.facts) >= 1
    assert fact_bank.facts[0].category is FactCategory.SKILL
    assert fact_bank.facts[0].allowed_claim_level is AllowedClaimLevel.PRACTICAL


def test_load_fact_bank_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_fact_bank(tmp_path / "missing.yaml")


def test_load_fact_bank_rejects_empty_file(tmp_path: Path) -> None:
    path = write_fact_bank(tmp_path, "")

    with pytest.raises(ValueError, match="empty"):
        load_fact_bank(path)


def test_load_fact_bank_rejects_missing_facts_key(tmp_path: Path) -> None:
    path = write_fact_bank(tmp_path, "items: []\n")

    with pytest.raises(ValueError, match="facts key"):
        load_fact_bank(path)


def test_load_fact_bank_rejects_facts_that_are_not_a_list(tmp_path: Path) -> None:
    path = write_fact_bank(tmp_path, "facts: invalid\n")

    with pytest.raises(ValueError, match="must be a list"):
        load_fact_bank(path)


def test_load_fact_bank_rejects_duplicate_fact_ids(tmp_path: Path) -> None:
    path = write_fact_bank(
        tmp_path,
        """
facts:
  - id: fact_python_001
    category: skill
    name: Python
    allowed_claim_level: practical
    evidence: Used in a portfolio project.
  - id: fact_python_001
    category: skill
    name: Python again
    allowed_claim_level: practical
    evidence: Used in another portfolio project.
""",
    )

    with pytest.raises(ValueError, match="Duplicate fact IDs"):
        load_fact_bank(path)


def test_load_fact_bank_rejects_empty_fact_id(tmp_path: Path) -> None:
    path = write_fact_bank(tmp_path, VALID_FACT_BANK.replace("fact_python_001", " "))

    with pytest.raises(ValueError, match="Invalid fact bank"):
        load_fact_bank(path)


def test_load_fact_bank_rejects_empty_fact_name(tmp_path: Path) -> None:
    path = write_fact_bank(tmp_path, VALID_FACT_BANK.replace("Python", " "))

    with pytest.raises(ValueError, match="Invalid fact bank"):
        load_fact_bank(path)


def test_load_fact_bank_rejects_empty_evidence(tmp_path: Path) -> None:
    path = write_fact_bank(
        tmp_path,
        VALID_FACT_BANK.replace("Used in a portfolio project.", " "),
    )

    with pytest.raises(ValueError, match="Invalid fact bank"):
        load_fact_bank(path)


def test_load_fact_bank_rejects_unknown_category(tmp_path: Path) -> None:
    path = write_fact_bank(tmp_path, VALID_FACT_BANK.replace("skill", "unknown"))

    with pytest.raises(ValueError, match="Invalid fact bank"):
        load_fact_bank(path)


def test_load_fact_bank_rejects_unknown_allowed_claim_level(tmp_path: Path) -> None:
    path = write_fact_bank(tmp_path, VALID_FACT_BANK.replace("practical", "expert"))

    with pytest.raises(ValueError, match="Invalid fact bank"):
        load_fact_bank(path)


def test_load_fact_bank_rejects_unknown_extra_fields(tmp_path: Path) -> None:
    path = write_fact_bank(
        tmp_path,
        VALID_FACT_BANK.replace(
            "evidence: Used in a portfolio project.",
            "evidence: Used in a portfolio project.\n    notes: not allowed",
        ),
    )

    with pytest.raises(ValueError, match="Invalid fact bank"):
        load_fact_bank(path)
