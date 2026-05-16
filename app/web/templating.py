from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.settings.service import SettingsService

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def shell_context(request: Request) -> dict[str, Any]:
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        return {"profiles": [], "active_profile": None}
    with factory() as session:
        service = SettingsService(session)
        return {
            "profiles": service.list_profiles(),
            "active_profile": service.get_active_profile(),
        }


class AppTemplates(Jinja2Templates):
    """Compatibility wrapper using the project's conventional call order."""

    def TemplateResponse(self, name: str, context: dict[str, Any], **kwargs: Any):  # noqa: N802
        context.setdefault("shell", shell_context(context["request"]))
        return super().TemplateResponse(context["request"], name, context, **kwargs)


templates = AppTemplates(directory=TEMPLATE_DIR)
