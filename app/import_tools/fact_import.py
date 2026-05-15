from __future__ import annotations

from pathlib import Path

from app.cv.fact_bank import load_fact_bank
from app.import_tools.models import PlannedFact


def load_planned_facts(profile_name: str, profile_dir: Path) -> list[PlannedFact]:
    fact_bank_path = profile_dir / "cv" / _fact_bank_filename(profile_name)
    fact_bank = load_fact_bank(fact_bank_path)
    return [
        PlannedFact(
            fact_key=fact.id,
            category=fact.category,
            name=fact.name,
            allowed_claim_level=fact.allowed_claim_level,
            evidence=fact.evidence,
            is_active=True,
            action="create",
        )
        for fact in fact_bank.facts
    ]


def _fact_bank_filename(profile_name: str) -> str:
    return "fact_bank.example.yaml" if profile_name == "example" else "fact_bank.yaml"
