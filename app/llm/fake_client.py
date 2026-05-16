from __future__ import annotations

from dataclasses import dataclass, field

from app.llm.prompts.cover_letter import build_cover_letter_prompt
from app.llm.prompts.tailoring import PromptPayload
from app.tailoring.schema import AiChangeProposalSchema


@dataclass
class FakeJobExtractionClient:
    captured_texts: list[str] = field(default_factory=list)

    def extract(self, job_text: str) -> list[dict[str, object]]:
        self.captured_texts.append(job_text)
        words = [word.strip(".,:;()[]").lower() for word in job_text.split()]
        keywords = []
        for candidate in [
            "python",
            "fastapi",
            "sql",
            "api",
            "automation",
            "testing",
            "docker",
        ]:
            if candidate in words and candidate not in keywords:
                keywords.append(candidate)
        if not keywords:
            keywords = ["communication"]
        return [
            {
                "requirement_type": "skill",
                "text": f"Experience with {keyword}",
                "keywords": [keyword],
                "priority": index + 1,
            }
            for index, keyword in enumerate(keywords[:5])
        ]


@dataclass
class FakeTailoringClient:
    captured_payloads: list[PromptPayload] = field(default_factory=list)

    def propose(self, payload: PromptPayload) -> AiChangeProposalSchema | None:
        self.captured_payloads.append(payload)
        target = payload.user_payload["target"]
        requirements = payload.user_payload["job_requirements"]
        facts = payload.user_payload["allowed_facts"]
        if not requirements:
            return None
        requirement = requirements[0]
        fact_ids = [int(fact["id"]) for fact in facts[:1] if fact.get("id")]
        policy = payload.user_payload["editing_policy"]
        if policy.get("fact_link_required") and not fact_ids:
            return AiChangeProposalSchema(
                target_type=target["target_type"],
                target_id=int(target["id"]),
                operation="rewrite",
                before_text=str(target.get("text", "")),
                after_text=str(target.get("text", "")),
                reason="No verified fact supports a stronger claim.",
                risk_level="high",
                requirement_ids=[int(requirement["id"])],
                fact_ids=[],
                warnings=["missing_verified_fact"],
            )
        before = str(target.get("text", ""))
        suffix = str(requirement["text"])
        after = (
            before
            if suffix.lower() in before.lower()
            else f"{before} Aligns with {suffix.lower()}."
        )
        operation = (
            "update_title"
            if target["target_type"] == "resume_block_title"
            else "rewrite"
        )
        return AiChangeProposalSchema(
            target_type=target["target_type"],
            target_id=int(target["id"]),
            operation=operation,
            before_text=before,
            after_text=after,
            reason="Deterministic fake proposal matched an extracted requirement.",
            risk_level="low" if fact_ids else "medium",
            requirement_ids=[int(requirement["id"])],
            fact_ids=fact_ids,
            warnings=[] if fact_ids else ["unsupported_optional_fact_link"],
        )


@dataclass
class FakeCoverLetterClient:
    captured_payloads: list[PromptPayload] = field(default_factory=list)

    def generate(
        self,
        *,
        profile_name: str,
        resume_markdown: str,
        job_requirements: list[dict[str, object]],
        user_instruction: str = "",
    ) -> str:
        payload = build_cover_letter_prompt(
            profile_name=profile_name,
            resume_markdown=resume_markdown,
            job_requirements=job_requirements,
            user_instruction=user_instruction,
        )
        self.captured_payloads.append(payload)
        requirement = (
            job_requirements[0]["text"] if job_requirements else "the role requirements"
        )
        return (
            "Dear hiring team,\n\n"
            "I am interested in this role because my verified resume background "
            f"matches {requirement}.\n\n"
            "Sincerely,\n"
            f"{profile_name}\n"
        )
