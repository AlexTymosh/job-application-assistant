from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import (
    LlmExtractionMode,
    ProjectConfig,
    load_profile_config,
    validate_llm_runtime_config,
)


def test_load_example_profile_config() -> None:
    config_path = Path("profiles/example/config.example.yaml")

    config = load_profile_config(config_path)

    assert config.app.profile_name == "example"
    assert config.app.data_dir == Path("profiles/example")
    assert config.cv.default_variant == "backend_developer"
    assert config.workflow.require_human_approval_before_export is True
    assert config.llm.extraction_mode is LlmExtractionMode.FAKE


def test_unresolved_llm_model_placeholders_are_normalised_to_none() -> None:
    config = load_profile_config(Path("profiles/example/config.example.yaml"))

    assert config.llm.model_extract is None
    assert config.llm.model_tailor is None
    assert config.llm.model_qa is None


def test_config_rejects_unknown_fields() -> None:
    invalid_config = {
        "app": {
            "profile_name": "example",
            "data_dir": "profiles/example",
            "unexpected": "value",
        },
        "workflow": {},
        "llm": {},
        "cv": {"default_variant": "backend_developer", "variants": []},
        "exports": {},
        "guardrails": {},
        "job_reader": {},
        "future_integrations": {},
    }

    with pytest.raises(ValidationError):
        ProjectConfig.model_validate(invalid_config)


def test_llm_extraction_mode_can_be_overridden_by_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_EXTRACTION_MODE", "openai")
    monkeypatch.setenv("OPENAI_MODEL_EXTRACT", "gpt-test")

    config = load_profile_config(Path("profiles/example/config.example.yaml"))

    assert config.llm.extraction_mode is LlmExtractionMode.OPENAI
    assert config.llm.model_extract == "gpt-test"


def test_fake_llm_runtime_mode_does_not_require_openai_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    config = load_profile_config(Path("profiles/example/config.example.yaml"))

    validate_llm_runtime_config(config)


def test_openai_llm_runtime_mode_requires_api_key_and_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    base_config = load_profile_config(Path("profiles/example/config.example.yaml"))
    config = ProjectConfig.model_validate(
        base_config.model_dump()
        | {
            "llm": base_config.llm.model_dump()
            | {"extraction_mode": "openai", "model_extract": None}
        }
    )

    with pytest.raises(ValueError, match="model_extract"):
        validate_llm_runtime_config(config)

    config = ProjectConfig.model_validate(
        base_config.model_dump()
        | {
            "llm": base_config.llm.model_dump()
            | {"extraction_mode": "openai", "model_extract": "gpt-test"}
        }
    )

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        validate_llm_runtime_config(config)
