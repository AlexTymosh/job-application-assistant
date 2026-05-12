from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import ProjectConfig, load_profile_config


def test_load_example_profile_config() -> None:
    config_path = Path("profiles/example/config.example.yaml")

    config = load_profile_config(config_path)

    assert config.app.profile_name == "example"
    assert config.app.data_dir == Path("profiles/example")
    assert config.cv.default_variant == "backend_developer"
    assert config.workflow.require_human_approval_before_export is True


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
