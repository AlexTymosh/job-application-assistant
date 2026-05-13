from __future__ import annotations

from app.cv.models import FactBank, LoadedCv
from app.llm.fake_tailor import JobTailoringClient
from app.llm.schemas import ExtractedJob
from app.pipeline.state import ApplicationRunState


class CvTailoringStep:
    def __init__(self, tailoring_client: JobTailoringClient) -> None:
        self._tailoring_client = tailoring_client

    def run(
        self,
        state: ApplicationRunState,
        *,
        loaded_cv: LoadedCv,
        fact_bank: FactBank,
        extracted_job: ExtractedJob | None = None,
    ) -> ApplicationRunState:
        job = extracted_job or state.extracted_job
        if job is None:
            raise ValueError("Extracted job is required for CV tailoring.")

        tailoring_result = self._tailoring_client.tailor_cv(
            original_markdown=loaded_cv.markdown,
            extracted_job=job,
            fact_bank=fact_bank,
            allowed_sections=loaded_cv.sections,
        )
        warning_codes = [warning.code.value for warning in tailoring_result.warnings]
        status = "tailored" if tailoring_result.changes else "ready_for_tailoring"

        if not tailoring_result.changes and warning_codes:
            status = "qa_warning"

        return state.model_copy(
            update={
                "original_cv_markdown": loaded_cv.markdown,
                "tailored_cv_markdown": tailoring_result.tailored_markdown,
                "cv_changes": tailoring_result.changes,
                "tailoring_warning_codes": warning_codes,
                "status": status,
            }
        )
