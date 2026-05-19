from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.core.errors import TailoringWorkflowError
from app.llm.schemas import (
    CoverLetterResponse,
    FitAnalysisResponse,
    ResumeTailoringResponse,
    expected_response_contract_for_task,
    schema_for_task,
)
from app.llm.tailoring_client import (
    FakeSectionTailoringClient,
    parse_model_json_response,
)
from app.llm.task_logging import AiTaskLogger
from app.llm.task_runner import AiTaskRunner


def _log_lines(log_dir):
    files = list(log_dir.glob("ai-tasks-*.jsonl"))
    assert files
    return [
        json.loads(line) for line in files[0].read_text(encoding="utf-8").splitlines()
    ]


def _runner(tmp_path, client=None):
    return AiTaskRunner(
        client=client or FakeSectionTailoringClient(),
        logger=AiTaskLogger(log_dir=tmp_path),
        application_id=1,
        profile_id=2,
        resume_id=3,
        prompt_variant_id=4,
        prompt_variant_name="Default Prompt Variant",
        model="gpt-test",
        llm_mode="fake",
        trace_id="trace-123",
    )


def test_schema_for_task_has_required_properties():
    schema = schema_for_task("resume_tailoring")
    assert "summary" in schema["properties"]
    assert "skills" in schema["properties"]
    assert schema["additionalProperties"] is False


def test_contract_is_in_system_prompt_format_text():
    contract = expected_response_contract_for_task("fit_analysis")
    assert "fit_summary" in contract
    assert "strong_matches" in contract
    assert "additionalProperties" in contract


def test_parse_model_json_response_direct_json():
    parsed = parse_model_json_response('{"cover_letter":"ok"}')
    assert parsed["cover_letter"] == "ok"


def test_parse_model_json_response_fenced_json():
    parsed = parse_model_json_response('```json\n{"cover_letter":"ok"}\n```')
    assert parsed["cover_letter"] == "ok"


def test_parse_model_json_response_with_prose_wrapper():
    parsed = parse_model_json_response('hello\n{"cover_letter":"ok"}\nthanks')
    assert parsed["cover_letter"] == "ok"


def test_parse_model_json_response_handles_braces_inside_strings():
    parsed = parse_model_json_response(
        'prefix {"cover_letter":"Uses {literal} braces"} suffix'
    )
    assert parsed["cover_letter"] == "Uses {literal} braces"


def test_parse_model_json_response_skips_non_json_braces_before_valid_json():
    parsed = parse_model_json_response(
        'Ignore this {not JSON}. Actual response: {"cover_letter":"ok"}'
    )

    assert parsed["cover_letter"] == "ok"


def test_parse_model_json_response_skips_invalid_json_candidate_before_valid_json():
    parsed = parse_model_json_response(
        'First candidate {"bad": } then final response {"cover_letter":"ok"}'
    )

    assert parsed["cover_letter"] == "ok"


def test_parse_model_json_response_rejects_top_level_array():
    with pytest.raises(TailoringWorkflowError):
        parse_model_json_response('[{"a":1}]')


def test_response_models_forbid_extra_fields():
    with pytest.raises(ValidationError):
        CoverLetterResponse.model_validate(
            {"cover_letter": "ok", "unexpected": "not allowed"}
        )


def test_ai_task_runner_logs_started_and_success(tmp_path):
    response = _runner(tmp_path).run_json_task(
        task_name="cover_letter",
        payload={"tailored_resume": "safe", "job_description": "job"},
        prompt="prompt",
        response_model=CoverLetterResponse,
    )

    assert response.cover_letter
    statuses = [(line["task_name"], line["status"]) for line in _log_lines(tmp_path)]
    assert ("cover_letter", "started") in statuses
    assert ("cover_letter", "response_received") in statuses
    assert ("cover_letter", "success") in statuses


def test_ai_task_runner_preserves_task_name_for_validation_error(tmp_path):
    client = FakeSectionTailoringClient()
    client.override_json_by_task["fit_analysis"] = {"fit_summary": "missing arrays"}

    with pytest.raises(TailoringWorkflowError) as error:
        _runner(tmp_path, client).run_json_task(
            task_name="fit_analysis",
            payload={"tailored_resume": "safe", "job_description": "job"},
            prompt="prompt",
            response_model=FitAnalysisResponse,
        )

    assert error.value.task_name == "fit_analysis"
    assert error.value.trace_id == "trace-123"
    assert error.value.error_kind == "validation_error"
    lines = _log_lines(tmp_path)
    assert any(
        line["task_name"] == "fit_analysis" and line["status"] == "validation_error"
        for line in lines
    )


def test_ai_task_runner_preserves_task_name_for_parse_error(tmp_path):
    client = FakeSectionTailoringClient()
    client.override_text_by_task["resume_tailoring"] = "not json"

    with pytest.raises(TailoringWorkflowError) as error:
        _runner(tmp_path, client).run_json_task(
            task_name="resume_tailoring",
            payload={"safe_resume": {"sections": {}}, "job_description": "job"},
            prompt="prompt",
            response_model=ResumeTailoringResponse,
        )

    assert error.value.task_name == "resume_tailoring"
    assert error.value.trace_id == "trace-123"
    assert error.value.error_kind == "parse_error"
    assert any(
        line["task_name"] == "resume_tailoring" and line["status"] == "parse_error"
        for line in _log_lines(tmp_path)
    )


def test_raw_response_logging_is_disabled_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEBUG_LOG_RAW_RESPONSES", raising=False)
    _runner(tmp_path).run_json_task(
        task_name="cover_letter",
        payload={"tailored_resume": "safe", "job_description": "job"},
        prompt="prompt",
        response_model=CoverLetterResponse,
    )

    log_text = "\n".join(
        path.read_text(encoding="utf-8") for path in tmp_path.glob("*.jsonl")
    )

    assert '"raw_response"' not in log_text
    assert '"safe_payload"' not in log_text


def test_raw_response_logging_can_be_enabled_and_is_redacted(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DEBUG_LOG_RAW_RESPONSES", "true")
    client = FakeSectionTailoringClient()
    client.override_text_by_task["cover_letter"] = json.dumps(
        {
            "cover_letter": (
                "Contact person@example.com or +44 1234567890 with sk-test-secret."
            )
        }
    )

    _runner(tmp_path, client).run_json_task(
        task_name="cover_letter",
        payload={"tailored_resume": "safe", "job_description": "job"},
        prompt="prompt",
        response_model=CoverLetterResponse,
    )

    text = "\n".join(
        path.read_text(encoding="utf-8") for path in tmp_path.glob("*.jsonl")
    )
    assert "raw_response" in text
    assert "person@example.com" not in text
    assert "+44 1234567890" not in text
    assert "sk-test-secret" not in text
    assert "[redacted_email]" in text
    assert "[redacted_phone]" in text
    assert "[redacted_key]" in text
