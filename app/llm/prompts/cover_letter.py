from __future__ import annotations

from typing import Any


def build_cover_letter_payload(
    *, tailored_resume: str, job_description: str
) -> dict[str, Any]:
    return {
        "instruction": (
            "Draft a concise cover letter using only supplied resume content."
        ),
        "tailored_resume": tailored_resume,
        "job_description": job_description,
    }
