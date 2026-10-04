from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ImageTags(BaseModel):
    """The ONLY shape we accept from a vision model. Anything else is invalid output."""

    model_config = ConfigDict(extra="ignore")
    subject: str = Field(min_length=1, max_length=80)
    category: str = Field(min_length=1, max_length=40)
    attributes: list[str] = Field(default_factory=list, max_length=12)
    caption: str = Field(min_length=3, max_length=300)
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("subject", "category")
    @classmethod
    def _norm(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("must not be blank")
        return v

    @field_validator("attributes")
    @classmethod
    def _attrs(cls, v: list[str]) -> list[str]:
        return [a.strip().lower()[:80] for a in v if a and a.strip()]


# Gemini's responseSchema dialect (OpenAPI subset).
GEMINI_TAG_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "subject": {"type": "STRING"},
        "category": {"type": "STRING"},
        "attributes": {"type": "ARRAY", "items": {"type": "STRING"}},
        "caption": {"type": "STRING"},
        "confidence": {"type": "NUMBER"},
    },
    "required": ["subject", "category", "attributes", "caption", "confidence"],
}


class PostCreate(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=120)
    title: str = Field(min_length=3, max_length=300)
    body: str = Field(min_length=1, max_length=20000)


class CheckRequest(BaseModel):
    image_id: int = Field(gt=0)


class ReviewRequest(BaseModel):
    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=1000)
    override: bool = False  # required to approve something the guard rejected
