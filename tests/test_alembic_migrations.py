from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command

ROOT = Path(__file__).resolve().parents[1]


def test_alembic_upgrade_head_creates_profile_database_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile_dir = tmp_path / "private-profile"
    profile_dir.mkdir()
    config_file = profile_dir / "config.yaml"
    config_file.write_text(
        f"""
app:
  profile_name: "test_profile"
  data_dir: "{profile_dir.as_posix()}"

workflow:
  require_human_approval_before_export: true
  stop_on_blacklist: true
  warn_on_duplicate: true
  stop_on_prompt_injection: false

llm:
  provider: "openai"
  model_extract: "${{OPENAI_MODEL_EXTRACT}}"
  model_tailor: "${{OPENAI_MODEL_TAILOR}}"
  model_qa: "${{OPENAI_MODEL_QA}}"
  temperature_extract: 0.0
  temperature_tailor: 0.2
  temperature_qa: 0.0
  use_structured_outputs: true

cv:
  default_variant: "backend_developer"
  variants:
    - "backend_developer"

exports:
  markdown: true
  html: true
  pdf: true
  docx: true

guardrails:
  allow_new_skills: false
  allow_fake_metrics: false
  require_fact_ids: true
  require_evidence_matrix: true
  max_summary_words: 80
  british_english: true

job_reader:
  allow_url_input: true
  allow_manual_text_input: true
  min_extracted_text_chars: 1200

future_integrations:
  reed_api_enabled: false
  auto_apply_enabled: false
""".strip()
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("PROFILE_NAME", "test_profile")
    monkeypatch.setenv("PROFILE_DATA_DIR", profile_dir.as_posix())

    alembic_config = Config(str(ROOT / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(ROOT / "alembic"))

    command.upgrade(alembic_config, "head")

    database_file = profile_dir / "applications.sqlite3"
    assert database_file.is_file()

    engine = create_engine(f"sqlite:///{database_file.as_posix()}")
    inspector = inspect(engine)

    assert {
        "applications",
        "artifacts",
        "application_events",
        "application_warnings",
        "alembic_version",
    }.issubset(set(inspector.get_table_names()))

    application_columns = {
        column["name"] for column in inspector.get_columns("applications")
    }
    assert "artifact_dir_name" in application_columns
