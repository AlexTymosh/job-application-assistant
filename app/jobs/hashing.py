from __future__ import annotations

import hashlib


def normalise_text_for_hashing(text: str) -> str:
    return " ".join(text.strip().split())


def build_job_text_hash(text: str) -> str:
    normalised_text = normalise_text_for_hashing(text)

    return hashlib.sha256(normalised_text.encode("utf-8")).hexdigest()
