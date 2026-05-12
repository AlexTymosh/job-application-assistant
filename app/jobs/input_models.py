from __future__ import annotations

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

MIN_MANUAL_TEXT_CHARS = 200


class JobInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_url: HttpUrl | None = None
    manual_text: str | None = Field(default=None)

    @field_validator("manual_text")
    @classmethod
    def validate_manual_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalised_value = " ".join(value.strip().split())

        if not normalised_value:
            raise ValueError("Manual job text must not be empty.")

        if len(normalised_value) < MIN_MANUAL_TEXT_CHARS:
            raise ValueError(
                f"Manual job text must contain at least {MIN_MANUAL_TEXT_CHARS} "
                "non-whitespace characters."
            )

        return value

    @model_validator(mode="after")
    def require_url_or_manual_text(self) -> JobInput:
        if self.source_url is None and self.manual_text is None:
            raise ValueError("Either source_url or manual_text must be provided.")

        return self
