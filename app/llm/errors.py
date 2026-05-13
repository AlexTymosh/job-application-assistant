from __future__ import annotations


class LlmError(Exception):
    """Base exception for LLM contract failures."""


class JobExtractionError(LlmError):
    """Raised when structured job extraction cannot be completed."""


class JobExtractionValidationError(JobExtractionError):
    """Raised when extracted job data fails schema validation."""


class OpenAIExtractionError(JobExtractionError):
    """Raised when the OpenAI extraction client cannot complete extraction."""


class OpenAIExtractionRefusalError(OpenAIExtractionError):
    """Raised when OpenAI refuses to provide a structured extraction response."""


class OpenAIExtractionResponseError(OpenAIExtractionError):
    """Raised when OpenAI returns no usable parsed extraction response."""
