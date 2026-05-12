from pathlib import Path

from app.core.config import load_profile_config


def test_load_example_profile_config() -> None:
    config_path = Path("profiles/example/config.example.yaml")

    config = load_profile_config(config_path)

    assert config.app.profile_name == "example"
    assert config.app.data_dir == Path("profiles/example")
    assert config.cv.default_variant == "backend_developer"
    assert config.workflow.require_human_approval_before_export is True
