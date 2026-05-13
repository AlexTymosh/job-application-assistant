from __future__ import annotations


class LlmError(Exception):
    """Base exception for LLM contract failures."""


class JobExtractionError(LlmError):
    """Raised when structured job extraction cannot be completed."""


class JobExtractionValidationError(JobExtractionError):
    """Raised when extracted job data fails schema validation."""
