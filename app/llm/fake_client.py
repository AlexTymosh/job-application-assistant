from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeJobExtractionClient:
    captured_texts: list[str] = field(default_factory=list)

    def extract(self, raw_job_text: str) -> list[dict[str, Any]]:
        self.captured_texts.append(raw_job_text)
        keywords = [
            word.strip(",.").lower() for word in raw_job_text.split() if len(word) > 3
        ]
        return [
            {
                "requirement_type": "keyword",
                "text": keyword,
                "keywords": [keyword],
                "priority": 3,
            }
            for keyword in keywords[:5]
        ]


@dataclass
class FakeCoverLetterClient:
    captured_payloads: list[dict[str, Any]] = field(default_factory=list)

    def draft(self, payload: dict[str, Any]) -> str:
        self.captured_payloads.append(payload)
        return (
            "Thank you for considering my application. The attached tailored "
            "resume highlights relevant experience for this role."
        )
