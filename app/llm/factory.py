from __future__ import annotations

from app.core.config import (
    LlmExtractionMode,
    ProjectConfig,
    validate_llm_runtime_config,
)
from app.llm.fake_client import FakeJobExtractionClient, JobExtractionClient
from app.llm.openai_client import OpenAIJobExtractionClient


def build_job_extraction_client(config: ProjectConfig) -> JobExtractionClient:
    """Build the configured job extraction client after runtime validation."""
    validate_llm_runtime_config(config)

    if config.llm.extraction_mode is LlmExtractionMode.FAKE:
        return FakeJobExtractionClient()

    if config.llm.extraction_mode is LlmExtractionMode.OPENAI:
        if config.llm.model_extract is None:  # guarded by validation
            raise ValueError("OpenAI extraction model is not configured.")
        return OpenAIJobExtractionClient(model=config.llm.model_extract)

    raise ValueError(f"Unsupported LLM extraction mode: {config.llm.extraction_mode}")
