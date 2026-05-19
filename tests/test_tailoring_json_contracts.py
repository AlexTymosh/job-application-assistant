from __future__ import annotations

import pytest

from app.core.errors import TailoringWorkflowError
from app.llm.schemas import expected_response_contract_for_task, schema_for_task
from app.llm.tailoring_client import parse_model_json_response


def test_schema_for_task_has_required_properties():
    schema = schema_for_task("resume_tailoring")
    assert "summary" in schema["properties"]
    assert "skills" in schema["properties"]


def test_contract_is_in_system_prompt_format_text():
    contract = expected_response_contract_for_task("fit_analysis")
    assert "fit_summary" in contract
    assert "strong_matches" in contract


def test_parse_model_json_response_direct_json():
    parsed = parse_model_json_response('{"cover_letter":"ok"}')
    assert parsed["cover_letter"] == "ok"


def test_parse_model_json_response_fenced_json():
    parsed = parse_model_json_response('```json\n{"cover_letter":"ok"}\n```')
    assert parsed["cover_letter"] == "ok"


def test_parse_model_json_response_with_prose_wrapper():
    parsed = parse_model_json_response('hello\n{"cover_letter":"ok"}\nthanks')
    assert parsed["cover_letter"] == "ok"


def test_parse_model_json_response_rejects_top_level_array():
    with pytest.raises(TailoringWorkflowError):
        parse_model_json_response('[{"a":1}]')
