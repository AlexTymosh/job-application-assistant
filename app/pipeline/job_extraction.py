from __future__ import annotations

from app.llm.errors import JobExtractionError
from app.llm.fake_client import JobExtractionClient
from app.pipeline.state import ApplicationRunState


class JobExtractionStep:
    def __init__(self, extraction_client: JobExtractionClient) -> None:
        self._extraction_client = extraction_client

    def run(self, state: ApplicationRunState) -> ApplicationRunState:
        if state.manual_job_text is None or not state.manual_job_text.strip():
            raise JobExtractionError("Manual job text is required for job extraction.")

        extracted_job = self._extraction_client.extract_job(state.manual_job_text)
        warning_codes = [*state.warning_codes]

        for warning in extracted_job.warnings:
            warning_code = warning.code.value

            if warning_code not in warning_codes:
                warning_codes.append(warning_code)

        return state.model_copy(
            update={
                "extracted_job": extracted_job,
                "warning_codes": warning_codes,
                "status": "job_extracted",
            }
        )
