from __future__ import annotations


class AppError(Exception):
    status_code = 400
    title = "Action could not be completed"

    def __init__(
        self, message: str | None = None, *, status_code: int | None = None
    ) -> None:
        super().__init__(message or self.title)
        self.message = message or self.title
        if status_code is not None:
            self.status_code = status_code


class NotFoundError(AppError):
    status_code = 404
    title = "Not found"


class ValidationAppError(AppError):
    status_code = 400
    title = "Check the submitted information"


class ActiveProfileRequiredError(AppError):
    status_code = 400
    title = "Active profile required"


class ProfileScopeError(AppError):
    status_code = 404
    title = "Workspace item not found"


class ResumeBuilderError(AppError):
    status_code = 400
    title = "Resume Builder action failed"


class ApplicationWorkflowError(AppError):
    status_code = 400
    title = "Application workflow action failed"


class TailoringWorkflowError(AppError):
    status_code = 400
    title = "Tailoring workflow action failed"

    def __init__(
        self,
        message: str,
        *,
        task_name: str | None = None,
        trace_id: str | None = None,
        error_kind: str | None = None,
    ) -> None:
        super().__init__(message)
        self.task_name = task_name
        self.trace_id = trace_id
        self.error_kind = error_kind


class ExportWorkflowError(AppError):
    status_code = 400
    title = "Export action failed"
