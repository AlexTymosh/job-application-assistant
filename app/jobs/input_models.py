from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class JobInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_url: HttpUrl | None = None
    manual_text: str | None = Field(default=None, min_length=200)

    @model_validator(mode="after")
    def require_url_or_manual_text(self) -> JobInput:
        if self.source_url is None and not self.manual_text:
            raise ValueError("Either source_url or manual_text must be provided.")

        return self
