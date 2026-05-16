from __future__ import annotations

from app.llm.prompts.tailoring import build_work_experience_bullet_prompt


def test_tailoring_prompt_excludes_private_contact_data():
    payload = build_work_experience_bullet_prompt(
        bullet={
            "id": 1,
            "target_type": "resume_bullet",
            "text": "Built APIs.",
            "email": "secret@example.com",
            "phone": "+1",
        },
        requirements=[{"id": 1, "text": "Python"}],
        facts=[{"id": 1, "claim": "Built APIs"}],
        policy={"fact_link_required": True},
    )
    rendered = str(payload.user_payload)
    assert "secret@example.com" not in rendered
    assert "+1" not in rendered
    assert "untrusted data" in payload.system_prompt
    assert "Do not invent" in payload.system_prompt
