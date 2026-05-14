from __future__ import annotations

SUSPICIOUS_PHRASES = (
    "ignore previous instructions",
    "forget your rules",
    "system prompt",
    "developer message",
    "act as chatgpt",
    "act as an ai",
    "act as a system",
    "override instructions",
    "reveal hidden prompt",
    "disregard previous",
    "you are chatgpt",
    "hidden instructions",
)


def detect_prompt_injection_phrases(text: str) -> list[str]:
    lowered_text = text.lower()

    return [phrase for phrase in SUSPICIOUS_PHRASES if phrase in lowered_text]
