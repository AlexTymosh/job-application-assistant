from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    AiChangeProposal,
    Application,
    ApplicationStatus,
    ExtractedJobRequirement,
    Fact,
    Resume,
    ResumeBlock,
    ResumeBullet,
    ResumeBulletFactLink,
    ResumeSection,
    TailoringRun,
)
from app.llm.fake_client import FakeTailoringClient
from app.llm.prompts.tailoring import (
    build_description_prompt,
    build_job_title_prompt,
    build_skills_prompt,
    build_summary_prompt,
    build_work_experience_bullet_prompt,
)
from app.resumes.policies import AiEditPolicy
from app.tailoring.schema import AiChangeProposalSchema


class TailoringValidationError(ValueError):
    pass


class TailoringService:
    def __init__(self, session: Session, client: FakeTailoringClient | None = None) -> None:
        self.session = session
        self.client = client or FakeTailoringClient()

    def run_tailoring(self, application_id: int) -> TailoringRun:
        app = self.session.get(Application, application_id)
        if app is None:
            raise ValueError("Application not found.")
        requirements = list(self.session.scalars(select(ExtractedJobRequirement).where(ExtractedJobRequirement.application_id == app.id)))
        if not requirements:
            raise ValueError("Extract job requirements before tailoring.")
        resume = self.session.scalar(select(Resume).where(Resume.id == app.resume_id).options(selectinload(Resume.sections).selectinload(ResumeSection.blocks).selectinload(ResumeBlock.bullets)))
        if resume is None:
            raise ValueError("Resume not found.")
        facts = list(self.session.scalars(select(Fact).where(Fact.profile_id == app.profile_id, Fact.is_active.is_(True))))
        run = TailoringRun(
            application_id=app.id,
            resume_id=resume.id,
            status="proposed",
            completed_at=datetime.now(UTC),
        )
        self.session.add(run)
        self.session.flush()
        requirement_payload = [{"id": req.id, "text": req.text, "priority": req.priority} for req in requirements]
        fact_payload = [
            {
                "id": fact.id,
                "claim": fact.claim,
                "allowed_claim_level": fact.allowed_claim_level,
            }
            for fact in facts
        ]
        for section in resume.sections:
            for block in section.blocks:
                self._propose_for_block(run, block, requirement_payload, fact_payload)
                for bullet in block.bullets:
                    self._propose_for_bullet(run, bullet, requirement_payload, fact_payload)
        app.status = ApplicationStatus.TAILORING_PROPOSED.value
        self.session.commit()
        return run

    def _propose_for_block(
        self,
        run: TailoringRun,
        block: ResumeBlock,
        requirements: list[dict[str, object]],
        facts: list[dict[str, object]],
    ) -> None:
        if not block.ai_edit_enabled:
            return
        policy = AiEditPolicy.from_json(block.policy_json).to_json()
        target = {
            "id": block.id,
            "target_type": "resume_block",
            "text": block.content or block.title,
            "block_type": block.block_type,
        }
        if block.block_type == "summary":
            payload = build_summary_prompt(block=target, requirements=requirements, facts=facts, policy=policy)
        elif block.block_type == "skills":
            target["target_type"] = "skills_set"
            payload = build_skills_prompt(block=target, requirements=requirements, facts=facts, policy=policy)
        elif block.block_type == "title":
            if not policy.get("ai_can_edit_title"):
                return
            target["target_type"] = "resume_block_title"
            target["text"] = block.title
            payload = build_job_title_prompt(block=target, requirements=requirements, facts=facts, policy=policy)
        else:
            payload = build_description_prompt(block=target, requirements=requirements, facts=facts, policy=policy)
        proposal = self.client.propose(payload)
        if proposal is not None:
            self._store_validated(run, proposal)

    def _propose_for_bullet(
        self,
        run: TailoringRun,
        bullet: ResumeBullet,
        requirements: list[dict[str, object]],
        facts: list[dict[str, object]],
    ) -> None:
        if not bullet.ai_edit_enabled:
            return
        linked_fact_ids = {link.fact_id for link in self.session.scalars(select(ResumeBulletFactLink).where(ResumeBulletFactLink.bullet_id == bullet.id))}
        allowed_facts = [fact for fact in facts if not linked_fact_ids or int(fact["id"]) in linked_fact_ids]
        policy = {
            "ai_editable": True,
            "ai_can_rewrite": True,
            "fact_link_required": bullet.fact_link_required,
        }
        payload = build_work_experience_bullet_prompt(
            bullet={
                "id": bullet.id,
                "target_type": "resume_bullet",
                "text": bullet.text,
            },
            requirements=requirements,
            facts=allowed_facts,
            policy=policy,
        )
        proposal = self.client.propose(payload)
        if proposal is not None:
            self._store_validated(run, proposal)

    def _store_validated(self, run: TailoringRun, proposal: AiChangeProposalSchema) -> None:
        self.validate_proposal(run.resume_id, proposal)
        self.session.add(
            AiChangeProposal(
                tailoring_run_id=run.id,
                target_type=proposal.target_type,
                target_id=proposal.target_id,
                operation=proposal.operation,
                before_text=proposal.before_text,
                after_text=proposal.after_text,
                reason=proposal.reason,
                risk_level=proposal.risk_level,
                requirement_ids_json=proposal.requirement_ids,
                fact_ids_json=proposal.fact_ids,
                warning_codes_json=proposal.warnings,
            )
        )

    def validate_proposal(self, resume_id: int, proposal: AiChangeProposalSchema) -> None:
        if proposal.target_type == "resume_bullet":
            bullet = self.session.get(ResumeBullet, proposal.target_id)
            if bullet is None or not bullet.ai_edit_enabled:
                raise TailoringValidationError("Target bullet does not exist or is not AI-editable.")
            if bullet.fact_link_required and proposal.risk_level != "high" and not proposal.fact_ids:
                raise TailoringValidationError("Fact IDs are required for supported bullet rewrites.")
        elif proposal.target_type in {
            "resume_block",
            "resume_block_title",
            "skills_set",
        }:
            block = self.session.get(ResumeBlock, proposal.target_id)
            if block is None or not block.ai_edit_enabled:
                raise TailoringValidationError("Target block does not exist or is not AI-editable.")
            if proposal.target_type == "resume_block_title" and not AiEditPolicy.from_json(block.policy_json).ai_can_edit_title:
                raise TailoringValidationError("Title edits are forbidden by policy.")
        else:
            raise TailoringValidationError("Unsupported target type.")
