from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.templating import Jinja2Templates

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


class AppTemplates(Jinja2Templates):
    """Compatibility wrapper using the project's conventional call order."""

    def TemplateResponse(self, name: str, context: dict[str, Any], **kwargs: Any):  # noqa: N802
        return super().TemplateResponse(context["request"], name, context, **kwargs)


templates = AppTemplates(directory=TEMPLATE_DIR)
