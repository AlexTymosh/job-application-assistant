from __future__ import annotations


class AppError(Exception):
    """Base class for safe, user-facing application errors."""

    status_code = 400
    title = "Action needed"

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class NotFoundError(AppError):
    status_code = 404
    title = "Not found"


class ValidationAppError(AppError):
    status_code = 400
    title = "Check the information"


class ActiveProfileRequiredError(AppError):
    status_code = 400
    title = "Active profile required"

    def __init__(
        self, message: str = "Select an active profile before using this workspace."
    ) -> None:
        super().__init__(message)


class ProfileScopeError(AppError):
    status_code = 404
    title = "Not found"


class ResumeBuilderError(AppError):
    status_code = 400
    title = "Resume builder issue"


class ApplicationWorkflowError(AppError):
    status_code = 400
    title = "Application workflow issue"


class TailoringWorkflowError(AppError):
    status_code = 400
    title = "Tailoring workflow issue"


class ExportWorkflowError(AppError):
    status_code = 400
    title = "Export workflow issue"
