from __future__ import annotations

from app.core.config import (
    LlmExtractionMode,
    ProjectConfig,
    validate_llm_runtime_config,
)
from app.llm.fake_client import FakeJobExtractionClient, JobExtractionClient
from app.llm.openai_client import OpenAIJobExtractionClient
from app.secrets.openai_key import (
    OpenAISecretService,
    SecretStorageError,
    get_environment_openai_api_key,
)


def build_job_extraction_client(
    config: ProjectConfig,
    *,
    openai_secret_service: OpenAISecretService | None = None,
) -> JobExtractionClient:
    """Build the configured job extraction client after runtime validation."""
    if config.llm.extraction_mode is LlmExtractionMode.FAKE:
        validate_llm_runtime_config(config, has_openai_api_key=False)
        return FakeJobExtractionClient()

    if config.llm.extraction_mode is LlmExtractionMode.OPENAI:
        api_key = _resolve_openai_api_key(openai_secret_service)
        validate_llm_runtime_config(config, has_openai_api_key=api_key is not None)
        if config.llm.model_extract is None:  # guarded by validation
            raise ValueError("OpenAI extraction model is not configured.")
        if api_key is None:  # guarded by validation
            raise ValueError("OpenAI API key is not configured.")
        return OpenAIJobExtractionClient(
            model=config.llm.model_extract,
            api_key=api_key,
        )

    raise ValueError(f"Unsupported LLM extraction mode: {config.llm.extraction_mode}")


def _resolve_openai_api_key(
    openai_secret_service: OpenAISecretService | None,
) -> str | None:
    if openai_secret_service is not None:
        try:
            keyring_key = openai_secret_service.get_api_key()
        except SecretStorageError:
            keyring_key = None
        if keyring_key is not None:
            return keyring_key
    return get_environment_openai_api_key()
